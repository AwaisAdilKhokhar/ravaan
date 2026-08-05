"""Carry one stage's removals into the next pass — PRD §6.3's freeze order, made executable.

Stages 6, 7 and 8 each decide which documents leave the corpus, and each decides on a property of a
*pair* or of the *whole corpus*, so none of them can be decided inside the pass that writes the
corpus. The freeze order is therefore 6 → 7 → 9 → 8 → 10: five passes that hand a set of document
ids forward. Until this module existed there was no hand. ``scripts/dedup.py``,
``scripts/neardedup.py`` and ``scripts/decontaminate.py`` all *write* ``--removals``; neither
``scripts/split.py`` nor ``scripts/pack.py`` could read one. **Stage 10 would have packed a corpus
that had never been deduplicated, and stage 9 would have carved its held-out split from a pool still
full of the near-duplicates stage 7 exists to remove.**

The list of ids is the easy half. The hard half is that **a list of ids carries no evidence of the
corpus it was computed over**, and every way of getting that wrong is silent:

* A list computed at ``--sample-rate 0.05`` and applied to a full pass removes a twentieth of what
  it should — and *every id in it matches*, so no count anywhere is out of place.
* A list computed under ``--limit 20000`` does the same, and :meth:`ShardReader.plan_fingerprint`
  cannot see it: the fingerprint covers files, layout, order, seed and sample rate, deliberately
  not the limit, because a limit does not change which documents come in what order.
* A source read with **no** list is the freeze order not having been run for it, which looks exactly
  like a source that had nothing to remove.

So the file carries a header naming the read plan of every source it covers, the consuming pass
checks its own readers against that header, and a source with no coverage is *reported* rather than
assumed clean. This is stage 1's licence gate again and stage 5's ``sole_rejections`` again: a check
that gets made once during planning and then drifts is a check that has to execute.

The file is still a plain list of ids, one per line, with ``#`` comments — so a human can read it,
``wc -l`` still nearly works, and the headerless files written before this module (
``reports/dedup_removals_wikipedia.txt``) still load, against a stated warning rather than a crash.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

EXCLUSIONS_VERSION = "1.0.0"

# Deliberately a comment line: a consumer that does not know about headers reads it as a comment,
# and `grep -v '^#'` is still the whole file format.
_HEADER_PREFIX = "#!ravaan-exclusions "


@dataclass(frozen=True)
class ReadPlan:
    """One source's read, as the pass that produced an exclusion list saw it.

    ``plan_fingerprint`` alone is not enough and ``limit`` is the reason: it is not part of the
    fingerprint, because a limit does not change *which documents in what order* — it changes how
    many of them you stop after. That is exactly the difference between a removal list computed on
    a 20,000-document smoke test and one computed on the corpus.
    """

    source: str
    plan_fingerprint: str
    limit: int | None = None
    sample_rate: float | None = None

    @classmethod
    def of(cls, reader) -> ReadPlan:
        """The plan of a :class:`ravaan.data.shards.ShardReader` reading exactly one source."""
        sources = sorted({f.source for f in reader.files})
        if len(sources) != 1:
            raise ValueError(
                f"an exclusion list is recorded per source, but this reader spans {sources} — "
                "build one reader per source, as every driver already does"
            )
        return cls(
            source=sources[0],
            plan_fingerprint=reader.plan_fingerprint(),
            limit=reader.limit,
            sample_rate=reader.sample_rate,
        )

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "plan_fingerprint": self.plan_fingerprint,
            "limit": self.limit,
            "sample_rate": self.sample_rate,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReadPlan:
        return cls(
            source=data["source"],
            plan_fingerprint=data["plan_fingerprint"],
            limit=data.get("limit"),
            sample_rate=data.get("sample_rate"),
        )

    def describe(self) -> str:
        limit = "all" if not self.limit else f"{self.limit:,}"
        rate = "1.0" if self.sample_rate is None else f"{self.sample_rate:g}"
        return f"plan {self.plan_fingerprint} limit {limit} rate {rate}"


@dataclass(frozen=True)
class ExclusionHeader:
    """What a removal list says about itself: which stage removed, over which read of which sources.

    ``stage`` is free text (``"6"``, ``"6+7"``, ``"8"``) and is reported rather than checked. What
    is checked is :attr:`plans` — the identity of the read — because that is the part whose being
    wrong produces a corpus rather than an error.
    """

    stage: str
    plans: tuple[ReadPlan, ...] = ()
    count: int = 0
    version: str = EXCLUSIONS_VERSION

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "stage": self.stage,
            "count": self.count,
            "plans": [plan.to_dict() for plan in self.plans],
        }

    @classmethod
    def from_dict(cls, data: dict) -> ExclusionHeader:
        return cls(
            stage=str(data.get("stage", "?")),
            plans=tuple(ReadPlan.from_dict(p) for p in data.get("plans", ())),
            count=int(data.get("count", 0)),
            version=str(data.get("version", "?")),
        )


@dataclass
class Coverage:
    """What :meth:`ExclusionSet.check` found, for the pass to print before it reads anything.

    Every field is a list of source names rather than a verdict, because the three cases have
    genuinely different meanings and merging them into "ok / not ok" would name none of them.
    """

    covered: tuple[str, ...] = ()
    uncovered: tuple[str, ...] = ()
    headerless: tuple[str, ...] = ()
    stages: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "covered": list(self.covered),
            "uncovered": list(self.uncovered),
            "headerless": list(self.headerless),
            "stages": list(self.stages),
        }

    @property
    def empty(self) -> bool:
        """No list was passed at all — as against a list that covers some sources and not others."""
        return not (self.covered or self.stages or self.headerless)

    def report(self) -> Iterator[str]:
        if self.empty:
            # One line rather than one per source. A measurement pass legitimately runs without
            # exclusions and should not be buried in warnings; a *freeze* pass that runs without
            # them is a bug, and this is the line that says so.
            yield (
                "  no --exclude given: this pass reads text that has been through no stage 6, 7 "
                "or 8 removal. Correct for a measurement, wrong for the freeze"
            )
            return
        if self.stages:
            yield f"  removals from stage(s) {', '.join(self.stages)}"
        for source in self.covered:
            yield f"  {source:<24} covered"
        for path in self.headerless:
            yield (
                f"  !! {path} carries no header — it cannot be checked against this read. "
                "It was written before exclusions had provenance; re-run the pass that produced "
                "it, or accept that a list from a sampled or limited run is indistinguishable "
                "from one over the corpus"
            )
        for source in self.uncovered:
            yield (
                f"  !! {source:<21} NO exclusions — either it has been through no earlier stage "
                "or its removal list was not passed. The freeze order (6 → 7 → 9 → 8 → 10) "
                "requires one per source"
            )


class ExclusionSet:
    """Document ids an earlier stage removed, plus the evidence of what they were computed over.

    Membership is the whole runtime interface — ``doc_id in exclusions`` — and the counting is a
    side effect of :meth:`excludes`, so a pass can report how many of the ids it was handed actually
    fired. On a read plan matching the header that number must be **exactly** the size of the list:
    exclusions are applied ahead of stage 2, so every id in the list is a document the reader still
    emits. A shortfall means the two passes did not read the same corpus.

    That post-condition catches the *limit* mistake from the other side; it cannot catch the
    *sample-rate* mistake, where the list is a subset and every id fires. Only the header catches
    that one, which is why both exist.
    """

    def __init__(
        self,
        ids: Iterable[str] = (),
        headers: Iterable[ExclusionHeader] = (),
        *,
        headerless: Iterable[str] = (),
    ) -> None:
        self._ids = frozenset(ids)
        self.headers = tuple(headers)
        self.headerless = tuple(headerless)
        self.hits = 0

    # --- loading -----------------------------------------------------------

    @classmethod
    def load(cls, paths: Sequence[str | Path]) -> ExclusionSet:
        """Union of several removal lists. Stage 7's and stage 8's are both passed to stage 10."""
        ids: set[str] = set()
        headers: list[ExclusionHeader] = []
        headerless: list[str] = []
        for path in paths:
            found, header = read_exclusions(path)
            ids.update(found)
            if header is None:
                headerless.append(str(path))
            else:
                headers.append(header)
        return cls(ids, headers, headerless=headerless)

    # --- checking ----------------------------------------------------------

    def check(self, readers: Iterable) -> Coverage:
        """Match this set's headers against the readers of the pass about to use it.

        Raises when a source is covered by a header whose read plan differs from the one about to
        be read: that is the case where applying the list silently removes the wrong documents, and
        there is no downstream symptom. Returns the coverage otherwise — including the sources with
        no exclusions at all, which are reported rather than refused, because a source legitimately
        has none until its own stage 6/7 pass has run.
        """
        by_source: dict[str, ReadPlan] = {}
        for header in self.headers:
            for plan in header.plans:
                by_source[plan.source] = plan

        covered: list[str] = []
        uncovered: list[str] = []
        for reader in readers:
            mine = ReadPlan.of(reader)
            theirs = by_source.get(mine.source)
            if theirs is None:
                uncovered.append(mine.source)
                continue
            if (
                theirs.plan_fingerprint != mine.plan_fingerprint
                or bool(theirs.limit) != bool(mine.limit)
                or (theirs.limit or 0) != (mine.limit or 0)
            ):
                raise ValueError(
                    f"exclusions for {mine.source!r} were computed over a different read: "
                    f"{theirs.describe()} against this pass's {mine.describe()}. Applying them "
                    "would remove a different set of documents than the stage that chose them "
                    "meant, and nothing downstream could tell — re-run that stage over this read, "
                    "or run this pass over that one"
                )
            covered.append(mine.source)

        return Coverage(
            covered=tuple(sorted(covered)),
            uncovered=tuple(sorted(uncovered)),
            headerless=self.headerless,
            stages=tuple(sorted({h.stage for h in self.headers})),
        )

    # --- runtime -----------------------------------------------------------

    def excludes(self, doc_id: str) -> bool:
        """Whether this document was removed earlier. Counts the hit."""
        if doc_id in self._ids:
            self.hits += 1
            return True
        return False

    def __contains__(self, doc_id: object) -> bool:
        return doc_id in self._ids

    def __len__(self) -> int:
        return len(self._ids)

    def __bool__(self) -> bool:
        return bool(self._ids)

    @property
    def unapplied(self) -> int:
        """Ids handed in that this pass never met. Must be 0 on a matching, unlimited read."""
        return len(self._ids) - self.hits

    def summary(self) -> Iterator[str]:
        """What actually fired, for the end of a pass. Empty when no list was given."""
        if not self._ids:
            return
        yield f"exclusions: applied {self.hits:,} of {len(self._ids):,} removed ids"
        if self.unapplied:
            yield (
                f"  !! {self.unapplied:,} were never met. On a read matching the header every id "
                "is a document this pass still emits, so a shortfall means the two passes did not "
                "read the same corpus — expected only under --limit"
            )

    def to_dict(self) -> dict:
        return {
            "version": EXCLUSIONS_VERSION,
            "ids": len(self._ids),
            "applied": self.hits,
            "unapplied": self.unapplied,
            "headers": [header.to_dict() for header in self.headers],
            "headerless": list(self.headerless),
        }


# --- file format -----------------------------------------------------------


def write_exclusions(
    path: str | Path,
    ids: Iterable[str],
    *,
    stage: str,
    readers: Iterable = (),
    plans: Iterable[ReadPlan] = (),
) -> int:
    """Write a removal list with the read plan it was computed over. Returns the count.

    ``newline="\\n"`` for session 4's reason: ``Path.write_text`` translates to ``os.linesep`` on
    Windows, and a list that hashed differently per platform would be one more way for two passes to
    disagree about the corpus.
    """
    ordered = list(ids)
    recorded = tuple(plans) or tuple(ReadPlan.of(reader) for reader in readers)
    header = ExclusionHeader(stage=stage, plans=recorded, count=len(ordered))
    body = "".join(f"{doc_id}\n" for doc_id in ordered)
    text = _HEADER_PREFIX + json.dumps(header.to_dict(), sort_keys=True) + "\n" + body
    Path(path).write_text(text, encoding="utf-8", newline="\n")
    return len(ordered)


def read_exclusions(path: str | Path) -> tuple[frozenset[str], ExclusionHeader | None]:
    """``(ids, header)``. ``header`` is ``None`` for a list written before headers existed."""
    header: ExclusionHeader | None = None
    ids: set[str] = set()
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(_HEADER_PREFIX):
                header = ExclusionHeader.from_dict(json.loads(line[len(_HEADER_PREFIX) :]))
                continue
            if line.startswith("#"):
                continue
            ids.add(line)
    if header is not None and header.count and header.count != len(ids):
        raise ValueError(
            f"{path}: header says {header.count:,} ids, file holds {len(ids):,} — the list was "
            "truncated or edited, and a partial removal list produces a corpus rather than an error"
        )
    return frozenset(ids), header
