"""Evaluation decontamination — stage 8 of the corpus pipeline (PRD §6.3.8).

§6.3.8 asks for "hash + fuzzy match against all test sets". Sessions 8 and 9 measured what each
half of that has to be, and the measurements point in opposite directions:

* **Finding L — the hash half returns a confident zero on the most likely contamination path.**
  Urdu Wikipedia articles sit inside FineWeb2 as crawled HTML: processed wikitext against a
  rendered page, same content, never byte-identical. Exact dedup found **0** cross-source groups
  where the URL census puts ~2,388 same-article documents. A stage 8 reporting "0 contaminated"
  from hashing alone would be reporting that artefact.
* **Finding M — the fuzzy half has to score containment, not Jaccard.** Of 49 sampled cross-source
  pairs, 11 fall below a 0.80 Jaccard cut, the clearest being **J = 0.656 with containment 1.000 at
  150/96 shingles**: a Wikipedia article whose every shingle is present in the crawled copy,
  scoring 0.656 only because the crawled page carries 54 shingles the article does not.

Session 9 handed this stage one more instruction — reuse :mod:`ravaan.data.minhash` rather than
grow a second estimator with a second threshold nobody swept. **Half of that survived contact with
the problem, and the half that did not is the central design decision here.**

**The shingling is shared; the sketch and the banding are not, because they cannot answer this
stage's question.** MinHash estimates *Jaccard*, and LSH banding proposes candidates by it. But an
eval item sitting **verbatim** inside a training document — containment 1.000, the exact thing
Finding M says stage 8 must catch — has a Jaccard of |E|/|T|, which falls as the document grows. A
100-shingle eval item inside a 1,500-shingle document scores J = 0.067, and the shipped (32, 4)
banding proposes it with probability **0.0006**. Retuning does not rescue it: (128, 1) reaches
0.9999 recall there and simultaneously makes **12% of all pairs** candidates, which over a corpus ×
eval-set cross product is ~9 × 10⁸ verifications. Either the recall collapses or the precision
does, and the reason is structural rather than a bad setting — Jaccard between a small item and a
large document is low *however complete the containment is*.

**So stage 8 holds the eval sets exactly, and the estimator becomes unnecessary rather than
merely wrong.** MinHash exists to avoid the all-pairs comparison of a corpus against itself. Stage
8 compares a corpus against a *bounded* set — §8.2's test sets are ~6K items total — so an inverted
index over the eval shingles fits in memory, and one lookup per corpus shingle yields the **exact**
intersection. Not an estimate with a standard error of 0.035: the true count. Containment and
Jaccard both follow from it exactly, no sketch, no banding, no S-curve, and no second threshold
that nobody swept. The cost is one dict lookup per shingle per document, which is the same
asymptotic pass the sketch would have cost.

Four properties this module is built around.

**1. Containment of the *eval item* decides, and the direction is the whole point.**
:func:`~ravaan.data.minhash.containment_from_jaccard` divides by ``min(|A|, |B|)``, which is the
right question for stage 7 — "is either of these inside the other" — and the wrong one here. Stage
8 asks a directed question: *is this test item inside this training document*. When the eval item
is the larger of the two, ``min()`` silently measures the training document's containment instead
and reports a number about the wrong object. Stage 7 has to *derive* its intersection from a
Jaccard estimate because it never holds both shingle sets at once; stage 8 holds the eval side
whole, so it counts the intersection directly and both scores are exact. Same quantity, one stage
estimating it and one measuring it.

**2. Both halves of §6.3.8 run, and they are reported separately.** The exact half is stage 6's
:func:`~ravaan.data.dedup.content_hash` over the whole document *and* over each of its lines — an
eval sentence quoted as one line of a training document is an exact match that document-level
hashing cannot see. Finding L predicts the hash half is near-inert on the wiki path; it is not
predicted to be inert on the Roman-Urdu-Parl path, where the source is machine-produced and PRD
§6.2 warns its 6.37M pairs collapse to ~1.09M unique sentences. Two instruments that fail on
different populations are worth more than either, but only if the report can tell which fired.

**3. Contamination is removed from the *training* side, always.** There is no survivor rule here
and no lowest-key tie-break, because stage 8 is not choosing between two copies: a test set is an
instrument, and shrinking it to fit the corpus is measuring the thermometer (PRD §8.1's phrase).
Every contaminated training document goes; every eval item stays. This also makes the stage
trivially order-independent — a document's verdict is a function of that document and the sealed
eval index, and of nothing else the pass has seen — which is the property stages 6 and 7 each pay a
second corpus pass to obtain.

**4. What cannot be measured is counted and reported loudly, and the doctrine inverts here.**
Stage 7's rule is "must not delete what it cannot measure", so a document below ``min_shingles`` is
kept. The dual for stage 8 is harsher: an *eval item* too short to shingle is contamination that
cannot be detected, so silence about it would be a false clean bill of health. Such items are
counted in ``eval_items_unmeasurable``, still covered by the exact half, and the log carries the
number into the manifest. 77.8% of Roman-Urdu-Parl's test rows fall below 8 word-5-grams, which is
why an eval set declares its own shingling and character shingles exist.

    index = Decontaminator()
    for item in eval_set:                                  # bounded, held exactly
        index.add_eval_item("roman-urdu-parl-test", item.id, item.text)
    index.seal()
    for doc in corpus:                                     # one streaming pass, O(1) memory
        if index.check(doc.doc_id, normalized(doc)).kept:
            write(doc)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from array import array
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from ravaan.data.dedup import canonical, content_hash, lines
from ravaan.data.minhash import SHINGLE_UNITS, shingle_hashes

__all__ = [
    "DECONTAMINATION_VERSION",
    "ContaminationHit",
    "DecontaminationConfig",
    "DecontaminationLog",
    "DecontaminationVerdict",
    "Decontaminator",
    "EvalSetSpec",
    "containment_of",
    "decontaminate",
]

# Bump on any change to which documents survive: the shingling, the scoring, the thresholds' units.
# The manifest records it, so a frozen corpus can be traced to the exact pass that produced it.
DECONTAMINATION_VERSION = "1.0.0"

# Keyed apart from stage 6's content hashes and stage 7's shingle hashes for the same reason those
# two are keyed apart from each other: a line hash must not be able to collide with a document hash.
_LINE_PERSON = b"ravaan/decon/l"


def containment_of(intersection: int, target_size: int) -> float:
    """|E ∩ T| / |E| — the share of the *eval item* that is present in the training document.

    Directed, unlike :func:`~ravaan.data.minhash.containment_from_jaccard`, whose ``min(|A|, |B|)``
    denominator answers stage 7's symmetric question. Stage 8's question has a subject and an
    object: a 500-shingle eval item sharing 100 shingles with a 100-shingle training document is
    20% contaminated, not 100% — and ``min()`` would call it 100% and delete a clean document.

    Exact here, because the intersection is counted rather than estimated (see the module note on
    why the sketch is not used). Clamped anyway: a caller passing an intersection larger than the
    set it came from has a bug, and returning 1.4 would hide it downstream.
    """
    if target_size <= 0:
        return 0.0
    return min(1.0, intersection / target_size)


def _line_hash(text: str, *, bits: int = 128) -> int:
    """Hash of one canonical line, in its own keyed space."""
    return int.from_bytes(
        hashlib.blake2b(
            canonical(text).encode("utf-8"), digest_size=bits // 8, person=_LINE_PERSON
        ).digest(),
        "big",
    )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvalSetSpec:
    """How one test set is shingled. Declared per set, never auto-detected.

    §8.2's five test sets are not one shape. Held-out native Urdu is documents; Roman-Urdu-Parl's
    reference split is single sentences averaging 43.5 characters; the real-OCR set is ~300 *lines*.
    Measured on the real file, **77.8% of Roman-Urdu-Parl's test rows carry fewer than 8
    word-5-grams** and are simply not measurable in that unit, against 2.6% in character 5-grams.
    One global shingling would therefore make stage 8 blind to a whole test set while reporting a
    clean number, which is the failure mode this stage exists to prevent.

    Auto-detecting the unit from row length was the alternative and it is rejected for the reason
    :mod:`ravaan.data.shards` rejects auto-detected columns: a corpus decision that changes with the
    data is one nobody can reproduce from the manifest.
    """

    name: str
    shingle_size: int = 5
    shingle_unit: str = "word"

    # Both fall back to the stage config when None. They are here rather than only there because
    # **a threshold carried across a change of unit is not the same threshold** — measured, and it
    # is the sharpest thing this stage learned from real text. See :meth:`for_sentences`.
    min_shingles: int | None = None
    containment_threshold: float | None = None
    retain_hits_above: float | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("an eval set needs a name — it is what the report attributes hits to")
        if self.shingle_unit not in SHINGLE_UNITS:
            raise ValueError(
                f"shingle_unit must be one of {SHINGLE_UNITS}, got {self.shingle_unit!r}"
            )
        if self.shingle_size < 1:
            raise ValueError(f"shingle size must be >= 1, got {self.shingle_size}")
        if self.min_shingles is not None and self.min_shingles < 1:
            raise ValueError(f"min_shingles must be >= 1, got {self.min_shingles}")
        if self.containment_threshold is not None and not 0.0 < self.containment_threshold <= 1.0:
            raise ValueError(
                f"containment_threshold must be in (0, 1], got {self.containment_threshold}"
            )
        if self.retain_hits_above is not None:
            if not 0.0 <= self.retain_hits_above <= 1.0:
                raise ValueError(
                    f"retain_hits_above must be in [0, 1], got {self.retain_hits_above}"
                )
            ceiling = self.containment_threshold
            if ceiling is not None and self.retain_hits_above > ceiling:
                raise ValueError(
                    f"retain_hits_above ({self.retain_hits_above}) must not exceed this set's "
                    f"containment_threshold ({ceiling}) — retaining fewer hits than the threshold "
                    "uses would make sweep() silently incomplete"
                )

    def for_sentences(self) -> EvalSetSpec:
        """A variant for test sets whose unit is a sentence, not a document.

        The same move :meth:`~ravaan.data.quality.QualityConfig.for_sentences` makes at stage 5, for
        the same reason and with the same consequence if it is skipped: one global setting applied
        to a population it was not measured on silently produces a wrong number. Three settings
        change together, and each was moved by reading documents.

        * **Character shingles.** 77.8% of Roman-Urdu-Parl's test rows carry fewer than 8
          word-5-grams; in character 5-grams, 2.0% do. Word shingling leaves stage 8 blind to
          three-quarters of a test set while reporting a clean number for it.
        * **``min_shingles`` 8 → 25, and this is the measured bug.** Eight shingles means ~12
          *words* in the word unit and ~12 *characters* in the character unit — one number with two
          meanings, and nothing in the config says so. At 8, two thirds of every hit on real text
          came from 12-to-19-character fragments: ``'angrezi blog'`` is genuinely contained in
          ``'az rashid Kamraan urdu blog angrezi blog az Shah'`` and is evidence of nothing. 25
          (~29 characters) excludes 24.8% of the test rows from containment scoring — all of them
          still covered by the exact half, which is the right instrument for a string that short.
        * **``containment_threshold`` 0.80 → 0.90.** A sentence is closer to atomic than a document
          is: it does not get truncated by a crawler or lose a section to an extractor, so partial
          containment is weaker evidence here than there. Measured, the 0.80–0.90 band on real text
          is templates — ``'qaisrani , September 4 , 2006'`` against ``'qaisrani , September 25 ,
          2006'``, and ``'scan safha number 36 : ( kitaab safha 29 )'`` against ``'... 21 : ( ...
          14 )'`` — while the 0.90+ band is the mechanism PRD §6.2 warns about: the same sentence
          re-transliterated by a second crowdworker, which is real contamination of a
          transliteration metric.
        * **``retain_hits_above`` 0.50 → 0.80, and this one is a freeze-time hazard rather than a
          correctness one.** A 30-shingle test sentence shares half its character 5-grams with a
          long article *constantly*: measured on Urdu Wikipedia, a floor of 0.50 retains **11.9
          hits per document of which 0.05% are above threshold**. Projected over a full FineWeb2
          shard that is ~17.7M retained hits against a ``max_retained_hits`` ceiling of 20M — a
          ``MemoryError`` hours into the pass that writes the frozen corpus. The floor exists so
          ``sweep()`` can explore, and 0.80 still brackets the decision from both sides. Word
          shingles have no such problem (unrelated documents measure mean Jaccard 0.00034), which is
          why this moves with the sentence variant rather than globally.
        """
        return replace(
            self,
            shingle_unit="char",
            min_shingles=25,
            containment_threshold=0.90,
            retain_hits_above=0.80,
        )

    @property
    def shingling(self) -> tuple[int, str]:
        """The key eval sets are grouped by — one inverted index per distinct shingling."""
        return (self.shingle_size, self.shingle_unit)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DecontaminationConfig:
    """Stage 8 settings. Defaults are the Ravaan corpus v1 settings."""

    # The share of an eval item that must appear in a training document for that document to go.
    #
    # 0.80 rather than 1.00 deliberately. Requiring a *whole* eval item makes the rule brittle in
    # exactly the direction that matters: Finding M's population is an article and its crawled
    # copy, where the crawl truncates a trailing section or the extractor drops a table, and a
    # single missing shingle would clear a threshold of 1.0 while the document is plainly the same
    # text. It is also the number stage 7's sweep settled on for the neighbouring question, so the
    # two stages do not disagree about how similar "the same document" is without a reason.
    #
    # Asymmetry with stage 7 is deliberate the other way too: this threshold is on *containment*,
    # which is >= Jaccard always, so 0.80 here is a strictly wider net than 0.80 there. That is the
    # correct direction for a decontamination — a false positive costs one training document out of
    # millions, a false negative costs the validity of an evaluation number.
    containment_threshold: float = 0.80

    # Every hit at or above this is retained with its measured containment, which is what makes
    # sweep() exact rather than a re-run. Session 6's lesson, applied one stage on: a threshold is
    # moved by reading documents, and the pass has to hand back the evidence to read.
    retain_hits_above: float = 0.50

    # Below this an eval item cannot be scored by containment and is reported as unmeasurable
    # rather than as clean. 8 is stage 7's figure and the argument is the same: beneath it
    # containment takes a handful of discrete values, so a threshold comparison measures
    # granularity rather than overlap.
    min_shingles: int = 8

    # The exact half of §6.3.8, both levels. Document-level catches a test document reproduced
    # whole; line-level catches a test *sentence* quoted inside a longer training document, which
    # document hashing structurally cannot see and which is the shape of every sentence-unit test
    # set in §8.2. Separable because their yields are separate findings (Finding L predicts the
    # first is inert on the wiki path).
    exact_document_match: bool = True
    exact_line_match: bool = True

    # A line shorter than this is not indexed for exact matching. Short lines are headings, dates
    # and navigation labels; "اہم خبریں" is a true exact match against thousands of documents and
    # evidence of nothing. 40 characters is stage 5's 400-character floor divided by the ~10 lines
    # a document of that length carries, and it is swept in the report rather than assumed.
    min_line_chars: int = 40

    # Ceilings, so a pass fails loudly at a stated size rather than swapping. An eval shingle costs
    # ~60 bytes as a dict entry, so 40M is ~2.4 GB — far past §8.2's ~6K items, which is the point:
    # it is a guard against pointing this stage at a corpus by mistake, not a working limit.
    max_index_shingles: int = 40_000_000
    max_retained_hits: int = 20_000_000

    def __post_init__(self) -> None:
        if not 0.0 < self.containment_threshold <= 1.0:
            raise ValueError(
                f"containment_threshold must be in (0, 1], got {self.containment_threshold}"
            )
        if not 0.0 <= self.retain_hits_above <= self.containment_threshold:
            raise ValueError(
                "retain_hits_above must be in [0, containment_threshold] — retaining fewer hits "
                "than the threshold uses would make sweep() silently incomplete"
            )
        if self.min_shingles < 1:
            raise ValueError("min_shingles must be >= 1 — an item with no shingles has no size")
        if self.min_line_chars < 0:
            raise ValueError(f"min_line_chars must be >= 0, got {self.min_line_chars}")
        if min(self.max_index_shingles, self.max_retained_hits) < 1:
            raise ValueError("the max_* ceilings must both be >= 1")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> DecontaminationConfig:
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known - {"decontamination_version", "eval_sets", "_comment"}
        if unknown:
            raise ValueError(f"unknown decontamination config keys: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json_file(cls, path: str | Path) -> DecontaminationConfig:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json_file(self, path: str | Path) -> None:
        payload = {"decontamination_version": DECONTAMINATION_VERSION, **self.to_dict()}
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"version": DECONTAMINATION_VERSION, **self.to_dict()},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ContaminationHit:
    """One (eval item, training document) overlap, with everything the decision rested on.

    Both scores are carried because they disagree, and the disagreement is Finding M. A hit at
    containment 1.000 and Jaccard 0.067 is an eval item sitting verbatim inside a document 15 times
    its length — invisible to stage 7's instrument, and the whole reason this stage has its own.
    """

    eval_set: str
    eval_id: str
    doc_id: str
    containment: float
    jaccard: float
    intersection: int
    eval_shingles: int
    doc_shingles: int
    exact: str = ""  # "" | "document" | "line"

    def to_dict(self) -> dict:
        return {
            "eval_set": self.eval_set,
            "eval_id": self.eval_id,
            "doc_id": self.doc_id,
            "containment": round(self.containment, 4),
            "jaccard": round(self.jaccard, 4),
            "intersection": self.intersection,
            "eval_shingles": self.eval_shingles,
            "doc_shingles": self.doc_shingles,
            "exact": self.exact,
        }


@dataclass(frozen=True, slots=True)
class DecontaminationVerdict:
    """One training document's fate, and the eval item that decided it."""

    doc_id: str
    kept: bool
    reason: str = ""  # "" | "contaminated" | "exact_document" | "exact_line"
    eval_set: str = ""
    eval_id: str = ""
    containment: float = 0.0

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "kept": self.kept,
            "reason": self.reason,
            "eval_set": self.eval_set,
            "eval_id": self.eval_id,
            "containment": round(self.containment, 4),
        }


