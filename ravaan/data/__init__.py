"""Corpus pipeline: acquisition, normalization, langid, dedup, quality, corruption, packing.

Stage 3's reader (`ravaan.data.shards`) is deliberately *not* re-exported here: importing it
pulls in parquet support from the `[data]` extra, and the stages that decide what the corpus
contains should stay importable without it.
"""

from ravaan.data.decontamination import (
    DECONTAMINATION_VERSION,
    ContaminationHit,
    DecontaminationConfig,
    DecontaminationLog,
    DecontaminationVerdict,
    Decontaminator,
    EvalSetSpec,
    decontaminate,
)
from ravaan.data.dedup import (
    DEDUP_VERSION,
    DedupConfig,
    DedupLog,
    DedupVerdict,
    ExactDeduplicator,
    deduplicate,
)
from ravaan.data.langid import (
    LANGID_VERSION,
    LangIDConfig,
    LangIDLog,
    LangIDResult,
    classify,
    script_ratios,
)
from ravaan.data.minhash import (
    MINHASH_VERSION,
    MinHashConfig,
    MinHashDeduplicator,
    MinHashLog,
    NearDuplicateVerdict,
    near_deduplicate,
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
    "DECONTAMINATION_VERSION",
    "DEDUP_VERSION",
    "LANGID_VERSION",
    "MINHASH_VERSION",
    "NORMALIZER_VERSION",
    "QUALITY_VERSION",
    "ContaminationHit",
    "DecontaminationConfig",
    "DecontaminationLog",
    "DecontaminationVerdict",
    "Decontaminator",
    "DedupConfig",
    "DedupLog",
    "DedupVerdict",
    "EvalSetSpec",
    "ExactDeduplicator",
    "LangIDConfig",
    "LangIDLog",
    "LangIDResult",
    "MinHashConfig",
    "MinHashDeduplicator",
    "MinHashLog",
    "NearDuplicateVerdict",
    "NormalizationConfig",
    "NormalizationLog",
    "NormalizationResult",
    "QualityConfig",
    "QualityLog",
    "QualityMetrics",
    "QualityResult",
    "check",
    "classify",
    "decontaminate",
    "deduplicate",
    "measure",
    "near_deduplicate",
    "normalize",
    "normalize_text",
    "script_ratios",
]
