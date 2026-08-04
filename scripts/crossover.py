#!/usr/bin/env python
"""Where does a given training budget sit relative to the predicted AR/diffusion crossover?

Reproduces the arithmetic in reports/literature_review.md §2.3 and §3.

Prabhudesai et al. (arXiv:2507.15857), Figure 6, fit a critical-compute threshold above which
masked diffusion is predicted to overtake autoregression in data-constrained training:

    log10(U) = 0.460 * log10(C) - 1.050        U in RAW unique tokens, C in FLOPs
    Ccrit(U) = 2.12 x 10^1.956 * U^2.174       equivalent closed form

Both forms are quoted verbatim from the paper and agree to within 1%.

VERIFIED 2026-08-03 against the typeset PDF. An earlier draft used -7.052, which is the same fit
with U expressed in millions (7.052 - 1.050 = 6.002 = log10(1e6)); it gave the same answers, but
the units were unstated. Raw tokens, matching the paper, are used here.

The unit check below is the reason to trust the reading: the paper's own maximum budget
(100M params x 80B tokens) lands within 2% of its own predicted crossover at U = 100M.

    python scripts/crossover.py                       # PRD v2.0 as written — reproduces Finding A
    python scripts/crossover.py --params 70e6 --unique 25e6 --epochs 396   # v2.1 arm A
    python scripts/crossover.py --params 70e6 --unique 100e6 --epochs 99   # v2.1 arm B
    python scripts/crossover.py --params 70e6 --unique 75e6 --epochs 132   # Finding R's alternative
"""

from __future__ import annotations

import argparse
import math
import sys

# Fitted constants from arXiv:2507.15857 Figure 6. U in raw tokens, C in FLOPs.
SLOPE = 0.460
INTERCEPT = 1.050

# The paper's own setup, used as a unit check.
PAPER_PARAMS = 100e6
PAPER_UNIQUE = 100e6
PAPER_MAX_EPOCHS = 800


def compute_flops(params: float, tokens_processed: float) -> float:
    """Standard C = 6ND transformer training-compute approximation."""
    return 6 * params * tokens_processed


def critical_compute(unique_tokens: float) -> float:
    """FLOPs at which diffusion is predicted to overtake AR for this unique-data budget."""
    return 10 ** ((math.log10(unique_tokens) + INTERCEPT) / SLOPE)


def critical_unique(flops: float) -> float:
    """Unique-token budget whose predicted crossover sits at this compute."""
    return 10 ** (SLOPE * math.log10(flops) - INTERCEPT)


def critical_compute_closed_form(unique_tokens: float) -> float:
    """The paper's closed form, kept as an independent check on the log-linear fit."""
    return 2.12 * 10**1.956 * unique_tokens**2.174


def unit_check() -> None:
    theirs = compute_flops(PAPER_PARAMS, PAPER_UNIQUE * PAPER_MAX_EPOCHS)
    crit = critical_compute(PAPER_UNIQUE)
    closed = critical_compute_closed_form(PAPER_UNIQUE)
    print("UNIT CHECK — the paper's own budget against its own fit")
    print(f"  100M params x {PAPER_MAX_EPOCHS} epochs over U=100M = {theirs:.3e} FLOPs")
    print(f"  C_crit(U=100M)  log-linear fit                     = {crit:.3e} FLOPs")
    print(f"  C_crit(U=100M)  closed form                        = {closed:.3e} FLOPs")
    print(f"  the two forms agree to {abs(crit - closed) / crit * 100:.1f}%")
    print(f"  ratio budget/crit = {theirs / crit:.2f}x  (≈1: their max sits on their crossover)\n")


def report(params: float, unique: float, epochs: float) -> None:
    processed = unique * epochs
    c = compute_flops(params, processed)
    crit = critical_compute(unique)

    print("BUDGET")
    print(f"  parameters        {params / 1e6:.0f}M")
    print(f"  unique tokens U   {unique / 1e6:.0f}M")
    print(f"  epochs            {epochs:.0f}  ->  {processed / 1e9:.1f}B tokens processed")
    print(f"  compute C = 6ND   {c:.3e} FLOPs")
    print(f"  C_crit(U)         {crit:.3e} FLOPs")

    if c >= crit:
        print(f"  REACHES the predicted crossover ({c / crit:.2f}x past it)\n")
    else:
        needed = crit / (6 * params) / unique
        print(f"  SHORT of the predicted crossover by {crit / c:.0f}x")
        print(f"  would need ~{needed:,.0f} epochs at this U\n")

    print(f"  At C = {c:.2e}, the crossover is predicted at U = {critical_unique(c) / 1e6:.0f}M\n")

    print(f"SWEEP — same {params / 1e6:.0f}M params, same {processed / 1e9:.1f}B tokens processed")
    print(f"  {'U':>10} {'epochs':>8} {'C_crit':>11} {'C/C_crit':>10}")
    for u in (10e6, 25e6, 50e6, 100e6, 200e6, 300e6):
        cc = critical_compute(u)
        mark = "reaches" if c >= cc else ""
        print(f"  {u / 1e6:>9.0f}M {processed / u:>8.0f} {cc:>11.2e} {c / cc:>9.2f}x  {mark}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--params", type=float, default=70e6, help="parameter count (default 70e6)")
    parser.add_argument("--unique", type=float, default=300e6, help="unique tokens (default 300e6)")
    parser.add_argument("--epochs", type=float, default=33, help="epochs (default 33)")
    parser.add_argument("--no-unit-check", action="store_true")
    args = parser.parse_args(argv)

    # Windows picks cp1252 for a redirected stdout, and this script prints "≈", "→" and "×".
    # reports/splits.md §1 tells the reader to run this command; piping it to a file must not be
    # the thing that breaks it. Same class as session 4's CRLF bug: a platform default reaching
    # output the pipeline is expected to produce.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if not args.no_unit_check:
        unit_check()
    report(args.params, args.unique, args.epochs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
