"""MinHash near-deduplication — stage 7 of the corpus pipeline (PRD §6.3.7).

Stage 6 answered "are these the same bytes". Stage 7 answers "are these the same document", which
is a different question with a *threshold* in it, and the threshold is the whole design problem.
Session 8 handed this stage four measured expectations before a line of it existed, and the module
is shaped by all four:

* **Finding H — the primary source is already near-deduplicated.** FineWeb2 removed 31.02% of
  ``urd_Arab`` by its own MinHash pass before we ever saw the shard. Stage 7 should be reported as
  an *assertion* on FineWeb2 unless it demonstrably is not — the same shape as stages 2, 3 and 5.
* **Finding I — the Wikipedia stub farm is out of reach at any shingle size.** 82 US-geography
  stubs, 3,321 pairs, word-shingle Jaccard topping out at 0.677 (n=2) and 0.423 (n=5). A stage 7
  built at the conventional 0.8 will not touch them, and that is the *expected* result.
* **Finding L — the one population with real work in it** is Urdu Wikipedia articles that also sit
  inside FineWeb2 as crawled HTML. Same content, different rendering, never byte-identical.
* **Finding G — a pair statistic cannot be measured on a sample.** Sampling at rate *r* retains a
  pair with probability *r²*. The exception that makes this affordable is cross-source: index one
  source whole, sample the other, and a shared document is found with probability *r*.

Four properties this module is built around.

**1. The estimator is one-permutation hashing with densification, not k-permutation MinHash.**
Classic MinHash applies *K* permutations to every shingle: at K=128 over the ~350 word-5-grams in
an average FineWeb2 document that is ~45,000 modular operations per document, and the deciding
stages are standard-library-only by doctrine (§13's argument — no numpy in the code that decides
what the corpus is), so the constant factor *is* the design. One-permutation hashing (Shrivastava &
Li) hashes each shingle **once**, bins it into one of *K* buckets and keeps the per-bucket minimum;
empty buckets are filled by densification from a fixed random probe order, which is what keeps the
collision probability equal to Jaccard. Measured here, that is the difference between ~3.6 ms and
~0.25 ms per document — hours against minutes for a full-shard pass. Unbiasedness is not asserted:
:mod:`tests.test_minhash` checks the estimate against *exact* Jaccard on real Urdu.

**2. Jaccard decides; containment is measured beside it.** This is Finding L's requirement, and it
is the same move stage 6 makes with raw-vs-normalized hashes. Jaccard is symmetric and is what a
removal decision should rest on. But Finding L's population is a Wikipedia article *contained in* a
rendered page carrying navigation chrome, and containment is structurally invisible to Jaccard: an
800-shingle page holding a 500-shingle article verbatim scores J = 0.63 while containing 100% of
it. Both numbers are reported for every candidate pair, from the same sketch, because stage 8's
decontamination is the consumer and §6.3.8's "hash + fuzzy match" now has a measured reason to
exist (Finding L: the hash half returns a confident zero on exactly this path).

**3. Which copy survives does not depend on read order — the same rule as stage 6, the same
primitive.** Clusters are connected components over verified pairs, and a component's survivor is
its lowest-:func:`~ravaan.data.dedup.document_key` member. That function is *imported* rather than
reimplemented: a corpus released as code + manifest + checksums is only reconstructible if both
dedup stages agree about which of two documents is the canonical one. Bucket representatives are
chosen the same way, so even the candidate set is a function of the corpus rather than of the pass.

**4. Stage 7 is single-pass, and that is a real difference from stage 6.** Stage 6 stores one
integer per distinct *content* and pays a second read of the corpus to stay order-independent.
Stage 7 cannot: comparing documents to each other means holding a sketch per *document*, so the
ids are already in memory and the second pass would buy nothing. The cost is memory, stated rather
than discovered — 512 bytes of signature plus ~180 bytes of bookkeeping per document at K=128, so
~1 GB for a full 1.5M-document FineWeb2 shard — and ``max_index_entries`` fails loudly at a named
ceiling rather than swapping.

**The threshold is not inherited.** 0.8 is what RefinedWeb and FineWeb use and it is the shipped
default, but session 6's lesson is that every stage-5 threshold which survived the distribution
still had to be moved by documents. So the pass retains every candidate pair above
``retain_pairs_above`` with its measured similarity, :meth:`MinHashDeduplicator.sweep` re-clusters
at any threshold from that one pass, and :meth:`MinHashDeduplicator.pair_examples` hands back pairs
to read at each similarity band. Pick the number after reading them, not before.

    index = MinHashDeduplicator()
    for doc in corpus:                                    # one pass
        index.index(doc.doc_id, normalized(doc), source=doc.source)
    index.build()                                         # band, verify, cluster
    verdict = index.verdict("urdu-wikipedia:122264")
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import sys
from array import array
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ravaan.console import pin_utf8_streams
from ravaan.data.dedup import canonical, document_key

__all__ = [
    "MINHASH_VERSION",
    "MinHashConfig",
    "MinHashDeduplicator",
    "MinHashLog",
    "NearDuplicateVerdict",
    "PairExample",
    "containment_from_jaccard",
    "jaccard",
    "near_deduplicate",
    "shingle_hashes",
    "shingles",
]

# Bump on any change to which documents survive: the shingling, the sketch, the survivor rule.
# The manifest records it, so a frozen corpus can be traced to the exact pass that produced it.
MINHASH_VERSION = "1.0.0"

# Two keyed spaces out of one primitive, as in stage 6: shingle hashes feed the sketch, band keys
# group the sketches. Nothing good happens if a shingle can collide with a band.
_SHINGLE_PERSON = b"ravaan/mh/s"

# Strictly greater than any 32-bit signature value, so "empty" needs no separate bitmap and `min`
# works on a freshly-initialised bin without a branch. Densification restores the invariant that
# every entry is < 2**32 before a signature is packed.
_EMPTY = 1 << 32
_MASK32 = 0xFFFFFFFF

SHINGLE_UNITS = ("word", "char")


# ---------------------------------------------------------------------------
# Shingling
# ---------------------------------------------------------------------------


def shingles(text: str, *, size: int = 5, unit: str = "word") -> Iterator[str]:
    """The overlapping n-grams a document is compared as.

    Shingled from the *same canonical form stage 6 hashes* — whitespace collapsed, case folded —
    so the two dedup stages agree about what a document is. A stage 7 that shingled raw text would
    call two documents different for a line break that stage 6 had already ruled irrelevant, which
    is not a near-dedup finding, it is two stages disagreeing.

    Words, not characters, by default. Finding I's measurements are word-shingle Jaccard, so the
    numbers this stage is accepted against are in the same unit; and word shingles are what
    RefinedWeb and FineWeb's own passes use, which matters because Finding H says FineWeb2 already
    ran one and stage 7 has to be comparable to it. ``unit="char"`` exists for the sentence-unit
    sources, where a 10-word row has six word-5-grams and nothing to estimate from.
    """
    if unit not in SHINGLE_UNITS:
        raise ValueError(f"unit must be one of {SHINGLE_UNITS}, got {unit!r}")
    if size < 1:
        raise ValueError(f"shingle size must be >= 1, got {size}")
    clean = canonical(text)
    if unit == "char":
        for i in range(len(clean) - size + 1):
            yield clean[i : i + size]
        return
    words = clean.split(" ")
    if not words or words == [""]:
        return
    for i in range(len(words) - size + 1):
        yield " ".join(words[i : i + size])


def shingle_hashes(text: str, *, size: int = 5, unit: str = "word") -> set[int]:
    """Distinct shingles as 64-bit hashes — the set MinHash actually estimates over.

    A *set*, so a phrase repeated ten times in one document counts once. That is what Jaccard is
    defined over, and it is also why stage 5's within-document repetition rules and stage 7 do not
    double-count the same house style.
    """
    digest = hashlib.blake2b
    return {
        int.from_bytes(
            digest(shingle.encode("utf-8"), digest_size=8, person=_SHINGLE_PERSON).digest(), "big"
        )
        for shingle in shingles(text, size=size, unit=unit)
    }


def jaccard(left: set[int], right: set[int]) -> float:
    """Exact Jaccard. The thing the sketch estimates, used by the tests to check that it does."""
    if not left and not right:
        return 1.0
    union = len(left | right)
    return len(left & right) / union if union else 0.0


def containment_from_jaccard(estimate: float, left_size: int, right_size: int) -> float:
    """|A ∩ B| / min(|A|, |B|), derived from a Jaccard estimate and the two set sizes.

    Free, because the sketch already needs the sizes and the algebra is exact:
    ``|A ∩ B| = J·(|A| + |B|) / (1 + J)``. Finding L is why it is here — a Wikipedia article sitting
    verbatim inside its own crawled-and-rendered copy is 100% contained and scores well under 0.7
    on Jaccard, because the chrome is in the union. Clamped to 1.0: the intersection is estimated,
    so it can come out a little larger than the smaller set.
    """
    smaller = min(left_size, right_size)
    if smaller <= 0:
        return 0.0
    intersection = estimate * (left_size + right_size) / (1.0 + estimate)
    return min(1.0, intersection / smaller)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MinHashConfig:
    """Stage 7 settings. Defaults are the Ravaan corpus v1 settings."""

    # K. 128 bins is 512 bytes of signature per document and a standard error on the Jaccard
    # estimate of sqrt(J(1-J)/K) — about 0.035 at J = 0.8, which is well inside the width of the
    # band the threshold has to be chosen from.
    num_bins: int = 128

    # bands * rows must equal num_bins. (32, 4) puts the LSH S-curve's inflection at
    # (1/32)^(1/4) = 0.420, far below similarity_threshold, because banding is the recall stage and
    # verification is the precision stage — and verification here is *exact* against the full
    # signature, so a wide net costs almost nothing and a narrow one cannot be undone.
    #
    # **The two settings agree about removals and differ about what can be measured.** Run on the
    # complete Urdu Wikipedia dump at threshold 0.80, the textbook (16, 8) and this (32, 4) produce
    # **118 clusters** either way, removing 178 and 179 documents — the same corpus to within one
    # document. So this is not chosen for recall at the threshold, and a claim that it was would be
    # wrong.
    #
    # It is chosen for the *sweep*. Picking a threshold means looking at what clustering would do
    # at 0.5, 0.6, 0.7 as well as 0.8, and (16, 8) cannot answer: its inflection is 0.707 and its
    # recall at J = 0.5 is **6%**, so every row of a sweep below ~0.7 would be measuring the bands
    # rather than the corpus. (32, 4) has inflection 0.420 and 87% recall at J = 0.5, which makes
    # the sweep honest over the whole range a threshold could plausibly be chosen from — and that
    # range is exactly where Finding L's asymmetric wiki-against-crawled-page pairs live.
    #
    # The cost is candidates, and it is affordable: 60,355 proposed on Urdu Wikipedia against 240
    # that verify at 0.80, a banding precision of 0.004. Verification is exact and is 128
    # byte-slice comparisons, so 60,355 of them is about a second.
    bands: int = 32
    rows: int = 4

    shingle_size: int = 5
    shingle_unit: str = "word"

    # Below this a document is not compared at all — it is kept, and counted as skipped. With
    # 5-word shingles a 400-character document (stage 5's floor) has ~79 of them; at 8 the estimate
    # is coarse but real, and beneath it Jaccard can only take a handful of discrete values, so a
    # threshold comparison is measuring granularity rather than similarity. Stage 7 must not delete
    # what it cannot measure.
    min_shingles: int = 8

    # Provisional until a pass has been read. RefinedWeb and FineWeb both use 0.8 and Finding I's
    # acceptance test is written against it, but session 6's lesson stands: every stage-5 threshold
    # that survived the distribution still had to be moved by documents. Use `sweep()` and
    # `pair_examples()` and then decide.
    similarity_threshold: float = 0.8

    # Every candidate pair at or above this is retained with its measured similarity, which is what
    # makes `sweep()` exact rather than a re-run. Below the banding inflection (0.707) candidates
    # are too sparse to sweep over anyway, so 0.5 keeps the whole usable range and a margin.
    retain_pairs_above: float = 0.5

    # Three ceilings, all so a pass fails loudly at a stated size rather than swapping. At K=128 a
    # document costs 512 bytes of signature plus ~180 of bookkeeping, so 8M is ~5.5 GB and a full
    # 1.5M-document FineWeb2 shard is ~1 GB. A retained pair costs 9 bytes across three arrays; a
    # seen pair costs ~60 as a set entry, which is the price of counting each pair once instead of
    # once per band that happened to collide on it.
    max_index_entries: int = 8_000_000
    max_retained_pairs: int = 40_000_000
    max_candidate_pairs: int = 20_000_000

    # Fixes the densification probe order. Part of the fingerprint because two seeds give two
    # different (both valid) estimators, and a frozen corpus must name the one that produced it.
    seed: int = 0

    def __post_init__(self) -> None:
        if self.num_bins < 8:
            raise ValueError(f"num_bins must be >= 8, got {self.num_bins}")
        if self.bands < 1 or self.rows < 1:
            raise ValueError("bands and rows must both be >= 1")
        if self.bands * self.rows != self.num_bins:
            raise ValueError(
                f"bands * rows must equal num_bins: {self.bands} * {self.rows} "
                f"= {self.bands * self.rows} != {self.num_bins}"
            )
        if self.shingle_unit not in SHINGLE_UNITS:
            raise ValueError(
                f"shingle_unit must be one of {SHINGLE_UNITS}, got {self.shingle_unit!r}"
            )
        if self.shingle_size < 1:
            raise ValueError(f"shingle_size must be >= 1, got {self.shingle_size}")
        if self.min_shingles < 1:
            raise ValueError("min_shingles must be >= 1 — a document with no shingles has no size")
        if not 0.0 < self.similarity_threshold <= 1.0:
            raise ValueError(
                f"similarity_threshold must be in (0, 1], got {self.similarity_threshold}"
            )
        if not 0.0 <= self.retain_pairs_above <= self.similarity_threshold:
            raise ValueError(
                "retain_pairs_above must be in [0, similarity_threshold] — retaining fewer pairs "
                "than the threshold uses would make sweep() silently incomplete"
            )
        if min(self.max_index_entries, self.max_retained_pairs, self.max_candidate_pairs) < 1:
            raise ValueError("the max_* ceilings must all be >= 1")

    @property
    def band_threshold(self) -> float:
        """Where the LSH S-curve turns over: ``(1 / bands) ** (1 / rows)``.

        Reported rather than configured. It is the similarity below which candidates stop being
        generated reliably, so a ``similarity_threshold`` set under it is asking the bands for pairs
        they were not built to find, and the run should say so instead of quietly under-reporting.
        """
        return (1.0 / self.bands) ** (1.0 / self.rows)

    def candidate_probability(self, similarity: float) -> float:
        """P(a pair at this similarity becomes a candidate) — the S-curve, for the report."""
        return 1.0 - (1.0 - similarity**self.rows) ** self.bands

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> MinHashConfig:
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known - {"minhash_version", "_comment"}
        if unknown:
            raise ValueError(f"unknown minhash config keys: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json_file(cls, path: str | Path) -> MinHashConfig:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json_file(self, path: str | Path) -> None:
        payload = {"minhash_version": MINHASH_VERSION, **self.to_dict()}
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"version": MINHASH_VERSION, **self.to_dict()}, sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NearDuplicateVerdict:
    """One document's fate, with the cluster that decided it."""

    doc_id: str
    kept: bool
    cluster: int = -1  # -1 when the document is its own cluster or was never compared
    cluster_size: int = 1
    reason: str = ""  # "" | "near_duplicate" | "too_few_shingles"

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "kept": self.kept,
            "cluster": self.cluster,
            "cluster_size": self.cluster_size,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class PairExample:
    """A measured candidate pair, kept so a threshold is chosen by reading rather than by taste."""

    left: str
    right: str
    similarity: float
    containment: float
    left_shingles: int
    right_shingles: int
    left_source: str = ""
    right_source: str = ""

    def to_dict(self) -> dict:
        return {
            "left": self.left,
            "right": self.right,
            "similarity": round(self.similarity, 4),
            "containment": round(self.containment, 4),
            "left_shingles": self.left_shingles,
            "right_shingles": self.right_shingles,
            "left_source": self.left_source,
            "right_source": self.right_source,
            "cross_source": bool(
                self.left_source and self.right_source and self.left_source != self.right_source
            ),
        }


