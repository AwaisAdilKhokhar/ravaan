"""Metrics and test-set harnesses (PRD §8).

Two pieces so far.

* :mod:`ravaan.evaluation.generation` — §8.3's open-generation metrics, the three G3's coherence
  read needs, built in session 22 alongside the sampler, plus two added on 2026-09-24 that are
  properties of *how* a sample was written rather than of the string: `commit_order` and
  `prefix_echo`. They exist because the three did not merely miss the defect a fluent reader
  reported on the published demo — distinct-1 ranked the two decoders in the opposite order.
* :mod:`ravaan.evaluation.infill` — §8.3's infill exact-match and token-F1, and the truncation
  rule preregistration §8 committed to on 2026-09-13. Built in session 24 because open question 5
  (the infilling share) cannot be answered without it, and because a preregistered scoring rule
  with no implementation is a promise nobody has checked is keepable.

Still Week 12's, and still waiting on §8.2's test sets rather than on code: transliteration
CER/WER/chrF, and restoration CER reduction with punctuation/whitespace F1. Two of §8.2's five
test sets do not exist yet.
"""

from ravaan.evaluation.generation import (
    GenerationStats,
    commit_order,
    longest_repeated_run,
    prefix_echo,
)
from ravaan.evaluation.infill import InfillItem, InfillScore, token_f1, truncate_to_gold

__all__ = [
    "GenerationStats",
    "InfillItem",
    "InfillScore",
    "commit_order",
    "longest_repeated_run",
    "prefix_echo",
    "token_f1",
    "truncate_to_gold",
]
