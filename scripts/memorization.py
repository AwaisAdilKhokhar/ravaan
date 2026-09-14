#!/usr/bin/env python
"""Train-versus-held-out loss under identical scoring — how much of a run is recall (PRD §4.3).

§4.3's epoch sweep is a *repeat* experiment: arm A processes 9.9B tokens drawn from 25M unique
ones, ~396 times over. The whole reason a crossover is predicted there is that the two objectives
are expected to degrade differently under repetition. So "how much has this checkpoint memorized"
is not a diagnostic sitting beside the primary endpoint — it is the mechanism the primary endpoint
is about, and nothing in the repository measured it until session 23.

**What this computes.** `Trainer.evaluate`'s plain-LM scoring, run twice: once over a sample of the
split the model trained on and once over the held-out split. Same objective, same denominator, same
code path — so the difference between the two numbers is generalization gap and not framing.

    python scripts/memorization.py --checkpoint runs/pilot/pilot-ar/ar_f1.pt \\
        --checkpoint runs/pilot/pilot-diff/diff_f1.pt \\
        --corpus data/packed-pilot --sequences 512

**Why the diffusion arm's number is noisier than the AR arm's, and is not directly comparable to
it.** The AR loss is an exact NLL; the diffusion loss is a one-sample estimate of an ELBO, with a
fresh masking rate drawn per sequence, so it carries the variance Finding AG measured. Both are
averaged over the same sequences here and the *gap* is what this driver is for — a bound and an
exact likelihood cannot be compared to each other, but each can be compared to itself on two
splits, which is the only comparison this file makes.

Requires the `[train]` extra.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

import torch  # noqa: E402

from ravaan.sampling import load_arm  # noqa: E402
from ravaan.training.data import PackedCorpus  # noqa: E402


def score(model, corpus: PackedCorpus, count: int, device: str, stride: int) -> dict:
    """Plain-LM loss over ``count`` sequences, evenly spaced. Nats, bits/token, bits/byte.

    Evenly spaced rather than the first ``count``: a packed stream is written in corpus order, so
    its head is one source's opening documents — the same argument `scripts/sample.py` makes about
    prompts, and it matters more here because this number is a *mean*.
    """
    nats = scored = text_bytes = 0.0
    taken = 0
    for index in range(0, min(len(corpus), count * stride), stride):
        tokens = torch.from_numpy(corpus[index]).unsqueeze(0).to(device)
        with torch.no_grad():
            out = model.loss(tokens)
        width = float(out.scored)
        nats += float(out.nats) * width
        scored += width
        text_bytes += corpus.text_bytes(index)
        taken += 1
        if taken >= count:
            break
    return {
        "nats_per_token": nats / max(scored, 1),
        "bits_per_token": nats / max(scored, 1) / math.log(2),
        "bits_per_byte": nats / max(text_bytes, 1) / math.log(2),
        "sequences": taken,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--checkpoint", action="append", required=True, help="repeatable")
    parser.add_argument("--corpus", default="data/packed-pilot")
    parser.add_argument("--corpus-arm", default="A")
    parser.add_argument("--sequences", type=int, default=512, help="per split")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default=None, help="write the table as JSON as well")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args(argv)

    torch.manual_seed(args.seed)
    train = PackedCorpus(args.corpus, split="train", arm=args.corpus_arm)
    held_out = PackedCorpus(args.corpus, split="validation", arm=None)
    print(f"corpus     {args.corpus}")
    print(f"  train    {len(train):,} sequences, {train.tokens:,} tokens")
    print(f"  held-out {len(held_out):,} sequences\n")

    rows = []
    for path in args.checkpoint:
        arm = load_arm(path, device=args.device)
        arm.model.eval()
        # Space the sample across each split rather than reading its head.
        seen = score(arm.model, train, args.sequences, args.device,
                     max(1, len(train) // max(args.sequences, 1)))
        unseen = score(arm.model, held_out, args.sequences, args.device,
                       max(1, len(held_out) // max(args.sequences, 1)))
        gap = unseen["nats_per_token"] - seen["nats_per_token"]
        rows.append(
            {
                "checkpoint": str(path),
                "arm": arm.arm,
                "fraction": arm.fraction,
                "train": seen,
                "held_out": unseen,
                "gap_nats": gap,
                "gap_ratio": (
                    unseen["nats_per_token"] / seen["nats_per_token"]
                    if seen["nats_per_token"]
                    else None
                ),
            }
        )
        print(arm.describe())
        print(
            f"  train    {seen['nats_per_token']:7.4f} nats  bpb {seen['bits_per_byte']:.4f}  "
            f"({seen['sequences']} seqs)"
        )
        print(
            f"  held-out {unseen['nats_per_token']:7.4f} nats  bpb {unseen['bits_per_byte']:.4f}  "
            f"({unseen['sequences']} seqs)"
        )
        print(f"  gap      {gap:+7.4f} nats\n", flush=True)

    print(f"{'checkpoint':<40} {'arm':<5} {'train':>9} {'held-out':>9} {'gap':>9}")
    for row in rows:
        print(
            f"{Path(row['checkpoint']).name:<40} {row['arm']:<5} "
            f"{row['train']['nats_per_token']:>9.4f} {row['held_out']['nats_per_token']:>9.4f} "
            f"{row['gap_nats']:>+9.4f}"
        )

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps({"corpus": args.corpus, "rows": rows}, indent=1) + "\n", encoding="utf-8"
        )
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
