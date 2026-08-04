"""Exact deduplication — stage 6 of the corpus pipeline (PRD §6.3.6).

Stage 6 is where the corpus stops being a pile of documents and becomes a training set with a
known number of *unique* tokens in it. That number is what PRD §11's Gate G1 is written against
and what arm B's U = 100M is measured in, so it has to come from something that says exactly what
it counted.

Four properties this module is built around.

**1. Which copy survives does not depend on the order the corpus was read in.** This is the
property that costs a second pass, and it is worth it. PRD §6.3's release policy is code,
manifest, checksums and statistics — *no raw text* — so re-running this pipeline is the only way
anyone, including us in week 15, reconstructs the frozen corpus. "Keep the first one you see"
makes that reconstruction depend on read order, and :mod:`ravaan.data.shards` deliberately reads
in a seeded shuffle: a different seed would then produce a different corpus from the same inputs
and the same code. So the survivor of a duplicate group is the document whose *id* hashes lowest
(:func:`document_key`), which is a property of the group rather than of the pass. It is the same
argument :func:`~ravaan.data.shards.stable_unit` makes one stage earlier — shuffling decides what
you look at first, hashing decides what belongs to what — except that here conflating them changes
the corpus rather than a measurement of it.

The cost is that dedup is two-phase: :meth:`ExactDeduplicator.index` over the whole corpus, then
:meth:`ExactDeduplicator.decide` over it again. Phase 1 stores one integer per distinct document,
not a document, so the second read is the price rather than the memory.

**2. Normalized text decides; raw text is measured beside it.** §6.3.6 asks for "raw and
normalized hashes", and Finding F (session 5) turned that into a prediction: Arabic-variant
spelling is a property of *publishers* — the top 1% of domains carry 65.3% of all variant hits —
and religious publishers republish the same hadith and tafsir texts across many domains. If that
is right, hashing after stage 4 finds duplicates that hashing before it misses, because the two
copies differ only in which keyboard typed them. Both hashes are computed for every document, one
decides and the other is counted, so the report states the difference as a measured number instead
of as the reason the stages are in this order.

**3. Canonicalization before hashing is whitespace collapse and case folding, and nothing else.**
Every further "harmless" fold — stripping punctuation, dropping harakat, sorting lines — turns
this into a *near*-dedup with an unstated similarity threshold, which is stage 7's job and which
stage 7 does with a measurable one. Whitespace is in because every HTML-to-text extractor wraps
differently and two copies of an article differing only in line breaks are one document by any
reading. Case folding is free on Urdu, which has no case, and load-bearing on the Roman Urdu
population, which has no standard orthography either. Both variants get the identical treatment,
so the raw-vs-normalized delta measures stage 4 and not the canonicalizer.

**4. The output is a decision, not a corpus.** :meth:`decide` returns a verdict per document; what
gets written is a list of removed ids and a statistics block. That is what the release policy can
ship, and it is what lets someone who cannot be given the text still check the corpus.

**Paragraph level measures; it does not rewrite.** §6.3.6 asks for document *and* paragraph level.
Paragraph-level counting runs inside phase 2 over the documents that survived document-level
dedup — counting it in phase 1 would inflate every line's count by exactly the copies stage 6 is
about to delete — and reports how much duplicated line volume the corpus carries.
:meth:`ExactDeduplicator.strip` will act on it, in a third pass, and is off unless a caller asks:
dropping a line out of the middle of a document is a rewrite, stage 5's reject-do-not-repair
doctrine applies for the same reason, and it silently invalidates the 400-character floor stage 5
applied one stage earlier.

    index = ExactDeduplicator()
    for doc in corpus:                                    # phase 1
        index.index(doc.doc_id, normalized(doc), raw=doc.text, source=doc.source)
    for doc in corpus:                                    # phase 2
        verdict = index.decide(doc.doc_id, normalized(doc), raw=doc.text, source=doc.source)
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path

__all__ = [
    "DEDUP_VERSION",
    "DedupConfig",
    "DedupLog",
    "DedupVerdict",
    "ExactDeduplicator",
    "StripResult",
    "canonical",
    "content_hash",
    "deduplicate",
    "document_key",
    "lines",
]

# Bump on any change to which documents survive: the canonical form, the hash, the survivor rule.
# The manifest records it, so a frozen corpus can be traced to the exact pass that produced it.
DEDUP_VERSION = "1.0.0"

# blake2b personalisation (<= 16 bytes). Two independent keyed spaces out of one primitive:
# content hashes decide group membership, id hashes decide who wins a group, and nothing good
# happens if a document's id can collide with some other document's text.
_CONTENT_PERSON = b"ravaan/dedup/c"
_KEY_PERSON = b"ravaan/dedup/k"

_WHITESPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def canonical(text: str, *, collapse_whitespace: bool = True, casefold: bool = True) -> str:
    """The form two documents must share, character for character, to count as duplicates.

    Whitespace collapse is not cosmetic. FineWeb2 and Urdu Wikipedia come from different
    extractors, and session 4 measured stage 4 firing 11.34 whitespace fixes per Wikipedia
    document against 0.02 per FineWeb2 document: two copies of one article that differ only in
    where the lines wrap are one document, and without this they are two.

    Case folding costs nothing on Arabic-script Urdu — the script has no case — and matters on the
    Roman Urdu population, where ``Aik`` and ``aik`` are the same word typed by two crowdworkers.
    """
    text = _WHITESPACE_RE.sub(" ", text).strip() if collapse_whitespace else text.strip()
    return text.casefold() if casefold else text


def _digest(payload: bytes, person: bytes, bits: int) -> int:
    return int.from_bytes(
        hashlib.blake2b(payload, digest_size=bits // 8, person=person).digest(), "big"
    )


def content_hash(
    text: str,
    *,
    bits: int = 128,
    collapse_whitespace: bool = True,
    casefold: bool = True,
) -> int:
    """Hash of a document's canonical form.

    blake2b rather than the builtin ``hash``, which is salted per process by PYTHONHASHSEED and
    would put the same document in a different group on every run — the same reason
    :func:`~ravaan.data.shards.stable_unit` does not use it either.
    """
    canonicalized = canonical(text, collapse_whitespace=collapse_whitespace, casefold=casefold)
    return _digest(canonicalized.encode("utf-8"), _CONTENT_PERSON, bits)


def document_key(doc_id: str, *, bits: int = 128) -> int:
    """The tie-break that decides which member of a duplicate group survives.

    A hash of the id rather than the id itself, because ``min(doc_id)`` is not a neutral choice:
    Urdu Wikipedia's ids are short integers and FineWeb2's are UUID URNs, so a lexicographic
    minimum would award *every* cross-source duplicate to whichever source sorts first and quietly
    rewrite the per-source composition table. Hashing keeps the choice proportional to the sources
    that are actually there.
    """
    return _digest(doc_id.encode("utf-8"), _KEY_PERSON, bits)


def lines(text: str, min_chars: int = 0) -> Iterator[str]:
    """Non-empty stripped lines of at least ``min_chars`` — the unit for sub-document dedup.

    "Paragraph" in §6.3.6 and "line" here are the same object for this corpus: both sources arrive
    as extracted text in which a paragraph *is* a line, and splitting on blank lines instead would
    put a nav bar, its five links and the article's opening paragraph into one unit. Splitting on
    a single newline is also what makes removal losslessly rejoinable, since no separator is
    discarded.
    """
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and len(stripped) >= min_chars:
            yield stripped


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VARIANTS = ("normalized", "raw")
PARAGRAPH_MODES = ("off", "measure")


@dataclass(frozen=True, slots=True)
class DedupConfig:
    """Stage 6 settings. Defaults are the Ravaan corpus v1 settings."""

    # 128 bits, and the reason is arithmetic rather than caution. A collision here does not
    # mis-file a document, it *deletes* one: two unrelated texts become one group and the loser is
    # dropped with no trace in any log, which is the one failure mode this stage cannot detect
    # afterwards. At 64 bits over the ~15M line hashes a full FineWeb2 shard produces, the
    # birthday bound puts the chance of at least one such deletion near 1e-5; at 128 bits it is
    # ~1e-24. The difference costs one machine word per distinct unit.
    hash_bits: int = 128

    collapse_whitespace: bool = True
    casefold: bool = True

    # Which text the decision is made on. The other is hashed and reported, never acted on — see
    # the module docstring on Finding F.
    variant: str = "normalized"
    measure_alternate: bool = True

    paragraph_mode: str = "measure"
    # Below this a line is not a paragraph, it is furniture: a date, a byline, a section heading, a
    # "مزید پڑھیں". Those recur across a site by design, and indexing them measures the site's
    # template rather than the corpus's redundancy. 60 characters is roughly one Urdu clause.
    min_paragraph_chars: int = 60
    # How many *distinct documents* a line must appear in to count as duplicated. 2 is the honest
    # floor for an exact-dedup stage; raising it turns the rule into boilerplate detection, which
    # is a different claim about a different thing.
    paragraph_min_documents: int = 2

    # Phase 1 holds one dict entry per distinct unit and nothing else, but "nothing else" times a
    # few tens of millions is still gigabytes. Fail loudly at a stated ceiling rather than swap.
    max_index_entries: int = 40_000_000

    def __post_init__(self) -> None:
        if self.hash_bits % 64 or not 64 <= self.hash_bits <= 512:
            raise ValueError(f"hash_bits must be a multiple of 64 in [64, 512]: {self.hash_bits}")
        if self.variant not in VARIANTS:
            raise ValueError(f"variant must be one of {VARIANTS}, got {self.variant!r}")
        if self.paragraph_mode not in PARAGRAPH_MODES:
            raise ValueError(
                f"paragraph_mode must be one of {PARAGRAPH_MODES}, got {self.paragraph_mode!r}"
            )
        if self.min_paragraph_chars < 0:
            raise ValueError("min_paragraph_chars must be >= 0")
        if self.paragraph_min_documents < 2:
            raise ValueError("paragraph_min_documents must be >= 2 — 1 would mean every line")
        if self.max_index_entries < 1:
            raise ValueError("max_index_entries must be >= 1")

    @property
    def alternate_variant(self) -> str:
        """The variant that is measured rather than acted on."""
        return "raw" if self.variant == "normalized" else "normalized"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> DedupConfig:
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known - {"dedup_version", "_comment"}
        if unknown:
            raise ValueError(f"unknown dedup config keys: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json_file(cls, path: str | Path) -> DedupConfig:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json_file(self, path: str | Path) -> None:
        payload = {"dedup_version": DEDUP_VERSION, **self.to_dict()}
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"version": DEDUP_VERSION, **self.to_dict()}, sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DedupVerdict:
    """One document's fate, with the group that decided it."""

    doc_id: str
    kept: bool
    group: str = ""  # the deciding hash, truncated for legibility; a group of one still has one
    group_size: int = 1
    reason: str = ""  # "" | "duplicate_document"

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "kept": self.kept,
            "group": self.group,
            "group_size": self.group_size,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class StripResult:
    """What paragraph-level removal did to one document — phase 3, opt-in."""

    text: str
    paragraphs_removed: int = 0
    chars_removed: int = 0
    emptied: bool = False  # every line was a duplicate; left whole, see ExactDeduplicator.strip


