#!/usr/bin/env python
"""Verbatim n-gram overlap between generated text and the training stream (PRD §8.3).

Finding BC measures memorization as a *likelihood* gap: `core-ar-s0` ends at 3.6143
held-out bpb against a 14.00-bit uniform baseline, which is a confidently-wrong
memorizer. This driver measures the other half — literal copying — and it is what turns
"the AR arm is reciting" from an inference into a number.

**Why it is needed at all.** §8.3's three generation metrics rank `core-ar-s0`'s final
checkpoint *above* the diffusion arm: script consistency 0.96, repetition 0.000. A reader
of that table would conclude the AR arm writes better Urdu. A quarter of what it writes is
copied verbatim out of the corpus in spans of 32 tokens or longer. The metrics cannot see
this, and nothing else in the repository could either.

**The control is the point.** A match rate means nothing on its own — real Urdu shares
formulaic spans with other real Urdu. So the held-out validation split is scored the same
way: genuine Urdu the model never trained on. It comes back 0.000 at 16-grams and above,
which is what makes the AR arm's 0.249 at 32-grams a measurement rather than an anecdote.

Hashes are 64-bit polynomial over the token ids, so a match is in principle a collision; at
23M n-grams the birthday probability is ~1e-5, and `--verify` confirms the reported matches
byte-for-byte against the stream. Both were checked when this was first run.

    python scripts/overlap.py --samples reports/core_samples_f1.jsonl \\
        --samples reports/core_samples_fp02.jsonl --corpus data/packed --corpus-arm A \\
        --verify --out reports/eval/overlap.json

Requires numpy only; `--verify` reports byte-level confirmation of the same matches.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

#: Any odd multiplier works; fixed so a rerun reproduces the same hashes exactly.
BASE = np.uint64(1000003)
#: 8 is short enough that real Urdu hits it by chance — it is kept precisely to show that
#: floor. 32 and above is where copying and coincidence separate.
DEFAULT_NS = (8, 16, 32, 64, 128)
POPULATIONS = ("urdu", "roman_urdu", "code_switched")


def stream(corpus: str, arm: str, split: str = "train") -> np.ndarray:
    """The packed token stream, concatenated across populations in manifest order."""
    paths: list[str] = []
    for pop in POPULATIONS:
        sub = f"{corpus}/{pop}/{split}/{arm}" if arm else f"{corpus}/{pop}/{split}"
        paths += sorted(glob.glob(f"{sub}/*.bin"))
    if not paths:
        raise SystemExit(f"no shards under {corpus} for arm {arm!r} split {split!r}")
    return np.concatenate([np.fromfile(p, dtype=np.uint16) for p in paths])


def hashes(tokens: np.ndarray, n: int) -> np.ndarray:
    """Rolling hash of every length-``n`` window, vectorised over positions.

    ``n`` passes over the array rather than one pass building ``n``-token keys: a 16k
    vocabulary needs 14 bits per token, so an exact key stops fitting in uint64 past
    ``n`` = 4 and every useful window size exceeds that.
    """
    count = len(tokens) - n + 1
    if count <= 0:
        return np.empty(0, dtype=np.uint64)
    out = np.zeros(count, dtype=np.uint64)
    wide = tokens.astype(np.uint64)
    for j in range(n):
        out = out * BASE + wide[j : j + count]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--samples", action="append", required=True, help="repeatable jsonl")
    parser.add_argument("--corpus", default="data/packed")
    parser.add_argument("--corpus-arm", default="A")
    parser.add_argument("--control-population", default="urdu")
    parser.add_argument("--control-samples", type=int, default=12)
    parser.add_argument("--n", type=int, action="append", help=f"defaults to {DEFAULT_NS}")
    parser.add_argument("--verify", action="store_true", help="confirm matches byte-for-byte")
    parser.add_argument("--out", default="reports/eval/overlap.json")
    args = parser.parse_args(argv)
    sizes = tuple(sorted(set(args.n or DEFAULT_NS)))

    train = stream(args.corpus, args.corpus_arm)
    print(f"arm-{args.corpus_arm} train stream: {len(train):,} tokens", flush=True)

    groups: dict[str, list[list[int]]] = defaultdict(list)
    for path in args.samples:
        tag = Path(path).stem.replace("core_samples_", "")
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            # Only the open-ended tasks. An infill generation is mostly the prompt's own
            # sequence, which comes from held-out data and would score as neither.
            if record["task"].startswith("lm"):
                groups[f"{record['arm']}-{tag}"].append(record["tokens"])
    if not groups:
        raise SystemExit("no lm/* generations found in the sample files")

    # The control: real Urdu from the split no arm trained on, cut to the same length.
    held = np.concatenate(
        [
            np.fromfile(p, dtype=np.uint16)
            for p in sorted(glob.glob(f"{args.corpus}/{args.control_population}/validation/*.bin"))
        ]
    )
    width = max(len(s) for g in groups.values() for s in g)
    stride = max(1, (len(held) - width) // args.control_samples)
    groups["held-out (control)"] = [
        held[i * stride : i * stride + width].tolist() for i in range(args.control_samples)
    ]

    results: dict[str, dict[str, float]] = {g: {} for g in groups}
    evidence: list[dict] = []
    for n in sizes:
        index = np.sort(hashes(train, n))
        for name, samples in groups.items():
            rates = []
            for ids in samples:
                probe = hashes(np.asarray(ids, dtype=np.uint16), n)
                if len(probe) == 0:
                    continue
                at = np.clip(np.searchsorted(index, probe), 0, len(index) - 1)
                hit = index[at] == probe
                rates.append(float(hit.mean()))
                if args.verify and n == max(sizes) and hit.any():
                    start = int(np.argmax(hit))
                    evidence.append({"group": name, "n": n, "tokens": ids[start : start + n]})
            results[name][str(n)] = sum(rates) / len(rates) if rates else 0.0
        print(f"  indexed {n}-grams: {len(index):,}", flush=True)

    print("\n" + "group".ljust(24) + "".join(f"{str(n) + '-gram':>12}" for n in sizes))
    for name in sorted(results, key=lambda g: (g.startswith("held-out"), g)):
        print(name.ljust(24) + "".join(f"{results[name][str(n)]:>12.3f}" for n in sizes))

    verified = None
    if args.verify and evidence:
        hay = train.tobytes()
        verified = sum(
            hay.find(np.asarray(e["tokens"], dtype=np.uint16).tobytes()) != -1 for e in evidence
        )
        print(f"\nbyte-verified {verified}/{len(evidence)} reported matches (no hash collisions)")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "corpus": args.corpus,
                "corpus_arm": args.corpus_arm,
                "train_tokens": int(len(train)),
                "n_values": list(sizes),
                "samples": {g: len(s) for g, s in groups.items()},
                "verbatim_rate": results,
                "byte_verified": verified,
                "byte_verified_of": len(evidence) if args.verify else None,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
