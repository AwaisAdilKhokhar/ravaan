"""Prove a staged release runs as a stranger would run it — before anything is pushed.

The failure this exists to catch is specific and it has happened in this repository twice, under
Findings AX and BB: **code verified by reading is not verified.** `scripts/release.py` rewrites
`from ravaan.` to `from ravaan_infer.` textually, and a textual rewrite that misses one import
produces a package that works perfectly on the machine that built it — because the real `ravaan`
is importable there — and fails on the first `pip install` anywhere else.

So this driver runs each staged repo in a **subprocess whose working directory is the release and
whose `sys.path` does not contain this repository**. If a vendored module still reaches for the
original package, the import fails here rather than in a stranger's terminal.

Four checks per release:

1. **Imports resolve** with the source repo off the path.
2. **Weights load** from safetensors and the parameter count is §5's 69,975,680.
3. **It generates**, at the decoder settings the model card names as defaults.
4. **The output is Urdu** — Arabic-script share of the sampled text, which is the one metric that
   catches the failure mode that matters (Finding AO: a canvas that decodes to punctuation and
   Latin scores fine on everything else).

    python scripts/verify_release.py --root D:/ravaan-release
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import textwrap
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ravaan.console import pin_utf8_streams  # noqa: E402

#: Run inside the release directory, with the source repo removed from sys.path.
PROBE = textwrap.dedent(
    """
    import json, sys, pathlib
    here = pathlib.Path.cwd()
    # A stranger has no `ravaan` package. Neither does this probe.
    sys.path = [p for p in sys.path if 'Desktop' not in p and 'rawaan' not in p.lower()]
    sys.path.insert(0, str(here))
    assert 'ravaan' not in sys.modules

    import torch, sentencepiece as spm
    from ravaan_infer.loader import load
    from ravaan_infer.sampling import SamplingConfig, build_generator, generate, prompts

    arm = load(here, device='cpu')
    n = sum(p.numel() for p in arm.model.parameters())

    sp = spm.SentencePieceProcessor(model_file=str(arm.tokenizer_path))
    prefix = sp.encode(PREFIX) if PREFIX else []
    cfg = SamplingConfig(temperature=1.0, top_k=0, top_p=0.95)
    forbid = arm.forbidden + ((arm.eos_id,) if arm.arm == 'diff' else ())
    g = build_generator('cpu', 0)

    if arm.arm == 'diff':
        p = prompts.lm(arm.framing, 'diff', prefix=prefix,
                       length=len(prefix) + 1 + NTOK, mask_id=arm.mask_id)
        out = generate(arm.model, p, config=cfg, steps=8, schedule='gumbel',
                       gumbel=2.0, forbid=forbid, generator=g)
    else:
        p = prompts.lm(arm.framing, 'ar', prefix=prefix)
        out = generate(arm.model, p, config=cfg, max_new_tokens=NTOK,
                       forbid=forbid, eos_id=arm.eos_id, generator=g)

    ids = [int(t) for t in out.tokens[0]]
    text = sp.decode([t for t in ids if t >= 16])
    print('@@RESULT@@' + json.dumps(
        {'arm': arm.arm, 'params': n, 'text': text, 'describe': arm.describe()},
        ensure_ascii=True))
    """
).strip()


def arabic_share(text: str) -> float:
    """Share of *letters* in the Arabic block. Punctuation and digits are not evidence either way."""
    letters = [c for c in text if unicodedata.category(c).startswith("L")]
    if not letters:
        return 0.0
    arabic = sum(1 for c in letters if "\u0600" <= c <= "\u06ff" or "\ufb50" <= c <= "\ufdff")
    return arabic / len(letters)


def longest_repeat(text: str) -> int:
    """Longest run of one repeated word — the slot-looping tell (`مہار مہار مہار`)."""
    words = text.split()
    best = run = 1
    for a, b in zip(words, words[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    return best if words else 0


def check(release: Path, *, prefix: str, n_tokens: int) -> dict:
    print(f"\n=== {release.name} ===")

    missing = [
        f for f in ("config.json", "model.safetensors", "generate.py",
                    "tokenizer/ravaan-16k.model", "ravaan_infer/loader.py")
        if not (release / f).exists()
    ]
    if missing:
        print(f"  ✗ missing files: {', '.join(missing)}")
        return {"ok": False, "reason": "missing files", "missing": missing}

    source = PROBE.replace("PREFIX", json.dumps(prefix)).replace("NTOK", str(n_tokens))
    proc = subprocess.run(
        [sys.executable, "-c", source],
        cwd=release,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=900,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-6:]
        print("  ✗ the release does not run standalone:")
        for line in tail:
            print(f"      {line}")
        return {"ok": False, "reason": "subprocess failed", "stderr": tail}

    line = next(
        (ln for ln in proc.stdout.splitlines() if ln.startswith("@@RESULT@@")), None
    )
    if line is None:
        print("  ✗ probe produced no result line")
        return {"ok": False, "reason": "no result"}
    result = json.loads(line[len("@@RESULT@@"):])

    text = result["text"].strip()
    share = arabic_share(text)
    repeat = longest_repeat(text)
    ok_params = result["params"] == 69_975_680
    # 0.90 rather than 1.00: the corpus is 5.4% code-switched by construction, so a little Latin
    # in a sample is the corpus showing through, not a decode that stopped being Urdu.
    ok_script = share >= 0.90
    ok_loop = repeat <= 4

    print(f"  {'✓' if ok_params else '✗'} parameters      {result['params']:,}")
    print(f"  {'✓' if ok_script else '✗'} Arabic script   {share:.3f} of letters")
    print(f"  {'✓' if ok_loop else '✗'} longest repeat  {repeat} word(s)")
    print(f"  ✓ imports resolve with the source repo off sys.path")
    print(f"\n  {result['describe']}")
    print(f"  sample: {text[:160]}")

    return {
        "ok": ok_params and ok_script and ok_loop,
        "arm": result["arm"],
        "params": result["params"],
        "arabic_share": round(share, 4),
        "longest_repeat": repeat,
        "sample": text,
    }


def main() -> int:
    pin_utf8_streams()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="D:/ravaan-release")
    ap.add_argument("--prefix", default="پاکستان کی معیشت", help="Urdu prefix to continue")
    ap.add_argument("--tokens", type=int, default=64)
    ap.add_argument("--out", help="write the verdicts here as JSON")
    args = ap.parse_args()

    root = Path(args.root)
    releases = sorted(p for p in root.iterdir() if (p / "config.json").exists())
    if not releases:
        raise SystemExit(f"no staged releases under {root}")

    results = {p.name: check(p, prefix=args.prefix, n_tokens=args.tokens) for p in releases}
    failed = [n for n, r in results.items() if not r["ok"]]

    print("\n" + "=" * 62)
    if failed:
        print(f"✗ NOT READY TO PUSH — {', '.join(failed)}")
    else:
        print(f"✓ all {len(results)} release(s) run standalone and produce Urdu")

    if args.out:
        Path(args.out).write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"wrote {args.out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