@dataclass
class DedupLog:
    """Corpus-level aggregate — the stage-6 line of the manifest and the statistics table.

    Filled across both phases: the group structure is known at the end of phase 1, the character
    accounting and everything paragraph-level only during phase 2.
    """

    config: DedupConfig = field(default_factory=DedupConfig)

    # --- phase 1: the group structure ---
    indexed: int = 0
    duplicate_groups: int = 0  # groups with more than one member
    duplicate_documents: int = 0  # members beyond the first, i.e. what stage 6 will remove
    largest_group: int = 0
    # What hashing the *other* variant would have removed instead. The Finding F measurement: if
    # normalizing before hashing surfaces cross-publisher duplicates, this number is smaller.
    alternate_duplicate_documents: int = 0
    # Groups whose members do not all come from one source. CommonCrawl crawls Wikipedia, so
    # FineWeb2 contains Wikipedia; this is the size of that overlap, and stage 8 cares because
    # Wikipedia is also where §8.2's held-out evaluation text comes from.
    cross_source_groups: int = 0
    cross_source_pairs: Counter[str] = field(default_factory=Counter)

    # --- phase 2: what it cost ---
    documents: int = 0
    documents_kept: int = 0
    chars_in: int = 0
    chars_kept: int = 0
    by_source: Counter[str] = field(default_factory=Counter)
    kept_by_source: Counter[str] = field(default_factory=Counter)
    removed_by_source: Counter[str] = field(default_factory=Counter)
    # Of those removals, the ones whose group spans more than one source — i.e. documents dropped
    # because another *source* already had them, not because the source repeats itself. Without
    # this split a joint run cannot report either number: a source's removals are the sum of the
    # two, and the two mean different things to §6.1's budget and to stage 8's decontamination.
    removed_cross_source_by_source: Counter[str] = field(default_factory=Counter)

    # --- paragraph level, measured over document-level survivors ---
    paragraph_units: int = 0  # line occurrences, deduplicated within a document
    paragraph_distinct: int = 0
    paragraph_duplicate_units: int = 0
    paragraph_chars: int = 0
    paragraph_chars_duplicated: int = 0  # every copy of every line seen in >= N documents
    paragraph_chars_removable: int = 0  # the same, minus one surviving copy of each

    # --- phase 3, only if a caller asked for it ---
    paragraph_documents_changed: int = 0
    paragraphs_removed: int = 0
    paragraph_chars_removed: int = 0
    paragraph_documents_emptied: int = 0

    @property
    def keep_rate(self) -> float:
        return self.documents_kept / self.documents if self.documents else 0.0

    @property
    def char_keep_rate(self) -> float:
        return self.chars_kept / self.chars_in if self.chars_in else 0.0

    @property
    def duplicate_rate(self) -> float:
        return self.duplicate_documents / self.indexed if self.indexed else 0.0

    @property
    def paragraph_removable_share(self) -> float:
        if not self.paragraph_chars:
            return 0.0
        return self.paragraph_chars_removable / self.paragraph_chars

    def to_dict(self) -> dict:
        return {
            "dedup_version": DEDUP_VERSION,
            "config_fingerprint": self.config.fingerprint(),
            "config": self.config.to_dict(),
            "indexed": self.indexed,
            "duplicate_groups": self.duplicate_groups,
            "duplicate_documents": self.duplicate_documents,
            "duplicate_rate": round(self.duplicate_rate, 6),
            "largest_group": self.largest_group,
            "variant": self.config.variant,
            "alternate_variant": self.config.alternate_variant,
            "alternate_duplicate_documents": self.alternate_duplicate_documents,
            "cross_source_groups": self.cross_source_groups,
            "cross_source_pairs": dict(sorted(self.cross_source_pairs.items())),
            "documents": self.documents,
            "documents_kept": self.documents_kept,
            "documents_removed": self.documents - self.documents_kept,
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
            "paragraph_mode": self.config.paragraph_mode,
            "paragraph_units": self.paragraph_units,
            "paragraph_distinct": self.paragraph_distinct,
            "paragraph_duplicate_units": self.paragraph_duplicate_units,
            "paragraph_chars": self.paragraph_chars,
            "paragraph_chars_duplicated": self.paragraph_chars_duplicated,
            "paragraph_chars_removable": self.paragraph_chars_removable,
            "paragraph_removable_share": round(self.paragraph_removable_share, 6),
            "paragraph_documents_changed": self.paragraph_documents_changed,
            "paragraphs_removed": self.paragraphs_removed,
            "paragraph_chars_removed": self.paragraph_chars_removed,
            "paragraph_documents_emptied": self.paragraph_documents_emptied,
        }