@dataclass
class MinHashLog:
    """Corpus-level aggregate — the stage-7 line of the manifest and the statistics table."""

    config: MinHashConfig = field(default_factory=MinHashConfig)

    # --- what was sketched ---
    indexed: int = 0
    eligible: int = 0
    skipped_short: int = 0  # below min_shingles: kept, never compared, counted
    shingles_total: int = 0
    # Sketched, then un-indexed by drop() because an earlier stage had removed them. Reported so
    # `indexed` — which drop() decrements — can be reconciled against the documents the pass read.
    dropped_before_build: int = 0

    # --- what banding proposed and verification kept ---
    candidate_pairs: int = 0
    verified_pairs: int = 0
    retained_pairs: int = 0  # at or above retain_pairs_above, i.e. what sweep() can see

    # --- clusters ---
    clusters: int = 0  # components with more than one member
    duplicate_documents: int = 0
    largest_cluster: int = 0
    cross_source_clusters: int = 0
    cross_source_pairs: Counter[str] = field(default_factory=Counter)

    # --- what it cost ---
    documents_kept: int = 0
    chars_in: int = 0
    chars_kept: int = 0
    by_source: Counter[str] = field(default_factory=Counter)
    kept_by_source: Counter[str] = field(default_factory=Counter)
    removed_by_source: Counter[str] = field(default_factory=Counter)
    removed_cross_source_by_source: Counter[str] = field(default_factory=Counter)

    # --- the distributions the threshold decision is made from ---
    similarity_histogram: Counter[str] = field(default_factory=Counter)
    containment_histogram: Counter[str] = field(default_factory=Counter)

    @property
    def keep_rate(self) -> float:
        return self.documents_kept / self.indexed if self.indexed else 0.0

    @property
    def char_keep_rate(self) -> float:
        return self.chars_kept / self.chars_in if self.chars_in else 0.0

    @property
    def duplicate_rate(self) -> float:
        return self.duplicate_documents / self.indexed if self.indexed else 0.0

    @property
    def band_precision(self) -> float:
        """Share of banding's candidates that survived verification.

        The one number that says whether the LSH parameters are doing their job on *this* corpus
        rather than on the S-curve's assumptions. A precision near 1.0 means the bands are tuned
        tighter than the threshold and pairs near it are being missed; near 0 means the run spent
        its time verifying noise.
        """
        return self.verified_pairs / self.candidate_pairs if self.candidate_pairs else 0.0

    def to_dict(self) -> dict:
        config = self.config
        return {
            "minhash_version": MINHASH_VERSION,
            "config_fingerprint": config.fingerprint(),
            "config": config.to_dict(),
            "band_threshold": round(config.band_threshold, 4),
            "candidate_probability_at_threshold": round(
                config.candidate_probability(config.similarity_threshold), 6
            ),
            "indexed": self.indexed,
            "eligible": self.eligible,
            "skipped_short": self.skipped_short,
            "dropped_before_build": self.dropped_before_build,
            "shingles_total": self.shingles_total,
            "mean_shingles": (
                round(self.shingles_total / self.eligible, 2) if self.eligible else 0.0
            ),
            "candidate_pairs": self.candidate_pairs,
            "verified_pairs": self.verified_pairs,
            "retained_pairs": self.retained_pairs,
            "band_precision": round(self.band_precision, 6),
            "clusters": self.clusters,
            "duplicate_documents": self.duplicate_documents,
            "duplicate_rate": round(self.duplicate_rate, 6),
            "largest_cluster": self.largest_cluster,
            "cross_source_clusters": self.cross_source_clusters,
            "cross_source_pairs": dict(sorted(self.cross_source_pairs.items())),
            "documents_kept": self.documents_kept,
            "documents_removed": self.indexed - self.documents_kept,
            "keep_rate": round(self.keep_rate, 6),
            "chars_in": self.chars_in,
            "chars_kept": self.chars_kept,
            "char_keep_rate": round(self.char_keep_rate, 6),
            "by_source": dict(sorted(self.by_source.items())),
            "kept_by_source": dict(sorted(self.kept_by_source.items())),
            "removed_by_source": dict(sorted(self.removed_by_source.items())),
            "removed_cross_source_by_source": dict(
                sorted(self.removed_cross_source_by_source.items())
            ),
            "similarity_histogram": dict(sorted(self.similarity_histogram.items())),
            "containment_histogram": dict(sorted(self.containment_histogram.items())),
        }