@dataclass
class DecontaminationLog:
    """Corpus-level aggregate — the stage-8 line of the manifest and the statistics table."""

    config: DecontaminationConfig = field(default_factory=DecontaminationConfig)

    # --- the eval side, which is indexed before the corpus is read ---
    eval_sets: dict[str, int] = field(default_factory=Counter)
    eval_items: int = 0
    eval_items_unmeasurable: int = 0  # below min_shingles: exact-only coverage, reported loudly
    eval_shingles: int = 0
    eval_lines: int = 0

    # --- the corpus side ---
    checked: int = 0
    kept: int = 0
    removed: int = 0
    chars_in: int = 0
    chars_kept: int = 0

    # Which half of §6.3.8 caught it. Separate counters because Finding L predicts these differ by
    # population, and a single "contaminated" number would hide exactly that.
    removed_by_reason: dict[str, int] = field(default_factory=Counter)
    removed_by_eval_set: dict[str, int] = field(default_factory=Counter)
    removed_by_source: dict[str, int] = field(default_factory=Counter)
    by_source: dict[str, int] = field(default_factory=Counter)

    # Eval items that caught at least one document — "how much of the test set is compromised",
    # which is a different and more important question than how many documents were removed.
    eval_items_hit: dict[str, set] = field(default_factory=dict)

    hits_retained: int = 0
    containment_histogram: dict[str, int] = field(default_factory=Counter)
    jaccard_histogram: dict[str, int] = field(default_factory=Counter)

    @property
    def keep_rate(self) -> float:
        return self.kept / self.checked if self.checked else 1.0

    @property
    def char_keep_rate(self) -> float:
        return self.chars_kept / self.chars_in if self.chars_in else 1.0

    @property
    def contamination_rate(self) -> float:
        return self.removed / self.checked if self.checked else 0.0

    def eval_coverage(self) -> dict[str, dict]:
        """Per test set: how many of its items were found in the training corpus.

        The number §8.2 actually cares about. Removing 40 training documents is housekeeping;
        learning that 40% of a *test set* was in the training data is a statement about whether the
        metric computed on it means anything.
        """
        coverage = {}
        for name, total in sorted(self.eval_sets.items()):
            hit = len(self.eval_items_hit.get(name, ()))
            coverage[name] = {
                "items": total,
                "items_found_in_corpus": hit,
                "share": round(hit / total, 6) if total else 0.0,
            }
        return coverage

    def to_dict(self) -> dict:
        return {
            "decontamination_version": DECONTAMINATION_VERSION,
            "config": self.config.to_dict(),
            "config_fingerprint": self.config.fingerprint(),
            "eval_sets": dict(sorted(self.eval_sets.items())),
            "eval_items": self.eval_items,
            "eval_items_unmeasurable": self.eval_items_unmeasurable,
            "eval_shingles": self.eval_shingles,
            "eval_lines": self.eval_lines,
            "checked": self.checked,
            "kept": self.kept,
            "removed": self.removed,
            "keep_rate": round(self.keep_rate, 6),
            "contamination_rate": round(self.contamination_rate, 6),
            "chars_in": self.chars_in,
            "chars_kept": self.chars_kept,
            "char_keep_rate": round(self.char_keep_rate, 6),
            "removed_by_reason": dict(sorted(self.removed_by_reason.items())),
            "removed_by_eval_set": dict(sorted(self.removed_by_eval_set.items())),
            "removed_by_source": dict(sorted(self.removed_by_source.items())),
            "by_source": dict(sorted(self.by_source.items())),
            "eval_coverage": self.eval_coverage(),
            "hits_retained": self.hits_retained,
            "containment_histogram": dict(sorted(self.containment_histogram.items())),
            "jaccard_histogram": dict(sorted(self.jaccard_histogram.items())),
        }