# ---------------------------------------------------------------------------
# The deduplicator
# ---------------------------------------------------------------------------


class ExactDeduplicator:
    """Two-phase exact dedup: :meth:`index` over the corpus, then :meth:`decide` over it again.

    Phase 1 records, for each distinct canonical text, the lowest document key that produced it.
    Phase 2 keeps a document exactly when its own key is that minimum. Neither phase looks at
    arrival order, so the surviving set is a function of the corpus and the config alone — which
    is what makes a corpus released as "code + manifest + checksums" reconstructible at all.

    Memory is dict entries per *distinct* unit and no text. Measured with ``tracemalloc`` at
    ``hash_bits=128``: **193 bytes** per distinct document, or **279** with ``measure_alternate``
    on, which is the second hash set. FineWeb2's 1,547,542-document shard therefore indexes in
    ~300 MB, or ~430 MB with the raw-variant comparison. ``max_index_entries`` is the stated
    ceiling, and exceeding it raises rather than swaps.
    """

    def __init__(
        self,
        config: DedupConfig | None = None,
        *,
        track_sources: bool = True,
        example_groups: int = 200,
    ) -> None:
        self.config = config or DedupConfig()
        self.track_sources = track_sources
        self.example_groups = example_groups
        self.log = DedupLog(config=self.config)

        self._bits = self.config.hash_bits
        self._hex = self._bits // 4
        self._hash_kwargs = {
            "bits": self._bits,
            "collapse_whitespace": self.config.collapse_whitespace,
            "casefold": self.config.casefold,
        }

        # hash -> lowest document key seen for it. The whole decision, one integer per group.
        self._best: dict[int, int] = {}
        self._repeats: dict[int, int] = {}
        # Per-group side tables, all of them deliberately *not* sized by the number of groups.
        # Roman-Urdu-Parl is the case that forces this: PRD §6.2 predicts its 6.37M pairs collapse
        # to ~1.09M unique Urdu sentences, so nearly every group repeats, and a four-id example
        # list plus a source set per group is about a gigabyte of Python objects to describe a
        # corpus we could otherwise index in a tenth of that. So: sources are stored only for
        # groups that genuinely span sources, and example ids only for the largest
        # ``example_groups`` groups, chosen in :meth:`seal` once the sizes are known.
        self._group_sources: dict[int, set[str]] = {}
        self._group_examples: dict[int, list[str]] = {}
        self._group_keeper: dict[int, str] = {}
        self._tracked: frozenset[int] = frozenset()
        # hash -> source of the first member, so a repeat can name both sides of a cross-source
        # group. Source names are few and interned, so this is one pointer per distinct document.
        self._source_of: dict[int, str] = {}
        # Membership only: the alternate variant is counted, never acted on, so it needs no winner.
        self._alternate: set[int] = set()

        # Line hash -> (documents containing it, its length, lowest key). Accumulated in phase 2
        # over document-level survivors only: counting lines in phase 1 would inflate every count
        # by exactly the copies stage 6 is about to delete.
        self._para_docs: dict[int, int] = {}
        self._para_len: dict[int, int] = {}
        self._para_best: dict[int, int] = {}

        self._sealed = False
        self._paragraphs_final = False

    # --- phase 1 -----------------------------------------------------------

    def index(self, doc_id: str, text: str, *, raw: str | None = None, source: str = "") -> None:
        """Record one document. Call over the whole corpus before any :meth:`decide`.

        ``text`` is the stage-4 output and ``raw`` the pre-normalization text. Which of the two
        decides is :attr:`DedupConfig.variant`; the other is counted for the comparison.
        """
        deciding, alternate = self._texts(text, raw)
        digest = content_hash(deciding, **self._hash_kwargs)
        key = document_key(doc_id, bits=self._bits)
        self.log.indexed += 1

        previous = self._best.get(digest)
        if previous is None:
            self._guard(len(self._best), "document")
            self._best[digest] = key
            if self.track_sources and source:
                self._source_of[digest] = sys.intern(source)
        else:
            if key < previous:
                self._best[digest] = key
            count = self._repeats.get(digest, 1) + 1
            self._repeats[digest] = count
            self.log.duplicate_documents += 1
            if count == 2:
                self.log.duplicate_groups += 1
            if count > self.log.largest_group:
                self.log.largest_group = count
            if self.track_sources and source:
                self._track_source(digest, source)

        if self.config.measure_alternate and alternate is not None:
            alternate_digest = content_hash(alternate, **self._hash_kwargs)
            if alternate_digest in self._alternate:
                self.log.alternate_duplicate_documents += 1
            else:
                self._alternate.add(alternate_digest)

    def _track_source(self, digest: int, source: str) -> None:
        """Record a group's sources — but only once it has more than one.

        A single-source group's source is already in ``_source_of``; allocating a set to say so
        again costs 216 bytes per group, which is the difference between indexing Roman-Urdu-Parl
        in 300 MB and in 1.3 GB.
        """
        sources = self._group_sources.get(digest)
        if sources is not None:
            sources.add(source)  # already counted as cross-source when the set was created
            return
        first = self._source_of.get(digest)
        if first is None or first == source:
            return
        self._group_sources[digest] = {first, source}
        self.log.cross_source_groups += 1

    def _guard(self, size: int, what: str) -> None:
        if size >= self.config.max_index_entries:
            raise MemoryError(
                f"stage 6 {what} index hit max_index_entries="
                f"{self.config.max_index_entries:,} at {self.log.indexed:,} documents — raise it "
                "deliberately or shard the pass; it exists so this fails loudly rather than swaps"
            )

    def seal(self) -> None:
        """Close phase 1 and derive what only the finished group structure knows.

        Which groups are worth naming is one of those things: their sizes are final now, so phase
        2 can collect example ids for the largest ``example_groups`` of them and for nothing else.
        Collecting during phase 1 would mean either keeping ids for every group that ever repeats —
        a million of them on Roman-Urdu-Parl — or keeping the first ones seen, which is read order
        deciding what the report shows.
        """
        if self._sealed:
            return
        self._sealed = True
        for sources in self._group_sources.values():
            for left, right in itertools.combinations(sorted(sources), 2):
                self.log.cross_source_pairs[f"{left}|{right}"] += 1
        ranked = sorted(self._repeats.items(), key=lambda item: (-item[1], item[0]))
        self._tracked = frozenset(digest for digest, _ in ranked[: self.example_groups])

    # --- phase 2 -----------------------------------------------------------

    def decide(
        self, doc_id: str, text: str, *, raw: str | None = None, source: str = ""
    ) -> DedupVerdict:
        """Keep or drop one document, and count its lines if it survives.

        Raises if the document was not seen in phase 1. That is not defensiveness: a phase 2 that
        reads a different document set than phase 1 — a changed sample rate, a limit, a checkpoint
        resumed from another plan — would drop every unseen document silently and the corpus would
        simply come out short. The loud version is the useful one.
        """
        self.seal()
        deciding, _ = self._texts(text, raw)
        digest = content_hash(deciding, **self._hash_kwargs)
        best = self._best.get(digest)
        if best is None:
            raise KeyError(
                f"{doc_id!r} was not indexed in phase 1 — phase 2 is reading a different document "
                "set than phase 1 did, which would silently shorten the corpus"
            )

        log = self.log
        log.documents += 1
        log.chars_in += len(deciding)
        if source:
            log.by_source[source] += 1

        group = f"{digest:0{self._hex}x}"[:16]
        group_size = self._repeats.get(digest, 1)
        key = document_key(doc_id, bits=self._bits)

        if key != best:
            if source:
                log.removed_by_source[source] += 1
                if len(self._group_sources.get(digest, ())) > 1:
                    log.removed_cross_source_by_source[source] += 1
            if digest in self._tracked:
                examples = self._group_examples.setdefault(digest, [])
                if len(examples) < 4:
                    examples.append(doc_id)
            return DedupVerdict(doc_id, False, group, group_size, "duplicate_document")

        if digest in self._tracked:
            self._group_keeper[digest] = doc_id
        log.documents_kept += 1
        log.chars_kept += len(deciding)
        if source:
            log.kept_by_source[source] += 1
        if self.config.paragraph_mode != "off":
            self._paragraphs_final = False
            self._count_paragraphs(deciding, key)

        return DedupVerdict(doc_id, True, group, group_size)

    def _count_paragraphs(self, text: str, key: int) -> None:
        seen: set[int] = set()
        for line in lines(text, self.config.min_paragraph_chars):
            digest = content_hash(line, **self._hash_kwargs)
            # A line repeated *inside* one document is stage 5's dup_line_ratio, not stage 6's
            # business; counting it here would make one bad page look like corpus-wide boilerplate.
            if digest in seen:
                continue
            seen.add(digest)
            count = self._para_docs.get(digest, 0)
            if count == 0:
                self._guard(len(self._para_docs), "paragraph")
                self._para_len[digest] = len(line)
                self._para_best[digest] = key
            elif key < self._para_best[digest]:
                self._para_best[digest] = key
            self._para_docs[digest] = count + 1

    def finish_paragraphs(self) -> None:
        """Roll the line index up into the log, and close phase 2. Idempotent."""
        self._paragraphs_final = True
        log = self.log
        minimum = self.config.paragraph_min_documents
        units = duplicate_units = chars = duplicated = removable = 0
        for digest, count in self._para_docs.items():
            length = self._para_len[digest]
            units += count
            chars += count * length
            if count >= minimum:
                duplicate_units += count
                duplicated += count * length
                removable += (count - 1) * length
        log.paragraph_units = units
        log.paragraph_distinct = len(self._para_docs)
        log.paragraph_duplicate_units = duplicate_units
        log.paragraph_chars = chars
        log.paragraph_chars_duplicated = duplicated
        log.paragraph_chars_removable = removable

    # --- phase 3, opt-in ---------------------------------------------------

    def strip(self, doc_id: str, text: str) -> StripResult:
        """Drop the lines this document shares with others. A third pass, and off by default.

        Only correct once phase 2 has run over the whole corpus, because that is when the line
        counts are complete — so it refuses until :meth:`finish_paragraphs` has been called with no
        :meth:`decide` after it. Stripping against half-built counts would leave every line whose
        second copy had not been read yet, which is a corpus that depends on where the pass got to.

        Kept separate from :meth:`decide` for the reason in the module docstring: this rewrites a
        document rather than judging it, and it can push one back under the 400-character floor
        stage 5 applied one stage earlier — so a caller that uses this owes the corpus a second
        stage-5 pass.
        """
        if self.config.paragraph_mode == "off":
            raise RuntimeError("paragraph_mode is 'off' — nothing was counted to strip against")
        if not self._paragraphs_final:
            raise RuntimeError(
                "call finish_paragraphs() after the last decide() before stripping — the line "
                "counts are only complete once phase 2 has read the whole corpus"
            )
        config = self.config
        key = document_key(doc_id, bits=self._bits)
        kept_lines: list[str] = []
        removed = 0
        removed_chars = 0

        for line in text.split("\n"):
            stripped = line.strip()
            if stripped and len(stripped) >= config.min_paragraph_chars:
                digest = content_hash(stripped, **self._hash_kwargs)
                if (
                    self._para_docs.get(digest, 0) >= config.paragraph_min_documents
                    and self._para_best.get(digest) != key
                ):
                    removed += 1
                    removed_chars += len(line)
                    continue
            kept_lines.append(line)

        if not removed:
            return StripResult(text)
        surviving = "\n".join(kept_lines).strip()
        if not surviving:
            # Every line of this document lives somewhere else. That is a near-duplicate finding,
            # not a removal instruction: leave it whole and let stage 7 cluster it, because the
            # alternative is a corpus with empty documents in it.
            self.log.paragraph_documents_emptied += 1
            return StripResult(text, emptied=True)
        self.log.paragraph_documents_changed += 1
        self.log.paragraphs_removed += removed
        self.log.paragraph_chars_removed += removed_chars
        return StripResult(surviving, removed, removed_chars)

    # --- reporting ---------------------------------------------------------

    def _texts(self, text: str, raw: str | None) -> tuple[str, str | None]:
        """``(the text the decision is made on, the text measured beside it)``."""
        if raw is None:
            return text, None
        if self.config.variant == "raw":
            return raw, text
        return text, raw

    def is_kept(self, doc_id: str, text: str, *, raw: str | None = None) -> bool:
        """Whether this document is its group's survivor. Read-only; does not touch the log."""
        deciding, _ = self._texts(text, raw)
        digest = content_hash(deciding, **self._hash_kwargs)
        best = self._best.get(digest)
        return best is not None and document_key(doc_id, bits=self._bits) == best

    @property
    def distinct_documents(self) -> int:
        return len(self._best)

    @property
    def tracked_groups(self) -> frozenset[str]:
        """The group ids :meth:`top_groups` will report — capture example *text* for these only.

        A caller that keeps a snippet for every duplicate group it meets is keeping a million of
        them on Roman-Urdu-Parl, and capping that by arrival order means the report shows whichever
        groups the read order reached first rather than the largest. Sizes are final after
        :meth:`seal`, so the set of groups worth illustrating is knowable before phase 2 starts.
        """
        self.seal()
        return frozenset(f"{digest:0{self._hex}x}"[:16] for digest in self._tracked)

    def top_groups(self, limit: int = 20) -> list[dict]:
        """The largest duplicate groups, for the report and for reading by hand.

        ``kept`` and ``duplicates`` are populated during phase 2 and only for the largest
        ``example_groups`` groups, so asking for more than that returns sizes without ids.
        """
        ranked = sorted(self._repeats.items(), key=lambda item: (-item[1], item[0]))
        return [
            {
                "group": f"{digest:0{self._hex}x}"[:16],
                "size": size,
                "sources": sorted(
                    self._group_sources.get(digest)
                    or ([self._source_of[digest]] if digest in self._source_of else ())
                ),
                "kept": self._group_keeper.get(digest, ""),
                "duplicates": self._group_examples.get(digest, []),
            }
            for digest, size in ranked[:limit]
        ]

    def to_dict(self) -> dict:
        self.seal()
        self.finish_paragraphs()
        payload = self.log.to_dict()
        payload["distinct_documents"] = self.distinct_documents
        payload["top_groups"] = self.top_groups()
        return payload


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def deduplicate(
    documents: Iterable[tuple], config: DedupConfig | None = None
) -> tuple[list[DedupVerdict], ExactDeduplicator]:
    """Both phases over a collection of ``(doc_id, text[, raw[, source]])``.

    For tests and for samples small enough to hold in memory. The corpus pass drives the two
    phases directly against a :class:`~ravaan.data.shards.ShardReader`, which re-iterates without
    materialising anything.
    """
    records = [tuple(record) for record in documents]
    index = ExactDeduplicator(config)
    for record in records:
        index.index(record[0], record[1], raw=_at(record, 2), source=_at(record, 3) or "")
    verdicts = [
        index.decide(record[0], record[1], raw=_at(record, 2), source=_at(record, 3) or "")
        for record in records
    ]
    return verdicts, index


