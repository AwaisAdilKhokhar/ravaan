#!/usr/bin/env python
"""Average K ELBO draws so a diffusion number carries an error bar — Finding BA.

Ravaan-DIFF's held-out bits-per-byte is not a property of a checkpoint. `RavaanDiffusion.loss`
draws one masking rate `t` and one mask **per sequence**, so the NELBO it returns is a Monte Carlo
estimate of an expectation, and `Trainer.evaluate` called it with `generator=None` — the draw rode
the global RNG. Session 28 measured the consequence over six independent draws of the full
validation split: **urdu sd 0.0069 bpb** (range 0.7995–0.8170), roman_urdu 0.0089, code_switched
0.0307, `all` 0.0040. This driver is that scratch measurement promoted to `scripts/`, turned from
a diagnostic into the thing that produces the reported number.

    python scripts/elbo.py --run D:/ravaan-runs/ship-diff-b --seed 0 --draws 9 \\
        --corpus data/packed --out reports/eval/elbo_diff_b.json

**Why averaging rather than a fix.** There is nothing to fix. The ELBO *is* an expectation over
`t`, a single draw is an unbiased estimate of it, and the variance is the price of not integrating
analytically. Averaging K independent draws is the whole repair: the estimator's sd falls as √K,
so **K = 9 takes native Urdu from 0.0069 to ~0.0023** — below the differences the report needs to
resolve. The AR arm needs none of this because its NLL is exact, which is also the asymmetry that
makes `--arm ar` an error here rather than a slow no-op.

**Why it is load-bearing and not hygiene.** Two live comparisons rest on one draw each. Arm B's
16-epoch endpoint is AR 0.8690 against DIFF **0.8320**, and the diffusion half is a single sample
— `ship-diff-b/evaluation.json` says 0.8247 for the *same checkpoint*, 1.06 sd away, and
`curves.py` refused to assert the two matched, naming BA rather than calling it a defect. And
§4.5's primary endpoint compares a noiseless AR number against a noisy diffusion one, so the
crossover's rungs need the bar beside them.

**The estimator, and why averaging bpb is the right average.** `bits_per_byte` is
`total_nats / total_bytes`. The byte denominator is a property of the text, and `scored` is
`labels != IGNORE_INDEX` minus `keep` — neither depends on the mask draw. Both are therefore
constant across draws, so averaging the K aggregate bpb figures is *identical* to averaging each
sequence's nats and aggregating once. `--check-denominators` asserts that constancy rather than
trusting the argument, because it is the assumption the mean rests on.

**Seeds are recorded, not implicit.** Draw *k* uses `--base-seed + k` on a generator built on the
eval device, so every number here is reproducible from the JSON alone. This is the same discipline
§8.1 imposes on the decoders, applied to the one place scoring turned out to be stochastic too.

Resumable per (checkpoint, draw): a seven-rung pass at K = 9 is 63 full-split evaluations, and
this machine has lost long passes before. Writes after every draw.

Requires the `[train]` extra.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

import torch  # noqa: E402

from ravaan.models.config import LADDER  # noqa: E402
from ravaan.sampling.decoding import build_generator  # noqa: E402
from ravaan.training.config import TrainingConfig  # noqa: E402
from ravaan.training.data import PackedCorpus  # noqa: E402
from ravaan.training.loop import Trainer  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from curves import fraction_of  # noqa: E402
from train import _device, build_model  # noqa: E402

POPULATIONS = ("urdu", "roman_urdu", "code_switched", "all")


def summarize(draws: list[dict]) -> dict:
    """Per-population mean, sd across draws, and the standard error of that mean.

    ``sd`` is Finding BA's quantity — the spread of a *single* draw, which is what every
    diffusion number in this repository before session 33 carried. ``sem`` is what the reported
    average carries instead, and the ratio between them is √K by construction. Reported for
    every key any draw produced rather than a fixed list, so a corpus with a population this
    file does not know about is still summarized.
    """
    keys = sorted({key for draw in draws for key in draw})
    summary = {}
    for key in keys:
        values = [draw[key]["bits_per_byte"] for draw in draws if key in draw]
        mean = statistics.fmean(values)
        # sd is undefined at K = 1, and a single draw is a legitimate thing to ask for — it is
        # what every prior number is. Report the mean and say the spread is unmeasured rather
        # than crashing on the degenerate case.
        sd = statistics.stdev(values) if len(values) > 1 else None
        summary[key] = {
            "bits_per_byte": mean,
            "draws": len(values),
            "sd": sd,
            "sem": (sd / len(values) ** 0.5) if sd is not None else None,
            "min": min(values),
            "max": max(values),
            "values": values,
        }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run", help="a run directory; scores every f* fraction checkpoint")
    source.add_argument("--checkpoint", help="a single .pt, scored on its own")
    parser.add_argument("--arm", default="diff", choices=("diff",))
    parser.add_argument("--size", default="70M")
    parser.add_argument("--seed", type=int, default=0, help="the run's seed, for its file names")
    parser.add_argument("--draws", type=int, default=9, help="K; sd falls as sqrt(K)")
    parser.add_argument("--base-seed", type=int, default=1000, help="draw k uses base-seed + k")
    parser.add_argument("--corpus", default="data/packed")
    parser.add_argument("--corpus-arm", default="A")
    parser.add_argument("--eval-split", default="validation")
    parser.add_argument("--microbatch", type=int, default=16)
    parser.add_argument("--mask-id", type=int, default=None)
    parser.add_argument("--out", required=True, help="JSON; appended to and resumed from")
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--check-denominators",
        action="store_true",
        help="assert scored tokens and text bytes are identical across draws (they must be)",
    )
    args = parser.parse_args(argv)

    if args.draws < 1:
        raise SystemExit("--draws must be at least 1")

    run_name = f"{args.arm}-s{args.seed}"
    if args.run:
        run_dir = Path(args.run)
        checkpoints = []
        for path in sorted(run_dir.glob(f"{run_name}_f*.pt")):
            fraction = fraction_of(path.name, run_name)
            if fraction is not None:
                checkpoints.append((f"{fraction:g}", path))
        checkpoints.sort(key=lambda pair: float(pair[0]))
        if not checkpoints:
            raise SystemExit(f"no fraction checkpoints matching {run_name}_f*.pt under {run_dir}")
    else:
        path = Path(args.checkpoint)
        run_dir = path.parent
        checkpoints = [(path.stem, path)]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done: dict[str, dict] = {}
    if out_path.exists():
        done = json.loads(out_path.read_text(encoding="utf-8")).get("points", {})
        have = sum(len(point.get("draws", [])) for point in done.values())
        print(f"resuming — {have} draws already on disk", file=sys.stderr)

    corpus = PackedCorpus(args.corpus, split="train", arm=args.corpus_arm)
    held_out = PackedCorpus(args.corpus, split=args.eval_split, arm=None)
    device = _device(args.device)
    total = len(checkpoints) * args.draws
    print(
        f"source  {run_dir}\n"
        f"arm     Ravaan-{args.arm.upper()} at {args.size}\n"
        f"eval    {args.eval_split}: {len(held_out):,} sequences, no limit (Finding AZ)\n"
        f"draws   K = {args.draws} per checkpoint, seeds "
        f"{args.base_seed}..{args.base_seed + args.draws - 1}\n"
        f"work    {len(checkpoints)} checkpoint(s) x {args.draws} = {total} full-split passes\n"
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

    def flush() -> None:
        out_path.write_text(
            json.dumps(
                {
                    "source": str(run_dir),
                    "arm": args.arm,
                    "seed": args.seed,
                    "eval_split": args.eval_split,
                    "corpus_arm": args.corpus_arm,
                    "base_seed": args.base_seed,
                    "requested_draws": args.draws,
                    "points": done,
                },
                indent=1,
            ),
            encoding="utf-8",
        )

    for key, path in checkpoints:
        point = done.setdefault(
            key, {"checkpoint": path.name, "draw_seeds": [], "draws": [], "summary": {}}
        )
        wanted = [args.base_seed + k for k in range(args.draws)]
        missing = [seed for seed in wanted if seed not in point["draw_seeds"]]
        if not missing:
            print(f"\n{path.name} — {len(point['draws'])} draws already, skipping",
                  file=sys.stderr)
            continue

        print(f"\n{path.name} — {len(missing)} of {args.draws} draws to take",
              file=sys.stderr, flush=True)
        # Loaded once per checkpoint, not once per draw. `Trainer.load` restores the global RNG
        # from the checkpoint, which is exactly the coupling this driver exists to remove — every
        # draw below names its own generator, so what the load leaves in the global state is
        # never read.
        trainer.load(path)
        point["step"] = trainer.state.step
        point["tokens"] = trainer.state.tokens

        for seed in missing:
            started = time.time()
            generator = build_generator(device, seed)
            evaluation = trainer.evaluate(held_out, limit=0, generator=generator)
            point["draw_seeds"].append(seed)
            point["draws"].append(evaluation)
            point["summary"] = summarize(point["draws"])
            flush()
            urdu = evaluation.get("urdu", evaluation["all"])["bits_per_byte"]
            print(
                f"  seed {seed}  urdu bpb {urdu:6.4f}  ({time.time() - started:.0f}s)",
                file=sys.stderr,
                flush=True,
            )

        if args.check_denominators:
            # The mean of K bpb figures equals the bpb of the mean nats only because the
            # denominators do not move. `scored` is `labels != IGNORE_INDEX` (minus `keep`) and
            # `text_bytes` is a property of the text, so neither should depend on the mask draw.
            # Asserted rather than argued.
            for name in POPULATIONS:
                if name not in point["draws"][0]:
                    continue
                seen = {
                    (draw[name]["scored_tokens"], draw[name]["sequences"])
                    for draw in point["draws"]
                }
                if len(seen) != 1:
                    raise SystemExit(
                        f"{path.name}: {name}'s denominators moved across draws ({seen}) — "
                        "averaging bits-per-byte is only valid while they do not"
                    )
            print("  ✓ denominators identical across draws", file=sys.stderr)

        summary = point["summary"]
        for name in POPULATIONS:
            entry = summary.get(name)
            if entry is None:
                continue
            sd, sem = entry["sd"], entry["sem"]
            bar = f"sd {sd:.4f}  sem {sem:.4f}" if sd is not None else "sd unmeasured at K=1"
            print(
                f"  {name:<14} bpb {entry['bits_per_byte']:6.4f}  {bar}  "
                f"K={entry['draws']}",
                file=sys.stderr,
                flush=True,
            )

    flush()
    print(f"\nwrote {out_path} — {len(done)} checkpoint(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
