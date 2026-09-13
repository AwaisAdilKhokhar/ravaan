"""Metrics and test-set harnesses (PRD §8).

Only §8.3's open-generation metrics so far — the three that G3's coherence read needs, built in
session 22 alongside the sampler. The task metrics (transliteration CER/WER/chrF, restoration CER
reduction and punctuation/whitespace F1, infill exact-match and token-F1) are Week 12's, and they
wait on §8.2's test sets rather than on code: two of the five do not exist yet.
"""

from ravaan.evaluation.generation import GenerationStats, longest_repeated_run

__all__ = ["GenerationStats", "longest_repeated_run"]