def _at(record: tuple, position: int):
    return record[position] if len(record) > position else None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("input", nargs="?", help="JSONL file (default: stdin)")
    parser.add_argument("-c", "--config", help="dedup config JSON")
    parser.add_argument("--field", default="text", help="text field (default: text)")
    parser.add_argument("--raw-field", help="pre-normalization text field, for the comparison")
    parser.add_argument("--id-field", default="doc_id", help="id field (default: doc_id)")
    parser.add_argument("--source-field", default="source", help="source field (default: source)")
    parser.add_argument("--removals", help="write the removed ids here, one per line")
    parser.add_argument("--log", help="write the stage-6 log here as JSON")
    args = parser.parse_args(argv)

    config = DedupConfig.from_json_file(args.config) if args.config else DedupConfig()
    payload = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    records = [json.loads(line) for line in payload.splitlines() if line.strip()]

    def fields(record: dict) -> dict:
        return {
            "raw": record.get(args.raw_field) if args.raw_field else None,
            "source": record.get(args.source_field, ""),
        }

    index = ExactDeduplicator(config)
    for record in records:
        index.index(record[args.id_field], record[args.field], **fields(record))

    removed: list[str] = []
    for record in records:
        verdict = index.decide(record[args.id_field], record[args.field], **fields(record))
        if not verdict.kept:
            removed.append(verdict.doc_id)
        print(json.dumps(verdict.to_dict(), ensure_ascii=False))

    if args.removals:
        Path(args.removals).write_text(
            "".join(f"{doc_id}\n" for doc_id in removed), encoding="utf-8", newline="\n"
        )

    report = json.dumps(index.to_dict(), indent=2, ensure_ascii=False)
    if args.log:
        Path(args.log).write_text(report + "\n", encoding="utf-8", newline="\n")
    else:
        print(report, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
