"""Metrics and test-set harnesses (PRD §8).

Two pieces so far.

* :mod:`ravaan.evaluation.generation` — §8.3's open-generation metrics, the three G3's coherence
  read needs, built in session 22 alongside the sampler, plus three added on 2026-09-24/25 that
  are properties of *how* a sample was written rather than of the string: `commit_order`,
  `prefix_echo` and `same_pass`. They exist because the three did not merely miss the defect a
  fluent reader reported on the published demo — distinct-1 ranked the two decoders in the
  opposite order.
* :mod:`ravaan.evaluation.lexicon` — added 2026-09-25, and the only metric here that consults
  something outside the sample: is the word a word? Every other number is computed from the
  string alone, and a fabricated word is script-consistent, unrepeated and invisible to all of
  them. The rate is read against a **control** — real held-out Urdu on the same instrument —
  because a corpus never contains every word a real writer uses.
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
    same_pass,
)
from ravaan.evaluation.infill import InfillItem, InfillScore, token_f1, truncate_to_gold
from ravaan.evaluation.lexicon import Fabrication, Lexicon

__all__ = [
    "Fabrication",
    "GenerationStats",
    "InfillItem",
    "InfillScore",
    "Lexicon",
    "commit_order",
    "longest_repeated_run",
    "prefix_echo",
    "same_pass",
    "token_f1",
    "truncate_to_gold",
]