# ---------------------------------------------------------------------------
# The stage
# ---------------------------------------------------------------------------


class _ShingleIndex:
    """Inverted index over one shingling of the eval sets: shingle hash -> eval item positions.

    Two dicts rather than one ``dict[int, list[int]]``, and the reason is the same one stage 6
    gives for not sizing its side tables by group count. Almost every eval shingle belongs to
    exactly one item, and a one-element list costs ~120 bytes on top of the dict entry that already
    holds the answer. The overflow dict carries only the shingles two or more items share — on the
    real test sets a few percent of them.
    """

    __slots__ = ("owner", "shared")

    def __init__(self) -> None:
        self.owner: dict[int, int] = {}
        self.shared: dict[int, list[int]] = {}

    def __len__(self) -> int:
        return len(self.owner)

    def add(self, shingle: int, position: int) -> bool:
        """Returns True if this shingle is new to the index."""
        existing = self.owner.get(shingle)
        if existing is None:
            self.owner[shingle] = position
            return True
        if existing == position:
            return False
        bucket = self.shared.get(shingle)
        if bucket is None:
            self.shared[shingle] = [position]
        elif position not in bucket:
            bucket.append(position)
        return False

    def tally(self, shingles: Iterable[int]) -> Counter:
        """Distinct-shingle hit counts per eval item — the exact intersection, per item."""
        counts: Counter = Counter()
        owner = self.owner
        shared = self.shared
        for shingle in shingles:
            position = owner.get(shingle)
            if position is None:
                continue
            counts[position] += 1
            extra = shared.get(shingle)
            if extra is not None:
                for other in extra:
                    counts[other] += 1
        return counts


