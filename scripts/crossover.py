#!/usr/bin/env python
"""Where does a given training budget sit relative to the predicted AR/diffusion crossover?

Reproduces the arithmetic in reports/literature_review.md §2.3 and §3.

Prabhudesai et al. (arXiv:2507.15857) fit a critical-compute threshold above which masked diffusion
is predicted to overtake autoregression in data-constrained training:

    log10(U) = 0.460 * log10(C) - 7.052        U in millions of unique tokens, C in FLOPs

The unit check below is the reason to trust that reading: the paper's own maximum budget
(100M params x 80B tokens) lands within 1% of its own predicted crossover at U = 100M.

    python scripts/crossover.py                       # Ravaan as specified in PRD v2
    python scripts/crossover.py --params 70e6 --unique 25e6 --epochs 400

CAVEAT: the fitted constants are pending verification against the typeset PDF -- see open item 1
in the literature review. Treat the outputs as order-of-magnitude guidance, not precision figures.
"""

from __future__ import annotations

import argparse
import math

# Fitted constants from arXiv:2507.15857. See caveat above.
SLOPE = 0.460
INTERCEPT = 7.052

# The paper's own setup, used as a unit check.
PAPER_PARAMS = 100e6
PAPER_UNIQUE = 100e6
PAPER_MAX_EPOCHS = 800


def compute_flops(params: float, tokens_processed: float) -> float:
    """Standard C = 6ND transformer training-compute approximation."""
    return 6 * params * tokens_processed


def critical_compute(unique_tokens: float) -> float:
    """FLOPs at which diffusion is predicted to overtake AR for this unique-data budget."""
    return 10 ** ((math.log10(unique_tokens / 1e6) + INTERCEPT) / SLOPE)


def critical_unique(flops: float) -> float:
    """Unique-token budget whose predicted crossover sits at this compute."""
    return 10 ** (SLOPE * math.log10(flops) - INTERCEPT) * 1e6


def unit_check() -> None:
    theirs = compute_flops(PAPER_PARAMS, PAPER_UNIQUE * PAPER_MAX_EPOCHS)
    crit = critical_compute(PAPER_UNIQUE)
    print("UNIT CHECK — the paper's own budget against its own fit")
    print(f"  100M params x {PAPER_MAX_EPOCHS} epochs over U=100M = {theirs:.3e} FLOPs")
    print(f"  C_crit(U=100M)                                     = {crit:.3e} FLOPs")
    print(f"  ratio = {theirs / crit:.2f}x  (≈1 confirms U is in millions and C in FLOPs)\n")


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

    if not args.no_unit_check:
        unit_check()
    report(args.params, args.unique, args.epochs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
