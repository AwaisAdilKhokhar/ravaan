#!/usr/bin/env python
"""Score every fraction checkpoint on the held-out split — PRD §4.3, gate G4.

§4.3 says "Checkpoint at 1, 2, 5, 10, 25, 50, 100% of tokens processed ... **Evaluate every
checkpoint**", and G4 (§11) reads those curves at 50% of tokens. `train.py run --evaluate` scores
only the *final* model, so the seven checkpoints it writes had no driver to read them and the
curve G4 is defined on could not be produced. This is that driver.

    python scripts/curves.py --run /d/ravaan-runs/core-diff-s0 --arm diff \
        --corpus data/packed --out reports/eval/curve_diff_s0.json

**The split is `validation`, not `test`, and that is a requirement rather than a default.**
PRD §8.2: the test split is what §8.2's reported number comes from, and "the separate 5K
validation split is what G4 and the §8.3 curves read". G4 may act on what it sees, so reading it
on the test split would be taking a decision on the set the headline number is later reported from.

**The scoring path is `Trainer.evaluate`, the same one `cmd_run` calls**, so a curve's 100% point
is directly comparable with the run's own `evaluation.json` rather than merely similar to it.
`--check` asserts exactly that and is on by default: if the f1 point does not reproduce the
committed number, the curve is wrong and says so instead of being plotted.

⚠️ **`limit` is 0 — the full split.** Finding AZ: `--eval-limit` truncates in shard order rather
than sampling, and populations concatenate code_switched → roman_urdu → urdu, so any cap scores
the primary endpoint on a prefix of one population and weights the `all` row 10/61/30 instead of
4/25/71. There is no cap here and there is no flag to add one.

Writes after every checkpoint, and skips what the output file already holds. A seven-checkpoint
pass is hours on a laptop card, and this machine has lost long passes before.

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

from ravaan.models.config import LADDER  # noqa: E402
from ravaan.training.config import TrainingConfig  # noqa: E402
from ravaan.training.data import PackedCorpus  # noqa: E402
from ravaan.training.loop import Trainer  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from train import _device, build_model  # noqa: E402


def fraction_of(name: str, run_name: str) -> float | None:
    """`diff-s0_fp25.pt` → 0.25, `diff-s0_f1.pt` → 1.0, `diff-s0_rolling.pt` → None.

    The suffix after `_f` is the fraction with its leading `0.` dropped, so `p25` is 0.25 and a
    bare `1` is the whole budget. Parsed rather than hard-coded so a run that ever writes a
    different set of fractions is read as it was written.
    """
    stem = Path(name).stem
    if not stem.startswith(f"{run_name}_f"):
        return None
    suffix = stem[len(run_name) + 2 :]
    if suffix.startswith("p"):
        digits = suffix[1:]
        return float(f"0.{digits}") if digits.isdigit() else None
    return float(suffix) if suffix.isdigit() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="a run directory written by train.py run")
    parser.add_argument("--arm", required=True, choices=("ar", "diff"))
    parser.add_argument("--size", default="70M")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--corpus", default="data/packed")
    parser.add_argument("--corpus-arm", default="A")
    parser.add_argument("--eval-split", default="validation")
    parser.add_argument("--tokenizer", default="data/tokenizer/ravaan-16k.model")
    parser.add_argument("--microbatch", type=int, default=16)
    parser.add_argument("--mask-id", type=int, default=None)
    parser.add_argument("--out", required=True, help="JSON; appended to and resumed from")
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="skip asserting the 100%% point against the run's own evaluation.json",
    )
    args = parser.parse_args(argv)

    run_dir = Path(args.run)
    run_name = f"{args.arm}-s{args.seed}"
    checkpoints = []
    for path in sorted(run_dir.glob(f"{run_name}_f*.pt")):
        fraction = fraction_of(path.name, run_name)
        if fraction is not None:
            checkpoints.append((fraction, path))
    checkpoints.sort()
    if not checkpoints:
        raise SystemExit(f"no fraction checkpoints matching {run_name}_f*.pt under {run_dir}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done: dict[str, dict] = {}
    if out_path.exists():
        done = json.loads(out_path.read_text(encoding="utf-8")).get("points", {})
        print(f"resuming — {len(done)} of {len(checkpoints)} already scored", file=sys.stderr)

    corpus = PackedCorpus(args.corpus, split="train", arm=args.corpus_arm)
    held_out = PackedCorpus(args.corpus, split=args.eval_split, arm=None)
    device = _device(args.device)
    print(
        f"run     {run_dir}\n"
        f"arm     Ravaan-{args.arm.upper()} at {args.size}\n"
        f"eval    {args.eval_split}: {len(held_out):,} sequences, no limit (Finding AZ)\n"
        f"device  {device}",
        file=sys.stderr,
    )

    model = build_model(args.arm, LADDER[args.size], corpus, args.mask_id)
    trainer = Trainer(
        model,
        corpus,
        TrainingConfig(),
        out_dir=out_path.parent,
        device=device,
        microbatch=args.microbatch,
        run_name=run_name,
        tasks=None,
    )

    for fraction, path in checkpoints:
        key = f"{fraction:g}"
        if key in done:
            continue
        print(f"\n{path.name} — {fraction:.0%} of tokens", file=sys.stderr, flush=True)
        trainer.load(path)
        evaluation = trainer.evaluate(held_out, limit=0)
        done[key] = {
            "fraction": fraction,
            "checkpoint": path.name,
            # The x-axis §4.3 asks for is tokens processed, taken from the checkpoint's own
            # state rather than inferred from the filename.
            "step": trainer.state.step,
            "tokens": trainer.state.tokens,
            "evaluation": evaluation,
        }
        out_path.write_text(
            json.dumps(
                {"run": str(run_dir), "arm": args.arm, "seed": args.seed,
                 "eval_split": args.eval_split, "points": done},
                indent=1,
            ),
            encoding="utf-8",
        )
        for name, entry in sorted(evaluation.items()):
            print(
                f"  {name:<14} bpb {entry['bits_per_byte']:6.4f}  "
                f"bpt {entry['bits_per_token']:6.4f}  {entry['sequences']:,} seqs",
                file=sys.stderr,
                flush=True,
            )

    # The 100% point must reproduce the run's own committed evaluation.json. If it does not, the
    # two were not produced by the same path and nothing above is comparable with the run record.
    committed = run_dir / "evaluation.json"
    if not args.no_check and "1" in done and committed.exists():
        theirs = json.loads(committed.read_text(encoding="utf-8"))
        ours = done["1"]["evaluation"]
        # The tolerance is relative, and it is not "exact" for a reason worth stating. Even a
        # deterministic arm does not reproduce bit-for-bit — bf16 autocast and non-deterministic
        # reduction order move the last digits, measured at **6.6e-6 relative** for Ravaan-AR.
        # What this guard exists to catch is a different thing by two orders of magnitude:
        # Ravaan-DIFF's ELBO is a *sampled* quantity (Finding BA) and lands **5.9e-3** away,
        # 207× further out. 1e-4 sits an order of magnitude clear of both.
        for name in sorted(theirs):
            a, b = theirs[name]["bits_per_byte"], ours[name]["bits_per_byte"]
            if not math.isclose(a, b, rel_tol=1e-4):
                raise SystemExit(
                    f"the 100% point does not reproduce {committed}: "
                    f"{name} bpb {b:.6f} against the committed {a:.6f} "
                    f"({abs(a - b) / a:.1e} relative). For --arm diff this is expected and is "
                    f"Finding BA, not a defect: the ELBO is a single-sample estimate and the "
                    f"two numbers are different draws. Re-run with --no-check to record it."
                )
        print(
            f"\n✓ 100% point reproduces {committed} to within 1e-4 relative",
            file=sys.stderr,
        )

    print(f"\nwrote {out_path} — {len(done)} points", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