# ---------------------------------------------------------------------------
# The deduplicator
# ---------------------------------------------------------------------------


class MinHashDeduplicator:
    """Sketch every document, band, verify, cluster. One pass over the corpus, then :meth:`build`.

    Memory is the constraint rather than time. Per document at K=128: 512 bytes of packed
    signature, the id, 4 bytes of shingle count, 4 of character count and an interned source
    pointer — about 700 bytes with Python's object overhead, so a 1.5M-document FineWeb2 shard
    indexes in roughly 1 GB and ``max_index_entries`` raises rather than swaps.
    """

    def __init__(
        self,
        config: MinHashConfig | None = None,
        *,
        track_sources: bool = True,
        example_clusters: int = 200,
        pair_examples_per_band: int = 12,
    ) -> None:
        self.config = config or MinHashConfig()
        self.track_sources = track_sources
        self.example_clusters = example_clusters
        self.pair_examples_per_band = pair_examples_per_band
        self.log = MinHashLog(config=self.config)

        self._bins = self.config.num_bins
        self._rows = self.config.rows
        self._row_bytes = self.config.rows * 4
        self._probe = _probe_table(self._bins, self.config.seed)

        # Parallel per-document arrays. Parallel rather than a list of records because a dataclass
        # per document is ~500 bytes of overhead on top of the 512 that carry information.
        self._ids: list[str] = []
        self._sigs: list[bytes] = []
        self._sizes = array("I")  # distinct shingles, for containment
        self._chars = array("L")
        self._sources: list[str] = []
        self._eligible: list[int] = []
        self._position: dict[str, int] = {}

        # Retained candidate pairs, for sweep() and pair_examples(). Three typed arrays rather than
        # a list of tuples: 9 bytes a pair against ~150, which is the difference between a sweep
        # being free and a sweep being the reason the pass ran out of memory.
        self._pair_left = array("I")
        self._pair_right = array("I")
        self._pair_agree = array("B")

        self._examples: dict[str, list[tuple[int, int, int]]] = {}
        self._parent: list[int] = []
        self._cluster_of: dict[int, int] = {}
        self._cluster_size: dict[int, int] = {}
        self._removed: set[int] = set()
        # Positions un-indexed by drop(); see its docstring. Never banded, never clustered.
        self._dropped: set[int] = set()
        self._cluster_sources: dict[int, set[str]] = {}
        self._cluster_members: dict[int, list[int]] = {}
        self._cluster_keeper: dict[int, str] = {}
        self._label_size: dict[int, int] = {}
        self._built = False

    # --- phase 1: sketch ---------------------------------------------------

    def index(self, doc_id: str, text: str, *, source: str = "") -> None:
        """Sketch one document. Call over the whole corpus, once, before :meth:`build`.

        ``text`` is the stage-4 output, as everywhere from stage 5 on. Unlike stage 6 there is no
        raw-variant comparison: Finding F's mechanism is *orthographic* — the same word typed on
        two keyboards — and a near-dedup with a 0.8 threshold absorbs that difference whether or not
        stage 4 ran, so the counterfactual stage 6 measures has nothing to measure here.
        """
        if self._built:
            raise RuntimeError(
                "build() has already run — a document indexed now would never be banded, so it "
                "would be reported as kept without ever having been compared to anything"
            )
        if doc_id in self._position:
            raise ValueError(
                f"{doc_id!r} was indexed twice — stage 7 holds one sketch per document, so a "
                "repeated id means the reader emitted the same document under two identities or "
                "the same document twice"
            )
        if len(self._ids) >= self.config.max_index_entries:
            raise MemoryError(
                f"stage 7 index hit max_index_entries={self.config.max_index_entries:,} at "
                f"{self.log.indexed:,} documents — raise it deliberately or shard the pass; it "
                "exists so this fails loudly rather than swaps"
            )

        position = len(self._ids)
        self._position[doc_id] = position
        self._ids.append(doc_id)
        self._sources.append(sys.intern(source) if source else "")
        self._chars.append(len(text))

        self.log.indexed += 1
        self.log.chars_in += len(text)
        if source:
            self.log.by_source[source] += 1

        hashes = shingle_hashes(
            text, size=self.config.shingle_size, unit=self.config.shingle_unit
        )
        self._sizes.append(min(len(hashes), _MASK32))
        if len(hashes) < self.config.min_shingles:
            # Kept, never compared. A document too short to sketch is not a document stage 7 has an
            # opinion about, and quietly clustering it on a handful of shingles would be an opinion.
            self._sigs.append(b"")
            self.log.skipped_short += 1
            return

        self._sigs.append(self._sketch(hashes))
        self._eligible.append(position)
        self.log.eligible += 1
        self.log.shingles_total += len(hashes)

    def drop(self, doc_ids: Iterable[str]) -> int:
        """Un-index documents an earlier stage removed. Before :meth:`build`; returns the count.

        This exists so a driver can read the corpus **once** instead of twice. Stage 6 is two-phase
        by construction — its verdict is a property of a duplicate *group*, so nothing is decided
        until the whole corpus has been indexed — and the obvious consequence was that stage 7 had
        to sketch during stage 6's second pass. But stages 2–5 are ~90% of a pass's cost (profiled:
        stage 5 53%, stage 3 27%, stage 4 9%), so paying them twice to learn nothing new is most of
        the price of a stage-7 run. A driver that sketches everything during phase 1 and then drops
        stage 6's removals here reads the corpus once.

        **The result is identical, by construction rather than by argument.** Dropping happens
        before :meth:`build`, and both :meth:`_band` and :meth:`_cluster` iterate ``_eligible`` —
        so a dropped document is never banded, never proposed as a candidate, never in a component
        and never a keeper. The banding sees exactly the set the two-pass driver would have indexed.
        (Had this dropped *after* clustering it would need a real argument, and the argument would
        have been that identical texts have identical neighbourhoods. It does not, so it does not.)

        What it is not free of is **peak memory**: the sketches of the dropped documents existed
        before they were dropped, at ~512 bytes each. On a source whose exact-duplicate rate is nil
        that costs nothing (FineWeb2 — Finding H: 31% was removed upstream by MinHash before we saw
        it), and on Roman-Urdu-Parl, whose 6.37M rows collapse toward ~3.48M distinct, it is close
        to double. That is a per-source decision and belongs to the caller, which is why nothing
        here does it automatically.
        """
        if self._built:
            raise RuntimeError(
                "build() has already run — dropping now would leave a document that was banded, "
                "clustered and possibly named as a cluster's survivor, which is a corpus whose "
                "keeper is a document no later stage will emit"
            )
        dropped = 0
        for doc_id in doc_ids:
            position = self._position.get(doc_id)
            if position is None:
                raise KeyError(
                    f"{doc_id!r} was not indexed — dropping a document stage 7 never sketched "
                    "means this removal list was computed over a different document set, and the "
                    "quiet answer would be a corpus short by however many ids missed"
                )
            if position in self._dropped:
                continue
            self._dropped.add(position)
            dropped += 1

            log = self.log
            log.indexed -= 1
            log.chars_in -= self._chars[position]
            if self._sources[position]:
                log.by_source[self._sources[position]] -= 1
            if self._sigs[position]:
                log.eligible -= 1
                log.shingles_total -= self._sizes[position]
                # Freeing the signature is the point at which the memory actually comes back, and
                # on a source with a high duplicate rate it is the difference between this mode
                # fitting and not. Cleared after the counters, which read it.
                self._sigs[position] = b""
            else:
                log.skipped_short -= 1

        self._eligible = [p for p in self._eligible if p not in self._dropped]
        self.log.dropped_before_build += dropped
        return dropped

    def _sketch(self, hashes: set[int]) -> bytes:
        """One-permutation hashing with densification — the K-value signature, packed.

        Each shingle is hashed once; the low bits choose its bin and the high bits are its value.
        Bins left empty are filled from the first non-empty bin in a fixed random probe order,
        which is what keeps ``P(sig_A[i] == sig_B[i]) = J(A, B)`` — the property the whole stage
        rests on. The probe order is a function of the bin index and the config seed only, never of
        the document, or two documents would densify differently and stop being comparable.
        """
        bins = self._bins
        signature = [_EMPTY] * bins
        for value in hashes:
            index = value % bins
            candidate = (value // bins) & _MASK32
            if candidate < signature[index]:
                signature[index] = candidate

        empty = [i for i in range(bins) if signature[i] == _EMPTY]
        if empty:
            # Snapshot the fill state first. Densifying against values written by densification
            # would make the result depend on the order the empty bins were visited, which is the
            # order-independence bug this module exists to avoid, one level down.
            filled = [i for i in range(bins) if signature[i] != _EMPTY]
            if not filled:  # unreachable: min_shingles >= 1 guarantees at least one filled bin
                raise ValueError("cannot sketch a document with no shingles")
            occupied = set(filled)
            for index in empty:
                for probe in self._probe[index]:
                    if probe in occupied:
                        signature[index] = signature[probe]
                        break
        return array("I", signature).tobytes()

    # --- phase 2: band, verify, cluster ------------------------------------

    def build(self) -> None:
        """Close indexing and derive the clusters. Idempotent.

        Three steps, in this order because each needs the one before it finished: band the
        signatures into candidate buckets, verify every candidate against the full signature, then
        take connected components over the verified pairs and give each its lowest-key survivor.
        """
        if self._built:
            return
        self._built = True
        self._parent = list(range(len(self._ids)))
        self._band()
        self._cluster()

    def _band(self) -> None:
        """One pass per band, so peak memory is one band's buckets rather than all of them.

        The alternative — emitting every (band, key, document) triple and grouping at the end — is
        ``bands`` times the memory for the same answer, and on a full FineWeb2 shard that is 24M
        entries against 1.5M. Signatures are already in memory, so re-reading them 16 times is free
        by comparison.

        Bucket keys are the raw signature slices, not a hash of them. Python's own ``bytes`` hash is
        salted per process, which is fatal when a hash *decides* something (stages 6 and 9 both say
        so) but harmless here: the slices are only ever grouped by equality within one pass, and
        every decision downstream — the representative, the components, the survivor — is a
        function of the resulting *sets*.
        """
        config = self.config
        threshold = config.similarity_threshold
        retain = config.retain_pairs_above
        bins = self._bins
        row_bytes = self._row_bytes
        sigs = self._sigs
        keys = [document_key(doc_id) for doc_id in self._ids]
        # One entry per distinct candidate pair, shared across every band pass — see the note at
        # the comparison below on why a pair must not be counted once per band it collides in.
        seen_pairs: set[int] = set()
        width = max(len(self._ids), 1)

        for band in range(config.bands):
            start = band * row_bytes
            stop = start + row_bytes
            first: dict[bytes, int] = {}
            collided: dict[bytes, list[int]] = {}
            for position in self._eligible:
                key = sigs[position][start:stop]
                seen = first.get(key)
                if seen is None:
                    first[key] = position
                else:
                    collided.setdefault(key, [seen]).append(position)

            for members in collided.values():
                # The representative is the bucket's lowest-keyed member, not the first one read —
                # the same rule stage 6 uses to pick a survivor, for the same reason. A bucket is a
                # *set*; letting arrival order name its centre would make the candidate pairs, and
                # therefore the clusters, a function of the seed the reader shuffled with.
                #
                # Anchor-only, so a bucket of m members costs m-1 comparisons rather than
                # m(m-1)/2. This does give up recall in principle — within a bucket {A, B, C}
                # anchored at A, the pair (B, C) is never tested — but two things recover it:
                # every band is a fresh chance for a different anchor, and the union-find closes
                # B~C whenever A~B and A~C both verify. Measured, the residue is small: doubling
                # the bands from 16 to 32 changes Urdu Wikipedia's clusters at threshold 0.80 not
                # at all (118 either way) and its removals by one document.
                anchor = min(members, key=lambda position: keys[position])
                anchor_sig = sigs[anchor]
                for position in members:
                    if position == anchor:
                        continue
                    # The same pair collides in as many bands as it has matching rows, and
                    # counting it once per band inflates every reported total and tilts the
                    # histograms toward similar pairs, which collide in more bands by
                    # construction. One entry per pair, so "candidate pairs" means pairs.
                    low, high = (anchor, position) if anchor < position else (position, anchor)
                    packed = low * width + high
                    if packed in seen_pairs:
                        continue
                    if len(seen_pairs) >= self.config.max_candidate_pairs:
                        raise MemoryError(
                            f"stage 7 reached max_candidate_pairs="
                            f"{self.config.max_candidate_pairs:,} distinct candidate pairs — "
                            "raise the ceiling or narrow the banding (fewer, longer bands); it "
                            "exists so this fails loudly rather than swaps"
                        )
                    seen_pairs.add(packed)
                    self.log.candidate_pairs += 1
                    agreement = _agreement(anchor_sig, sigs[position])
                    similarity = agreement / bins
                    if similarity >= retain:
                        self._retain(anchor, position, agreement, similarity)
                    if similarity >= threshold:
                        self.log.verified_pairs += 1
                        self._union(anchor, position)

    def _retain(self, left: int, right: int, agreement: int, similarity: float) -> None:
        if self.log.retained_pairs >= self.config.max_retained_pairs:
            raise MemoryError(
                f"stage 7 retained {self.log.retained_pairs:,} candidate pairs, hitting "
                f"max_retained_pairs — raise retain_pairs_above to keep fewer, or the ceiling to "
                "keep them; a sweep over more pairs than fit is not a sweep"
            )
        self.log.retained_pairs += 1
        self._pair_left.append(left)
        self._pair_right.append(right)
        self._pair_agree.append(agreement)

        band = _band_label(similarity)
        self.log.similarity_histogram[band] += 1
        contained = containment_from_jaccard(
            similarity, self._sizes[left], self._sizes[right]
        )
        self.log.containment_histogram[_band_label(contained)] += 1
        self._sample_pair(band, left, right)

    def _sample_pair(self, band: str, left: int, right: int) -> None:
        """Keep a readable handful of pairs per similarity band, chosen by hash, not by arrival.

        Session 6 learned this on stage 5's rejection examples and session 8 learned it again on
        stage 6's cluster snippets: capping by arrival order shows whichever pairs the read order
        reached first. Keeping the lowest-hashing ones instead makes the sample a property of the
        corpus, so two runs that read it in different orders print the same pairs.
        """
        if self.pair_examples_per_band < 1:
            return
        kept = self._examples.setdefault(band, [])
        rank = _pair_rank(self._ids[left], self._ids[right])
        if len(kept) < self.pair_examples_per_band:
            kept.append((rank, left, right))
            kept.sort()
        elif rank < kept[-1][0]:
            kept[-1] = (rank, left, right)
            kept.sort()

    def _find(self, position: int) -> int:
        parent = self._parent
        root = position
        while parent[root] != root:
            root = parent[root]
        while parent[position] != root:  # path compression
            parent[position], position = root, parent[position]
        return root

    def _union(self, left: int, right: int) -> None:
        left_root, right_root = self._find(left), self._find(right)
        if left_root != right_root:
            self._parent[max(left_root, right_root)] = min(left_root, right_root)

    def _cluster(self) -> None:
        """Connected components over verified pairs; the lowest-keyed member of each survives.

        Components, not pairs, and the transitivity is deliberate: if A ≈ B and B ≈ C then A and C
        are the same document even when the estimate between them lands under the threshold. It is
        also the known weakness of this construction — a chain of barely-similar documents merges
        into one cluster — which is why ``largest_cluster`` is reported and why the cluster listing
        exists to be read.
        """
        log = self.log
        sizes: Counter[int] = Counter()
        for position in self._eligible:
            sizes[self._find(position)] += 1
        multi = {root for root, size in sizes.items() if size > 1}

        best: dict[int, tuple[int, int]] = {}
        for position in self._eligible:
            root = self._find(position)
            if root not in multi:
                continue
            key = document_key(self._ids[position])
            current = best.get(root)
            if current is None or key < current[0]:
                best[root] = (key, position)

        # Labels are assigned largest-cluster-first, so "cluster 0" is the biggest one in the run
        # and the example tables below can simply take the lowest labels. Ties break on the root
        # index, which is itself a position — deterministic given the corpus, which is all that is
        # needed, since nothing outside one report refers to a cluster by number.
        ranked = sorted(multi, key=lambda root: (-sizes[root], root))
        labels = {root: label for label, root in enumerate(ranked)}
        illustrated = set(ranked[: self.example_clusters])

        for position in self._eligible:
            root = self._find(position)
            if root not in multi:
                continue
            label = labels[root]
            self._cluster_of[position] = label
            self._cluster_size[position] = sizes[root]
            if best[root][1] != position:
                self._removed.add(position)
            if self.track_sources and self._sources[position]:
                self._cluster_sources.setdefault(label, set()).add(self._sources[position])
            if root in illustrated:
                members = self._cluster_members.setdefault(label, [])
                if len(members) < 5:
                    members.append(position)

        self._cluster_keeper = {
            labels[root]: self._ids[position] for root, (_, position) in best.items()
        }
        self._label_size = {labels[root]: sizes[root] for root in multi}

        log.clusters = len(multi)
        log.duplicate_documents = len(self._removed)
        log.largest_cluster = max(sizes[root] for root in multi) if multi else 0

        for sources in self._cluster_sources.values():
            if len(sources) > 1:
                log.cross_source_clusters += 1
                for left, right in itertools.combinations(sorted(sources), 2):
                    log.cross_source_pairs[f"{left}|{right}"] += 1

        for position in range(len(self._ids)):
            if position in self._dropped:
                continue  # an earlier stage removed it; it is not stage 7's to keep or count
            source = self._sources[position]
            if position in self._removed:
                if source:
                    log.removed_by_source[source] += 1
                    label = self._cluster_of.get(position, -1)
                    if len(self._cluster_sources.get(label, ())) > 1:
                        log.removed_cross_source_by_source[source] += 1
                continue
            log.documents_kept += 1
            log.chars_kept += self._chars[position]
            if source:
                log.kept_by_source[source] += 1

    # --- reporting ---------------------------------------------------------

    def verdict(self, doc_id: str) -> NearDuplicateVerdict:
        """This document's fate. A lookup, not a recomputation — stage 7 needs no second pass.

        Raises on an unknown id for stage 6's reason: a caller asking about a document this pass
        never saw is a caller reading a different corpus than the one that was clustered, and the
        quiet answer ("kept") would be indistinguishable from a correct one.
        """
        self.build()
        position = self._position.get(doc_id)
        if position is None:
            raise KeyError(
                f"{doc_id!r} was not indexed — stage 7 is being asked about a document it never "
                "sketched, which means this is a different document set than the one clustered"
            )
        if position in self._dropped:
            # Not "kept": an earlier stage removed it, and answering `kept=True` here would be a
            # true statement about stage 7 that reads as a false one about the corpus.
            return NearDuplicateVerdict(doc_id, False, reason="removed_before_stage_7")
        if not self._sigs[position]:
            return NearDuplicateVerdict(doc_id, True, reason="too_few_shingles")
        cluster = self._cluster_of.get(position, -1)
        size = self._cluster_size.get(position, 1)
        if position in self._removed:
            return NearDuplicateVerdict(doc_id, False, cluster, size, "near_duplicate")
        return NearDuplicateVerdict(doc_id, True, cluster, size)

    def verdicts(self) -> Iterator[NearDuplicateVerdict]:
        self.build()
        for doc_id in self._ids:
            yield self.verdict(doc_id)

    def indexed_ids(self) -> Iterator[str]:
        """Every id sketched, in index order — including any later handed to :meth:`drop`.

        Exists so a single-pass driver can ask an earlier stage about each document without having
        kept the corpus: the ids are already here, which is the fact that makes the second read
        unnecessary. Read-only, and safe before :meth:`build`.
        """
        yield from self._ids

    def removed_ids(self) -> list[str]:
        self.build()
        return [self._ids[position] for position in sorted(self._removed)]

    def sweep(self, thresholds: Iterable[float]) -> list[dict]:
        """Re-cluster at other thresholds from the pairs this pass already measured.

        This is the point of retaining pairs. Session 6's lesson was that a threshold has to be
        moved by documents rather than chosen from a distribution, and session 8's carried-forward
        note asks for candidate pairs at several thresholds to be *read* before one is picked.
        Re-running the corpus for each candidate is hours; re-running the union-find over a few
        million retained pairs is seconds, and it is exact for any threshold at or above
        ``retain_pairs_above``.
        """
        self.build()
        results = []
        for threshold in sorted(thresholds):
            if threshold < self.config.retain_pairs_above:
                raise ValueError(
                    f"threshold {threshold} is below retain_pairs_above="
                    f"{self.config.retain_pairs_above}: the pairs that decide it were not kept, so "
                    "the answer would be silently incomplete"
                )
            parent = list(range(len(self._ids)))

            def find(position: int, parent: list[int] = parent) -> int:
                while parent[position] != position:
                    parent[position] = parent[parent[position]]
                    position = parent[position]
                return position

            pairs = 0
            for left, right, agreement in zip(
                self._pair_left, self._pair_right, self._pair_agree, strict=True
            ):
                if agreement / self._bins < threshold:
                    continue
                pairs += 1
                left_root, right_root = find(left), find(right)
                if left_root != right_root:
                    parent[max(left_root, right_root)] = min(left_root, right_root)

            sizes = Counter(find(position) for position in self._eligible)
            multi = [size for size in sizes.values() if size > 1]
            results.append(
                {
                    "threshold": round(threshold, 4),
                    "verified_pairs": pairs,
                    "clusters": len(multi),
                    "duplicate_documents": sum(multi) - len(multi),
                    "largest_cluster": max(multi, default=0),
                    "keep_rate": round(
                        (self.log.indexed - (sum(multi) - len(multi))) / self.log.indexed, 6
                    )
                    if self.log.indexed
                    else 0.0,
                }
            )
        return results

    def pair_examples(self) -> list[PairExample]:
        """Measured pairs to read, spread across similarity bands — the threshold's real input."""
        self.build()
        out: list[PairExample] = []
        for band in sorted(self._examples, reverse=True):
            for _, left, right in self._examples[band]:
                similarity = _agreement(self._sigs[left], self._sigs[right]) / self._bins
                out.append(
                    PairExample(
                        left=self._ids[left],
                        right=self._ids[right],
                        similarity=similarity,
                        containment=containment_from_jaccard(
                            similarity, self._sizes[left], self._sizes[right]
                        ),
                        left_shingles=self._sizes[left],
                        right_shingles=self._sizes[right],
                        left_source=self._sources[left],
                        right_source=self._sources[right],
                    )
                )
        return out

    def top_clusters(self, limit: int = 20) -> list[dict]:
        """The largest clusters, for the report and for reading by hand.

        Labels are already assigned largest-first, so this is a prefix rather than a sort, and the
        member ids exist only for the largest ``example_clusters`` of them — the same rule stage 6
        applies to its example groups, for the same reason: per-cluster side tables must not be
        sized by the number of clusters.
        """
        self.build()
        return [
            {
                "cluster": label,
                "size": self._label_size[label],
                "sources": sorted(self._cluster_sources.get(label, ())),
                "kept": self._cluster_keeper.get(label, ""),
                "duplicates": [
                    self._ids[position]
                    for position in self._cluster_members.get(label, ())
                    if position in self._removed
                ][:4],
            }
            for label in range(min(limit, self.log.clusters))
        ]

    @property
    def distinct_documents(self) -> int:
        self.build()
        return self.log.documents_kept

    def to_dict(self) -> dict:
        self.build()
        payload = self.log.to_dict()
        payload["distinct_documents"] = self.distinct_documents
        payload["top_clusters"] = self.top_clusters(limit=self.example_clusters)[:20]
        payload["pair_examples"] = [example.to_dict() for example in self.pair_examples()]
        return payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _probe_table(bins: int, seed: int) -> tuple[tuple[int, ...], ...]:
    """One fixed random probe order per bin, for densification.

    A permutation rather than a re-hashed sequence of attempts, and the unbiasedness argument
    survives the swap: the first element of a uniformly random permutation, restricted to whichever
    bins happen to be non-empty, is uniform over that set — which is exactly the property optimal
    densification needs, and it terminates in one scan instead of retrying on collisions.

    Seeded through blake2b rather than by handing ``random.Random`` a tuple or a string, for the
    reason `shards.py` gives: tuple seeds were removed in 3.14 and string seeding goes through a
    hash whose stability across releases is not something a frozen corpus should depend on.
    """
    key = f"ravaan/minhash/probe\x00{bins}\x00{seed}".encode()
    rng = random.Random(int.from_bytes(hashlib.blake2b(key, digest_size=16).digest(), "big"))
    table = []
    for index in range(bins):
        order = [position for position in range(bins) if position != index]
        rng.shuffle(order)
        table.append(tuple(order))
    return tuple(table)


def _agreement(left: bytes, right: bytes, width: int = 4) -> int:
    """How many of the K signature values match — the Jaccard estimate, unnormalised."""
    return sum(left[i : i + width] == right[i : i + width] for i in range(0, len(left), width))


def _band_label(value: float) -> str:
    """``0.85`` -> ``"0.85-0.90"``. Fixed 0.05 bands, so two runs' histograms line up."""
    lower = min(int(value * 20), 19) / 20
    return f"{lower:.2f}-{lower + 0.05:.2f}"


def _pair_rank(left: str, right: str) -> int:
    """A stable order over pairs, so an example sample does not depend on the read order."""
    first, second = sorted((left, right))
    return int.from_bytes(
        hashlib.blake2b(f"{first}\x00{second}".encode(), digest_size=8).digest(), "big"
    )


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def near_deduplicate(
    documents: Iterable[tuple], config: MinHashConfig | None = None
) -> tuple[list[NearDuplicateVerdict], MinHashDeduplicator]:
    """One pass over a collection of ``(doc_id, text[, source])``, then :meth:`build`.

    For tests and for samples small enough to hold in memory — which, unlike stage 6, is the same
    condition the corpus pass runs under, since stage 7 holds a sketch per document either way.
    """
    index = MinHashDeduplicator(config)
    records = [tuple(record) for record in documents]
    for record in records:
        index.index(record[0], record[1], source=record[2] if len(record) > 2 else "")
    index.build()
    return [index.verdict(record[0]) for record in records], index


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    pin_utf8_streams()  # Urdu on a cp1252 console raises rather than mangles.
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("input", nargs="?", help="JSONL file (default: stdin)")
    parser.add_argument("-c", "--config", help="minhash config JSON")
    parser.add_argument("--field", default="text", help="text field (default: text)")
    parser.add_argument("--id-field", default="doc_id", help="id field (default: doc_id)")
    parser.add_argument("--source-field", default="source", help="source field (default: source)")
    parser.add_argument("--threshold", type=float, help="override similarity_threshold")
    parser.add_argument(
        "--sweep",
        nargs="+",
        type=float,
        help="also report clustering at these thresholds, from the same pass",
    )
    parser.add_argument("--removals", help="write the removed ids here, one per line")
    parser.add_argument("--log", help="write the stage-7 log here as JSON")
    args = parser.parse_args(argv)

    config = MinHashConfig.from_json_file(args.config) if args.config else MinHashConfig()
    if args.threshold is not None:
        config = MinHashConfig.from_dict(
            {**config.to_dict(), "similarity_threshold": args.threshold}
        )

    payload_text = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    records = [json.loads(line) for line in payload_text.splitlines() if line.strip()]

    index = MinHashDeduplicator(config)
    for record in records:
        index.index(
            record[args.id_field], record[args.field], source=record.get(args.source_field, "")
        )
    index.build()

    removed: list[str] = []
    for verdict in index.verdicts():
        if not verdict.kept:
            removed.append(verdict.doc_id)
        print(json.dumps(verdict.to_dict(), ensure_ascii=False))

    if args.removals:
        Path(args.removals).write_text(
            "".join(f"{doc_id}\n" for doc_id in removed), encoding="utf-8", newline="\n"
        )

    payload = index.to_dict()
    if args.sweep:
        payload["sweep"] = index.sweep(args.sweep)
    report = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.log:
        Path(args.log).write_text(report + "\n", encoding="utf-8", newline="\n")
    else:
        print(report, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
