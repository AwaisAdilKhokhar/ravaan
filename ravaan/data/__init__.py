"""Corpus pipeline: acquisition, normalization, langid, dedup, quality, corruption, packing.

Stage 3's reader (`ravaan.data.shards`) is deliberately *not* re-exported here: importing it
pulls in parquet support from the `[data]` extra, and the stages that decide what the corpus
contains should stay importable without it.
"""

from ravaan.data.langid import (
    LANGID_VERSION,
    LangIDConfig,
    LangIDLog,
    LangIDResult,
    classify,
    script_ratios,
)
from ravaan.data.normalization import (
    NORMALIZER_VERSION,
    NormalizationConfig,
    NormalizationLog,
    NormalizationResult,
    normalize,
    normalize_text,
)
from ravaan.data.quality import (
    QUALITY_VERSION,
    QualityConfig,
    QualityLog,
    QualityMetrics,
    QualityResult,
    check,
    measure,
)

__all__ = [
    "LANGID_VERSION",
    "NORMALIZER_VERSION",
    "QUALITY_VERSION",
    "LangIDConfig",
    "LangIDLog",
    "LangIDResult",
    "NormalizationConfig",
    "NormalizationLog",
    "NormalizationResult",
    "QualityConfig",
    "QualityLog",
    "QualityMetrics",
    "QualityResult",
    "check",
    "classify",
    "measure",
    "normalize",
    "normalize_text",
    "script_ratios",
]