class Decontaminator:
    """Index the eval sets, then stream the corpus past them. One pass, O(1) corpus memory.

    The asymmetry with stages 6 and 7 is the point. Those compare a corpus against *itself*, so
    they must hold something per corpus document and pay a second pass to keep the answer
    independent of read order. Stage 8 compares a corpus against a bounded external artifact: the
    index is sized by the test sets (§8.2: ~6K items), a document's verdict depends only on that
    index and the document, and nothing about the pass — its order, its resumption point, its seed
    — can change what any document's verdict is.
    """

    def __init__(self, config: DecontaminationConfig | None = None) -> None:
        self.config = config or DecontaminationConfig()
        self.log = DecontaminationLog(config=self.config)

        self._specs: dict[str, EvalSetSpec] = {}
        self._indexes: dict[tuple[int, str], _ShingleIndex] = {}

        # Parallel per-eval-item arrays, as in stage 7 and for the same reason.
        self._eval_set: list[str] = []
        self._eval_id: list[str] = []
        self._eval_sizes = array("I")
        self._eval_shingling: list[tuple[int, str]] = []
        # Resolved per item at index time rather than looked up per hit: the threshold belongs to
        # the eval set, and _score() runs once per candidate hit on every corpus document.
        #
        # **"d" (float64), not "f".** Single precision rounds 0.80 *up*, to 0.80000001192, so a
        # document containing exactly 0.80 of an eval item — 20 of 25 shingles, which is an ordinary
        # value at these sizes — compares as below the threshold and is kept. The config would say
        # 0.80 and the code would mean 0.80000001, silently, only at the boundary, and only on the
        # removal side. Measured when it dropped 16 hits from a band that could not have changed.
        # Python floats are doubles, so "d" round-trips whatever the config declares; the cost is
        # 4 bytes per eval item over §8.2's ~6K of them.
        self._eval_threshold = array("d")
        self._eval_retain = array("d")

        self._doc_hashes: dict[int, int] = {}  # content hash -> eval item position
        self._line_hashes: dict[int, int] = {}

        self._hits: list[ContaminationHit] = []
        self._sealed = False

    # --- phase 1: index the eval sets --------------------------------------

    def add_eval_set(self, spec: EvalSetSpec) -> None:
        """Declare a test set's shingling before adding its items."""
        if self._sealed:
            raise RuntimeError("seal() has already run — the eval index is closed")
        existing = self._specs.get(spec.name)
        if existing is not None and existing != spec:
            raise ValueError(
                f"eval set {spec.name!r} was already declared as {existing} and cannot be "
                f"redeclared as {spec} — two shinglings for one set would put its items in two "
                "indexes and report the union as one number"
            )
        self._specs[spec.name] = spec
        self._indexes.setdefault(spec.shingling, _ShingleIndex())
        self.log.eval_sets.setdefault(spec.name, 0)

    def add_eval_item(self, eval_set: str, item_id: str, text: str) -> None:
        """Index one test item. Every §8.2 test set goes through here before the corpus is read.

        ``text`` is stage-4 output, as everywhere from stage 5 on — the eval sets must be
        normalized by the same pass as the corpus or the comparison measures the normalizer.
        """
        if self._sealed:
            raise RuntimeError(
                "seal() has already run — an eval item added now would never be indexed, so the "
                "corpus would be declared clean of a test set it was never checked against"
            )
        if eval_set not in self._specs:
            self.add_eval_set(EvalSetSpec(name=eval_set))
        spec = self._specs[eval_set]

        position = len(self._eval_id)
        self._eval_set.append(sys.intern(eval_set))
        self._eval_id.append(item_id)
        self._eval_shingling.append(spec.shingling)
        self._eval_threshold.append(
            spec.containment_threshold
            if spec.containment_threshold is not None
            else self.config.containment_threshold
        )
        self._eval_retain.append(
            spec.retain_hits_above
            if spec.retain_hits_above is not None
            else min(self.config.retain_hits_above, self._eval_threshold[position])
        )
        self.log.eval_items += 1
        self.log.eval_sets[eval_set] += 1

        if self.config.exact_document_match:
            self._doc_hashes.setdefault(content_hash(text), position)
        if self.config.exact_line_match:
            for line in lines(text, self.config.min_line_chars):
                if self._line_hashes.setdefault(_line_hash(line), position) == position:
                    self.log.eval_lines += 1

        hashes = shingle_hashes(text, size=spec.shingle_size, unit=spec.shingle_unit)
        self._eval_sizes.append(len(hashes))
        floor = spec.min_shingles if spec.min_shingles is not None else self.config.min_shingles
        if len(hashes) < floor:
            # Counted, never scored — and *reported*, which is the inversion of stage 7's rule.
            # An eval item too short to shingle is contamination stage 8 cannot detect by overlap,
            # so a silent skip would be a false clean bill of health. The exact half still covers
            # it, which is most of why the exact half is not optional.
            self.log.eval_items_unmeasurable += 1
            return

        index = self._indexes[spec.shingling]
        for shingle in hashes:
            if len(index) >= self.config.max_index_shingles:
                raise MemoryError(
                    f"stage 8 eval index hit max_index_shingles="
                    f"{self.config.max_index_shingles:,} — §8.2's test sets are ~6K items, so "
                    "this almost certainly means a corpus was passed as an eval set; the ceiling "
                    "exists so that fails loudly rather than swaps"
                )
            if index.add(shingle, position):
                self.log.eval_shingles += 1

    def seal(self) -> None:
        """Close the eval index. Idempotent. Nothing may be added after the corpus is read."""
        self._sealed = True

    # --- phase 2: stream the corpus ----------------------------------------

    def check(self, doc_id: str, text: str, *, source: str = "") -> DecontaminationVerdict:
        """Score one training document against every test set. Removal is the document's fate.

        **Both halves of §6.3.8 run on every document, and neither short-circuits the other.** The
        exact half names the ``reason`` when it fires, because "this document *is* a test item" is a
        stronger statement than "94% of one is in it" — but the containment scan still runs, so a
        document that duplicates one eval item and contains a second reports both as compromised.
        An exact match is also a containment of 1.0, so the two halves agree wherever both can see;
        where they disagree it is because one of them is blind, which is Finding L in one direction
        and eval items below ``min_shingles`` in the other.
        """
        if not self._sealed:
            raise RuntimeError(
                "seal() has not been called — checking against a half-built eval index would "
                "clear documents against test items that had not been added yet, and the result "
                "would depend on how far the eval loop had got"
            )
        self.log.checked += 1
        self.log.chars_in += len(text)
        if source:
            self.log.by_source[source] += 1

        verdict = self._score(doc_id, text)
        if verdict.kept:
            self.log.kept += 1
            self.log.chars_kept += len(text)
        else:
            self.log.removed += 1
            self.log.removed_by_reason[verdict.reason] += 1
            self.log.removed_by_eval_set[verdict.eval_set] += 1
            if source:
                self.log.removed_by_source[source] += 1
        return verdict

    def _score(self, doc_id: str, text: str) -> DecontaminationVerdict:
        config = self.config

        # The exact half decides the *reason*, but it does not short-circuit the fuzzy half. A
        # document that is an exact copy of one eval item may contain a second one, and returning
        # early would remove the document (right) while reporting only one test item as compromised
        # (wrong). `eval_coverage` is the number §8.2 cares about, and silent under-reporting is
        # this stage's whole failure mode. The extra cost is nil: the exact half fires on ~0.003% of
        # documents, so the containment scan was already running for essentially all of them.
        exact: DecontaminationVerdict | None = None
        if config.exact_document_match:
            position = self._doc_hashes.get(content_hash(text))
            if position is not None:
                exact = self._contaminated(doc_id, position, "exact_document")
        if exact is None and config.exact_line_match and self._line_hashes:
            for line in lines(text, config.min_line_chars):
                position = self._line_hashes.get(_line_hash(line))
                if position is not None:
                    exact = self._contaminated(doc_id, position, "exact_line")
                    break

        worst: DecontaminationVerdict | None = None
        for shingling, index in self._indexes.items():
            if not index.owner:
                continue
            size, unit = shingling
            doc_shingles = shingle_hashes(text, size=size, unit=unit)
            if not doc_shingles:
                continue
            counts = index.tally(doc_shingles)
            if not counts:
                continue
            doc_size = len(doc_shingles)
            for position, intersection in counts.items():
                eval_size = self._eval_sizes[position]
                contained = containment_of(intersection, eval_size)
                if contained < self._eval_retain[position]:
                    continue
                union = eval_size + doc_size - intersection
                similarity = intersection / union if union else 0.0
                self._retain(
                    ContaminationHit(
                        eval_set=self._eval_set[position],
                        eval_id=self._eval_id[position],
                        doc_id=doc_id,
                        containment=contained,
                        jaccard=similarity,
                        intersection=intersection,
                        eval_shingles=eval_size,
                        doc_shingles=doc_size,
                    )
                )
                if contained < self._eval_threshold[position]:
                    continue
                # Every eval item over its own threshold is recorded, not only the one that names
                # the verdict. `eval_coverage` answers "how much of this test set is compromised",
                # and one training row matching nine test items compromises nine of them — on real
                # text that is not hypothetical: Roman-Urdu-Parl:train 58:6137 matches nine spelling
                # variants of one test sentence.
                self._record_hit(self._eval_set[position], self._eval_id[position])
                if worst is None or contained > worst.containment:
                    worst = DecontaminationVerdict(
                        doc_id=doc_id,
                        kept=False,
                        reason="contaminated",
                        eval_set=self._eval_set[position],
                        eval_id=self._eval_id[position],
                        containment=contained,
                    )
        # An exact match names the reason even when a containment hit scored higher: "this document
        # *is* a test item" is a stronger and more legible statement than "94% of one is in it".
        if exact is not None:
            return exact
        if worst is not None:
            return worst
        return DecontaminationVerdict(doc_id=doc_id, kept=True)

    def _contaminated(self, doc_id: str, position: int, reason: str) -> DecontaminationVerdict:
        eval_set = self._eval_set[position]
        eval_id = self._eval_id[position]
        self._record_hit(eval_set, eval_id)
        self._retain(
            ContaminationHit(
                eval_set=eval_set,
                eval_id=eval_id,
                doc_id=doc_id,
                containment=1.0,
                jaccard=1.0 if reason == "exact_document" else 0.0,
                intersection=self._eval_sizes[position],
                eval_shingles=self._eval_sizes[position],
                doc_shingles=0,
                exact=reason.removeprefix("exact_"),
            )
        )
        return DecontaminationVerdict(
            doc_id=doc_id,
            kept=False,
            reason=reason,
            eval_set=eval_set,
            eval_id=eval_id,
            containment=1.0,
        )

    def _record_hit(self, eval_set: str, eval_id: str) -> None:
        self.log.eval_items_hit.setdefault(eval_set, set()).add(eval_id)

    def _retain(self, hit: ContaminationHit) -> None:
        if self.log.hits_retained >= self.config.max_retained_hits:
            raise MemoryError(
                f"stage 8 retained {self.log.hits_retained:,} hits, hitting max_retained_hits — "
                "raise retain_hits_above to keep fewer, or the ceiling to keep them; a sweep over "
                "more hits than fit is not a sweep"
            )
        self.log.hits_retained += 1
        self._hits.append(hit)
        self.log.containment_histogram[_band_label(hit.containment)] += 1
        self.log.jaccard_histogram[_band_label(hit.jaccard)] += 1

    # --- reporting ---------------------------------------------------------

    def hits(self) -> list[ContaminationHit]:
        """Every retained hit, sorted so the strongest evidence reads first."""
        return sorted(
            self._hits, key=lambda hit: (-hit.containment, hit.eval_set, hit.eval_id, hit.doc_id)
        )

    def sweep(self, thresholds: Iterable[float]) -> list[dict]:
        """What stage 8 would have removed at other containment thresholds, exactly.

        Exact rather than a re-run, for every threshold at or above ``retain_hits_above``: the pass
        retained each hit with its measured containment, so re-deciding is a filter over that list.
        Session 6's lesson — a threshold is moved by reading documents, and the pass that measured
        it must hand back what a later reader needs.
        """
        # The honest floor is the *highest* per-set retention floor in play, not the config's. With
        # per-set floors a sweep at 0.6 would be complete for the document sets and silently
        # truncated for the sentence sets, and a single number covering both would be a lie about
        # the half it does not cover.
        floor = max(self._eval_retain, default=self.config.retain_hits_above)
        rows = []
        for threshold in sorted(thresholds):
            if threshold < floor:
                rows.append(
                    {
                        "threshold": threshold,
                        "note": (
                            f"below the highest per-eval-set retain_hits_above ({floor:.2f}) — "
                            "not measured by this pass"
                        ),
                    }
                )
                continue
            documents: set[str] = set()
            items: dict[str, set[str]] = {}
            for hit in self._hits:
                if hit.containment >= threshold:
                    documents.add(hit.doc_id)
                    items.setdefault(hit.eval_set, set()).add(hit.eval_id)
            rows.append(
                {
                    "threshold": threshold,
                    "documents_removed": len(documents),
                    "eval_items_hit": {name: len(ids) for name, ids in sorted(items.items())},
                }
            )
        return rows

    def to_dict(self) -> dict:
        payload = self.log.to_dict()
        payload["eval_specs"] = [spec.to_dict() for _, spec in sorted(self._specs.items())]
        payload["shinglings"] = [
            {"shingle_size": size, "shingle_unit": unit, "distinct_shingles": len(index)}
            for (size, unit), index in sorted(self._indexes.items())
        ]
        payload["top_hits"] = [hit.to_dict() for hit in self.hits()[:200]]
        return payload


