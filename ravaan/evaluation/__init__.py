"""Metrics and test-set harnesses (PRD §8).

Two pieces so far.

* :mod:`ravaan.evaluation.generation` — §8.3's open-generation metrics, the three G3's coherence
  read needs, built in session 22 alongside the sampler.
* :mod:`ravaan.evaluation.infill` — §8.3's infill exact-match and token-F1, and the truncation
  rule preregistration §8 committed to on 2026-09-13. Built in session 24 because open question 5
  (the infilling share) cannot be answered without it, and because a preregistered scoring rule
  with no implementation is a promise nobody has checked is keepable.

Still Week 12's, and still waiting on §8.2's test sets rather than on code: transliteration
CER/WER/chrF, and restoration CER reduction with punctuation/whitespace F1. Two of §8.2's five
test sets do not exist yet.
"""

from ravaan.evaluation.generation import GenerationStats, longest_repeated_run
from ravaan.evaluation.infill import InfillItem, InfillScore, token_f1, truncate_to_gold

__all__ = [
    "GenerationStats",
    "InfillItem",
    "InfillScore",
    "longest_repeated_run",
    "token_f1",
    "truncate_to_gold",
]
