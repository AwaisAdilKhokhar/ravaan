#!/usr/bin/env python
"""§8.3's infill row, scored under preregistration §8's rule — and open question 5's instrument.

Two jobs in one pass, because they are the same measurement asked of different checkpoints.

**§8.3/§4.5's secondary endpoint.** "Infill exact-match" is one of three Holm-corrected secondary
endpoints and nothing in this repository could compute it until now. The rule it is scored under
was preregistered on 2026-09-13, before any result existed: the AR arm's generation is cut to the
gold span's token length, because §4.2's FIM framing has no terminator after the middle and the
diffusion arm is handed the width of its answer by construction. `ravaan.evaluation.infill` holds
the rule; this driver is what points it at a checkpoint.

**Open question 5.** §4.2 sets the infilling share at 10%; reported FIM practice is 50-90%. If 10%
leaves Ravaan-AR genuinely bad at infilling then ablation A2 ("AR without FIM") loses its meaning,
because the *fair* baseline would also be undertrained and §4.1's whole fairness argument weakens.
That question has been open since session 4 and has never had a number attached to it. It costs one
extra run today and six core runs once Week 9 has started.

**Three things about the measurement that are choices, and are here rather than in a footnote.**

* **The span grid is not the training distribution.** `TaskGenerator._frame_infill` draws a middle
  of 5-50% of the content, which on a 512-token sequence is a 25-255 token hole. Exact-match on a
  120-token hole is zero for every checkpoint in this project and would report nothing. So the grid
  is fixed hole sizes and the report carries the curve: the question "can it fill a hole" has a
  different answer at 8 tokens than at 64, and a single number hides which.
* **Decoding is greedy.** Exact-match against a gold string is a MAP-shaped task; sampling at
  temperature 0.9 would lower it for reasons that have nothing to do with the model. ⚠️ §8.3 does
  not preregister the decode settings for this endpoint and Week 12 must, before the core runs are
  scored. This driver's defaults are a diagnostic's, not the endpoint's.
* **The prefixes come from validation, never from training.** Same reason `scripts/sample.py`
  says: an infill of text the model was trained on measures recall. Session 23's `memorization.py`
  puts both arms' gaps at ~0.05 on this corpus, so that is checked rather than assumed.

    python scripts/infill_eval.py \\
        --checkpoint runs/urdu-ar/ar-s0_f1.pt \\
        --checkpoint runs/urdu-ar-fim50/ar-s0_f1.pt \\
        --checkpoint runs/urdu-diff/diff-s0_f1.pt \\
        --corpus data/packed-urdu --out reports/infill_share

Requires the `[train]` and `[tokenizer]` extras.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

import numpy as np  # noqa: E402
import torch  # noqa: E402

from ravaan.evaluation.infill import InfillItem, InfillScore  # noqa: E402
from ravaan.sampling import SamplingConfig, generate, load_arm, prompts  # noqa: E402
from ravaan.training.data import PackedCorpus  # noqa: E402
from ravaan.training.tasks import SentencePieceCodec  # noqa: E402

#: Hole sizes in tokens. Chosen to bracket the thing §8.3 is asking: 8 is a phrase, 32 is Finding
#: AQ's measured hole, 64 is a clause and a half. The training distribution reaches far past 64;
#: what it does not do is put any mass low enough for exact-match to be a live number.
SPANS = (8, 16, 32, 64)

#: How much of each validation sequence the prompt is built from. Fixed rather than the full 512
#: so that the AR arm's prompt plus its generation budget fits inside §5's context at every span.
CONTENT = 256

#: The diffusion arm's schedules. `confidence` is §4.4's preregistered A4 setting; `gumbel` is the
#: third arm session 23 added between A4's two after both endpoints were measured and both failed
#: (Finding AR). Both are reported — one of them is the preregistration's and one of them is the
#: one that produces readable text, and collapsing that to a single row is what §11 warns about.
SCHEDULES = ("confidence", "gumbel")
GUMBEL_SCALE = 2.0


def build_arguments() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--checkpoint", action="append", required=True, help="repeatable")
    p.add_argument("--corpus", default="data/packed-urdu")
    p.add_argument("--split", default="validation", help="never 'train' — see the module docstring")
    p.add_argument("--tokenizer", default="data/tokenizer/ravaan-16k.model")
    p.add_argument("--out", default="reports/infill_share", help="written as .jsonl and .md")
    p.add_argument("--items", type=int, default=64, help="validation sequences per span")
    p.add_argument("--spans", type=int, nargs="+", default=list(SPANS))
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--device", default="auto")
    p.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="0 is greedy, which is what an exact-match endpoint wants",
    )
    p.add_argument("--top-p", type=float, default=1.0)
    return p


def pick_sequences(corpus: PackedCorpus, count: int, seed: int) -> list[np.ndarray]:
    """A spaced sample, the same shape `memorization.py` uses — never the first N."""
    total = len(corpus)
    if total == 0:
        raise SystemExit("the corpus split is empty")
    take = min(count, total)
    stride = max(1, total // take)
    rng = np.random.default_rng(seed)
    offset = int(rng.integers(0, stride)) if stride > 1 else 0
    return [np.asarray(corpus[min(offset + i * stride, total - 1)]) for i in range(take)]


def carve(content: list[int], span: int, rng) -> tuple[list[int], list[int], list[int]] | None:
    """prefix / gold middle / suffix, with both sides non-empty — `_frame_infill`'s shape."""
    n = len(content)
    if n < span + 4:
        return None
    start = int(rng.integers(1, n - span - 1))
    return content[:start], content[start : start + span], content[start + span :]