def _band_label(value: float) -> str:
    """0.83 -> "0.80-0.90". Ten fixed bands, so two runs' histograms are comparable."""
    if value >= 1.0:
        return "1.00"
    low = int(value * 10) / 10
    return f"{low:.2f}-{low + 0.1:.2f}"


def decontaminate(
    documents: Iterable[tuple[str, str]],
    eval_items: Iterable[tuple[str, str, str]],
    config: DecontaminationConfig | None = None,
    specs: Iterable[EvalSetSpec] = (),
) -> tuple[list[DecontaminationVerdict], DecontaminationLog]:
    """One-shot convenience wrapper: index the eval sets, then check every document."""
    index = Decontaminator(config)
    for spec in specs:
        index.add_eval_set(spec)
    for eval_set, item_id, text in eval_items:
        index.add_eval_item(eval_set, item_id, text)
    index.seal()
    verdicts = [index.check(doc_id, text) for doc_id, text in documents]
    return verdicts, index.log


def main(argv: list[str] | None = None) -> int:
    """Print the shipped defaults, as the other stage modules do."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--config", help="stage-8 config JSON (default: shipped defaults)")
    parser.add_argument("--write-config", help="write the shipped defaults here")
    args = parser.parse_args(argv)

    config = (
        DecontaminationConfig.from_json_file(args.config)
        if args.config
        else DecontaminationConfig()
    )
    if args.write_config:
        config.to_json_file(args.write_config)
        return 0
    print(json.dumps({"fingerprint": config.fingerprint(), **config.to_dict()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
