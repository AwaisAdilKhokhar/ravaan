#!/usr/bin/env python
"""Where §4.2's AR infilling framing loses its information — teacher-forced, no decoder (PRD §4.2).

`scripts/infill_eval.py` scores what a decoder produced. This asks the prior question: **does the
model know the answer at all?** One forward pass per item, the rank and probability of the *gold*
token under the model's own distribution. A decoder cannot hide anything from it, which is the
point — the first reading of the infill numbers was that greedy decoding had collapsed the AR arm
onto a high-frequency token (`کے` on 32 of 64 items at span 1), and that reading is wrong.

Three comparisons, and each one exists to kill an explanation of the previous one:

1. ``framing`` — the same gold token, asked two ways. Under `<lm>` the AR arm ranks it **2**; under
   `<fim_middle>`, holding everything else fixed and handing it *more* information (the suffix),
   it ranks it **74**. So the gap is not the model's Urdu and not the decoder.
2. ``span`` — the same question across hole sizes. `_frame_infill` trains on middles of 5-50% of
   the content, so a small hole is off-distribution for the AR arm and that is a live explanation.
   It is not the explanation: the rank does not recover at 16, 64, 128 or 200 either.
3. ``depth`` — the rank of the middle's *k*-th token, teacher-forced with the gold middle prefixed
   back in. This is the one that localises it. d0 is rank ~117 and d1 is rank ~11; by d4 the arm is
   at rank 3.5, which is its plain-LM rank. **The damage is one position wide.**

The mechanism that fits all three: to predict `middle[0]` the arm has to reach back past the entire
suffix to where the prefix ended, and at 20M parameters it does not — it emits a high-frequency
token instead. To predict `middle[1]` it has `middle[0]` adjacent. The diffusion arm never has this
problem because its canvas keeps the hole *in place*, with both neighbours adjacent and attention
bidirectional; it sits at median rank 1-6 across every span.

This is the same framing Finding AQ found has no terminator after the middle. AQ says the arm was
never taught where an infill *ends*; this says it barely learns where one *begins*. Both are
properties of §4.2's FIM layout rather than of masked diffusion or of the backbone.

    python scripts/infill_probe.py --checkpoint runs/urdu-ar/ar-s0_f1.pt \\
        --checkpoint runs/urdu-ar-fim50/ar-s0_f1.pt \\
        --checkpoint runs/urdu-diff/diff-s0_f1.pt \\
        --corpus data/packed-urdu --out reports/eval/infill_framing_probe.json

Requires the `[train]` extra.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

import numpy as np  # noqa: E402
import torch  # noqa: E402

from ravaan.sampling import load_arm, prompts  # noqa: E402
from ravaan.training.data import PackedCorpus  # noqa: E402

#: Matches `scripts/infill_eval.py`, so the two files' numbers are about the same prompts.
CONTENT = 476
#: Spans 1-4 are where exact-match is a live number; 16-200 is `_frame_infill`'s own range.
SPANS = (1, 2, 4, 16, 64, 128, 200)
#: Positions into the middle, for the depth curve. 0 is the `<fim_middle>` transition.
DEPTHS = (0, 1, 2, 4, 8, 16, 32)
#: The span the depth curve is measured at — long enough to reach d32, and inside
#: `_frame_infill`'s own 5-50% range.
DEPTH_SPAN = 64


def build_arguments() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--checkpoint", action="append", required=True, help="repeatable")
    p.add_argument("--corpus", default="data/packed-urdu")
    p.add_argument("--split", default="validation")
    p.add_argument("--items", type=int, default=64)
    p.add_argument("--content", type=int, default=CONTENT)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--device", default="auto")
    p.add_argument("--out", default="reports/eval/infill_framing_probe.json")
    return p


def pick_sequences(corpus: PackedCorpus, count: int, seed: int) -> list[np.ndarray]:
    total = len(corpus)
    if total == 0:
        raise SystemExit("the corpus split is empty")
    take = min(count, total)
    stride = max(1, total // take)
    offset = int(np.random.default_rng(seed).integers(0, stride)) if stride > 1 else 0
    return [np.asarray(corpus[min(offset + i * stride, total - 1)]) for i in range(take)]


def rank_of(logits: torch.Tensor, position: int, gold: int, forbid) -> tuple[int, float]:
    """Rank (1 = argmax) and probability of ``gold`` at ``position``, with `<mask>`/`<pad>` out."""
    row = (logits[position] if logits.dim() == 2 else logits[0, position]).float()
    for bad in forbid:
        row[bad] = float("-inf")
    rank = int((row > row[gold]).sum().item()) + 1
    return rank, float(torch.log_softmax(row, -1)[gold].exp().item())


def summarize(ranks: list[int], probs: list[float]) -> dict:
    return {
        "items": len(ranks),
        "median_rank": float(np.median(ranks)),
        "mean_probability": float(np.mean(probs)),
        "top1": float(np.mean([r == 1 for r in ranks])),
        "top10": float(np.mean([r <= 10 for r in ranks])),
    }


def carve(content: list[int], span: int, rng) -> tuple[list[int], list[int], list[int]]:
    start = int(rng.integers(1, len(content) - span - 1))
    return content[:start], content[start : start + span], content[start + span :]


def main(argv: list[str] | None = None) -> int:
    args = build_arguments().parse_args(argv)
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    corpus = PackedCorpus(args.corpus, split=args.split, arm=None)
    sequences = pick_sequences(corpus, args.items, args.seed)
    print(f"{corpus.describe()}\n{len(sequences)} {args.split} sequences\n", file=sys.stderr)

    report: dict = {
        "corpus": args.corpus,
        "split": args.split,
        "items": len(sequences),
        "content_tokens": args.content,
        "depth_span": DEPTH_SPAN,
        "checkpoints": {},
    }

    for path in args.checkpoint:
        arm = load_arm(path, device=device)
        arm.model.eval()
        label = f"{Path(path).parent.name}/{Path(path).stem}"
        entry: dict = {"arm": arm.arm, "span": {}, "depth": {}, "plain_lm": {}}
        print(f"{label} — {arm.arm.upper()}", file=sys.stderr)

        for span in SPANS:
            rng = np.random.default_rng(args.seed * 1_000_003 + span)
            fim_r, fim_p, lm_r, lm_p = [], [], [], []
            for sequence in sequences:
                content = [int(t) for t in sequence[: args.content]]
                prefix, gold, suffix = carve(content, span, rng)
                prompt = prompts.infill(
                    arm.framing, arm.arm, prefix=prefix, suffix=suffix,
                    span=span, mask_id=arm.mask_id,
                )
                ids = torch.tensor([list(prompt.tokens)], device=device)
                with torch.no_grad():
                    logits = arm.model(ids)
                position = (
                    len(prompt.tokens) - 1
                    if arm.arm == "ar"
                    else list(prompt.locked).index(False)
                )
                rank, probability = rank_of(logits, position, gold[0], arm.forbidden)
                fim_r.append(rank)
                fim_p.append(probability)

                # The control, AR only: the same gold token under `<lm>`, same prefix, no suffix.
                # The diffusion arm has no left-to-right framing to compare against.
                if arm.arm == "ar":
                    plain = prompts.lm(arm.framing, "ar", prefix=prefix)
                    ids = torch.tensor([list(plain.tokens)], device=device)
                    with torch.no_grad():
                        logits = arm.model(ids)
                    rank, probability = rank_of(
                        logits, len(plain.tokens) - 1, gold[0], arm.forbidden
                    )
                    lm_r.append(rank)
                    lm_p.append(probability)

            entry["span"][str(span)] = summarize(fim_r, fim_p)
            if lm_r:
                entry["plain_lm"][str(span)] = summarize(lm_r, lm_p)
            plain = (
                f"   plain-LM rank {np.median(lm_r):6.1f}" if lm_r else ""
            )
            print(
                f"  span {span:>3}  FIM rank {np.median(fim_r):7.1f}  "
                f"P(gold) {np.mean(fim_p):.4f}{plain}",
                file=sys.stderr,
                flush=True,
            )

        # The depth curve: teacher-forced with the gold middle prefixed back in, so position k
        # asks "given the middle so far, how well ranked is its next token". AR only — the
        # diffusion arm commits positions in its own order and has no "depth into the middle".
        if arm.arm == "ar":
            rng = np.random.default_rng(args.seed * 1_000_003 + DEPTH_SPAN)
            depths: dict[int, list[int]] = {d: [] for d in DEPTHS}
            for sequence in sequences:
                content = [int(t) for t in sequence[: args.content]]
                prefix, gold, suffix = carve(content, DEPTH_SPAN, rng)
                prompt = prompts.infill(
                    arm.framing, "ar", prefix=prefix, suffix=suffix, span=DEPTH_SPAN
                )
                ids = torch.tensor([list(prompt.tokens) + list(gold)], device=device)
                with torch.no_grad():
                    logits = arm.model(ids)
                for depth in DEPTHS:
                    rank, _ = rank_of(
                        logits, len(prompt.tokens) - 1 + depth, gold[depth], arm.forbidden
                    )
                    depths[depth].append(rank)
            entry["depth"] = {
                str(d): {"median_rank": float(np.median(v))} for d, v in depths.items()
            }
            curve = "  ".join(f"d{d}:{np.median(v):6.1f}" for d, v in depths.items())
            print(f"  depth (span {DEPTH_SPAN}) {curve}", file=sys.stderr, flush=True)

        report["checkpoints"][label] = entry
        del arm
        if device == "cuda":
            torch.cuda.empty_cache()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\nwrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