def decode_text(codec: SentencePieceCodec, ids: list[int], framing_ids: set[int]) -> str:
    return codec.decode([i for i in ids if i not in framing_ids]).strip()


def main(argv: list[str] | None = None) -> int:
    args = build_arguments().parse_args(argv)
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    corpus = PackedCorpus(args.corpus, split=args.split, arm=None)
    codec = SentencePieceCodec(args.tokenizer)
    sequences = pick_sequences(corpus, args.items, args.seed)
    config = SamplingConfig(temperature=args.temperature, top_p=args.top_p, seed=args.seed)
    print(
        f"corpus  {corpus.describe()}\nsplit   {args.split} — {len(sequences)} sequences\n"
        f"decode  temperature {args.temperature} top-p {args.top_p} "
        f"({'greedy' if config.greedy else 'sampled'})",
        file=sys.stderr,
    )

    records: list[dict] = []
    scores: list[dict] = []
    started = time.time()

    for path in args.checkpoint:
        arm = load_arm(path, device=device)
        arm.model.eval()
        framing_ids = {getattr(arm.framing, field) for _, field in arm.framing.PIECES}
        framing_ids.add(arm.mask_id)
        framing_ids.add(arm.framing.pad)
        run_config = _run_config(Path(path))
        label = _label(Path(path), run_config)
        print(f"\n{label}: {arm.describe()}", file=sys.stderr)

        settings = [(None, None)] if arm.arm == "ar" else [(s, GUMBEL_SCALE) for s in SCHEDULES]
        for schedule, gumbel in settings:
            for span in args.spans:
                rng = np.random.default_rng(args.seed * 1_000_003 + span)
                items: list[InfillItem] = []
                for index, sequence in enumerate(sequences):
                    content = [int(t) for t in sequence[:CONTENT]]
                    carved = carve(content, span, rng)
                    if carved is None:
                        continue
                    prefix, gold, suffix = carved
                    prompt = prompts.infill(
                        arm.framing,
                        arm.arm,
                        prefix=prefix,
                        suffix=suffix,
                        span=span,
                        mask_id=arm.mask_id,
                    )
                    # A generous budget on purpose: the point of `exact_untruncated` is to measure
                    # how far past the hole the AR arm runs, and a budget of `span` would answer
                    # that question by construction.
                    headroom = arm.model_config.context_length - len(prompt.tokens)
                    budget = min(4 * span + 16, headroom)
                    if arm.arm == "ar" and budget < span:
                        continue
                    generation = generate(
                        arm.model,
                        prompt,
                        config=config,
                        max_new_tokens=budget if arm.arm == "ar" else None,
                        steps=span,
                        schedule=schedule or "confidence",
                        gumbel=gumbel or 1.0,
                        forbid=arm.forbidden,
                        eos_id=arm.eos_id,
                        generator=torch.Generator(device=device).manual_seed(
                            args.seed * 7919 + index
                        ),
                    )
                    written = generation.written()[0]
                    # §8.1's invariant, re-checked here as a *number* rather than trusted. The
                    # decoders assert it internally; this is the reported rate §8.3 asks for, and
                    # it is computed against the prompt this driver built rather than against the
                    # one the decoder believes it was given.
                    decoded = generation.tokens[0].tolist()
                    locked_ok = all(
                        decoded[position] == token
                        for position, (token, is_locked) in enumerate(
                            zip(prompt.tokens, prompt.locked, strict=True)
                        )
                        if is_locked
                    )
                    item = InfillItem.of(
                        arm=arm.arm, gold=gold, generated=written, locked_preserved=locked_ok
                    )
                    items.append(item)
                    records.append(
                        {
                            "checkpoint": str(path),
                            "label": label,
                            "arm": arm.arm,
                            "infill_share": run_config.get("infill_share"),
                            "schedule": schedule,
                            "gumbel": gumbel,
                            "span": span,
                            "index": index,
                            **item.to_dict(),
                            "gold_text": decode_text(codec, list(gold), framing_ids),
                            "generated_text": decode_text(codec, list(item.scored), framing_ids),
                        }
                    )
                if not items:
                    continue
                score = InfillScore.of(items)
                row = {
                    "checkpoint": str(path),
                    "label": label,
                    "arm": arm.arm,
                    "infill_share": run_config.get("infill_share"),
                    "schedule": schedule,
                    "gumbel": gumbel,
                    "span": span,
                    **score.to_dict(),
                }
                scores.append(row)
                print(
                    f"  span {span:>3}  {schedule or 'ar':<11} "
                    f"exact {score.exact_match:6.3f}  F1 {score.token_f1:6.3f}  "
                    f"(untruncated exact {score.exact_untruncated:6.3f}, "
                    f"cut {score.truncated:5.1%})",
                    file=sys.stderr,
                    flush=True,
                )
        del arm
        if device == "cuda":
            torch.cuda.empty_cache()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.with_suffix(".jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    out.with_suffix(".scores.json").write_text(
        json.dumps(
            {
                "corpus": args.corpus,
                "split": args.split,
                "items_requested": args.items,
                "spans": args.spans,
                "decode": config.to_dict(),
                "content_tokens": CONTENT,
                "scores": scores,
            },
            indent=1,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out.with_suffix(".md").write_text(render(scores, records, args), encoding="utf-8")
    print(
        f"\n{len(records):,} generations in {time.time() - started:.1f}s → "
        f"{out.with_suffix('.jsonl')}, {out.with_suffix('.scores.json')} and "
        f"{out.with_suffix('.md')}",
        file=sys.stderr,
    )
    return 0


def render(scores: list[dict], records: list[dict], args: argparse.Namespace) -> str:
    """The table, and enough text under it that a reader can see what a number is made of.

    §8.3's metrics cannot tell fluent Urdu from Urdu-shaped noise — `pilot_coherence.md` §6, twice
    — and exact-match is stricter than those three but no more able to say whether a *wrong*
    infill was a reasonable one. So the examples are not decoration: they are the only part of
    this file that shows what the model actually wrote where it did not write the gold span.
    """
    how = (
        "greedy decode"
        if args.temperature == 0
        else f"temperature {args.temperature}, top-p {args.top_p}"
    )
    lines = [
        "# §8.3's infill row — exact-match and token-F1",
        "",
        f"`scripts/infill_eval.py` over `{args.corpus}` (`{args.split}` split), "
        f"{args.items} sequences a span, {how}.",
        "",
        "Scored under preregistration §8's rule: **the AR arm's generation is cut to the gold "
        "span's token length.** `exact (raw)` is the same metric with the rule switched off and "
        "is a diagnostic, not the endpoint — see `ravaan/evaluation/infill.py`.",
        "",
        "| checkpoint | infill share | decoder | span | exact | token-F1 | exact (raw) | cut "
        "| mean generated |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in scores:
        share = "—" if row["infill_share"] is None else f"{row['infill_share']:.0%}"
        decoder = row["schedule"] or "left-to-right"
        if row["schedule"] == "gumbel":
            decoder = f"gumbel {row['gumbel']:g}"
        lines.append(
            f"| `{row['label']}` | {share} | {decoder} | {row['span']} | "
            f"{row['exact_match']:.3f} | {row['token_f1']:.3f} | "
            f"{row['exact_untruncated']:.3f} | {row['truncated']:.0%} | "
            f"{row['mean_generated_length']:.1f} |"
        )

    lines += ["", "## Locked-span preservation (§8.1, reported per §8.3)", ""]
    broken = [row for row in scores if row["locked_preserved"] < 1.0]
    lines.append(
        "Every row: 1.000."
        if not broken
        else "⚠️ **Not 1.000 everywhere** — "
        + ", ".join(f"`{r['label']}` span {r['span']}: {r['locked_preserved']:.3f}" for r in broken)
    )

    lines += ["", "## What the misses look like", ""]
    seen: set[tuple] = set()
    for record in records:
        key = (record["label"], record["schedule"], record["span"])
        if record["exact"] or key in seen:
            continue
        seen.add(key)
        decoder = record["schedule"] or "left-to-right"
        lines += [
            f"**`{record['label']}` · {decoder} · span {record['span']}** "
            f"(F1 {record['f1']:.3f}, wrote {record['generated_length']} tokens)",
            "",
            f"- gold: {record['gold_text']}",
            f"- generated: {record['generated_text']}",
            "",
        ]
    return "\n".join(lines) + "\n"


def _run_config(path: Path) -> dict:
    """The run's `config.json`, if it is next to the checkpoint — for the infilling share."""
    candidate = path.parent / "config.json"
    if not candidate.exists():
        return {}
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    tasks = payload.get("tasks") or {}
    shares = tasks.get("shares") or {}
    return {"infill_share": shares.get("infill"), "shares": shares, "arm": payload.get("arm")}


def _label(path: Path, run_config: dict) -> str:
    share = run_config.get("infill_share")
    suffix = "" if share is None else f" · infill {share:.0%}"
    return f"{path.parent.name}/{path.stem}{suffix}"


if __name__ == "__main__":
    raise SystemExit(main())
