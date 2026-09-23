"""Read Urdu out of a released Ravaan model.

    pip install torch sentencepiece safetensors
    python generate.py                                  # unconditional
    python generate.py --prefix "پاکستان کی معیشت"      # continue a prefix
    python generate.py --tokens 200 --seed 7

**The decoder settings below are part of the model, not preferences.** A masked diffusion model
is a denoising schedule as much as it is a weight matrix, and three of these defaults were
measured rather than chosen:

* ``--steps 8``. More denoising steps decode *worse* on this checkpoint, monotonically: 8 steps
  score repetition 0.016 where 160 steps score 0.084, and `confidence` at any step count scores
  0.29–0.61. Measured twice, at two scales, in opposite corners of the sweep. 8 steps is also
  20× cheaper than 160, so the better setting is the faster one.
* ``--schedule gumbel --gumbel 2``. The two schedules the design preregistered — `random` and
  `confidence` — are the *limits* of one family, and both fail, in opposite directions. The
  interior is where real Urdu clauses come out.
* ``</s>`` is forbidden. On a fixed-width canvas with no context, the end-of-sequence token is
  47% of first commits, and forbidding it moves the Arabic-script share of the output from 0.000
  to 1.000. Nothing about that is a default worth hiding, so it is stated here.

The AR model ignores ``--steps``, ``--schedule`` and ``--gumbel``: it decodes left to right and
stops when it emits `</s>`. That asymmetry is a property of the factorization, not a defect —
a diffusion decode is told the width of its answer before its first forward pass and an AR decode
chooses its own.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sentencepiece as spm  # noqa: E402

from ravaan_infer.loader import load  # noqa: E402
from ravaan_infer.sampling import SamplingConfig, build_generator, generate, prompts  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--model", default=".", help="the release directory (holds config.json)")
    ap.add_argument("--prefix", default="", help="Urdu text to continue; empty = unconditional")
    ap.add_argument("--tokens", type=int, default=160, help="canvas width / max new tokens")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--top-p", type=float, default=0.95)
    ap.add_argument("--top-k", type=int, default=0)
    ap.add_argument("--steps", type=int, default=8, help="diffusion only — see the module note")
    ap.add_argument("--schedule", default="gumbel", choices=("confidence", "random", "gumbel"))
    ap.add_argument("--gumbel", type=float, default=2.0)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    arm = load(args.model, device=args.device)
    sp = spm.SentencePieceProcessor(model_file=str(arm.tokenizer_path))
    print(arm.describe(), file=sys.stderr)
    print(f"device {args.device} · {args.samples} sample(s)\n", file=sys.stderr)

    prefix_ids = sp.encode(args.prefix) if args.prefix else []
    # top_k=0 disables it; None is not a valid value here.
    cfg = SamplingConfig(
        temperature=args.temperature, top_k=args.top_k, top_p=args.top_p
    )
    # `</s>` joins `<mask>` and `<pad>` on the forbidden list for the diffusion arm only: on a
    # fixed-width canvas it is not a stop signal, it is a token that wins 47% of first commits.
    forbid = arm.forbidden + ((arm.eos_id,) if arm.arm == "diff" else ())

    for i in range(args.samples):
        generator = build_generator(args.device, args.seed + i)
        if arm.arm == "diff":
            prompt = prompts.lm(
                arm.framing,
                "diff",
                prefix=prefix_ids,
                length=len(prefix_ids) + 1 + args.tokens,
                mask_id=arm.mask_id,
            )
            out = generate(
                arm.model,
                prompt,
                config=cfg,
                steps=args.steps,
                schedule=args.schedule,
                gumbel=args.gumbel,
                forbid=forbid,
                generator=generator,
            )
        else:
            prompt = prompts.lm(arm.framing, "ar", prefix=prefix_ids)
            out = generate(
                arm.model,
                prompt,
                config=cfg,
                max_new_tokens=args.tokens,
                forbid=forbid,
                eos_id=arm.eos_id,
                generator=generator,
            )

        ids = [int(t) for t in out.tokens[0]]
        # Drop the framing piece and anything the tokenizer treats as control, so what prints is
        # the text rather than the scaffolding the model was prompted with.
        text = sp.decode([t for t in ids if t >= len(arm.framing.PIECES) + 4])
        print(f"--- sample {i + 1} " + "-" * 50)
        print(text.strip())
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
