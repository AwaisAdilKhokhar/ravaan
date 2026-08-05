"""Engineering invariants for the exclusion lists that carry the freeze order (PRD §6.3, §8.1).

The stage this covers has one job — hand a set of document ids from one corpus pass to the next —
and exactly one interesting failure: applying a list computed over a *different* corpus. Every way
of doing that produces a corpus rather than an error, so the tests here are mostly about what makes
the pass refuse.

Two of them are the whole reason the header exists:

* `test_check_refuses_a_list_computed_under_a_different_limit` — the read plan fingerprint cannot
  see `--limit`, by design, because a limit does not change which documents come in what order.
  A removal list from a 20,000-document smoke test is therefore *fingerprint-identical* to one over
  the corpus, and applying it removes a rounding error's worth of duplicates.
* `test_a_source_with_no_list_is_named_rather_than_assumed_clean` — the freeze order is
  6 → 7 → 9 → 8 → 10, and a source that has been through none of it looks exactly like a source
  with nothing to remove.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from ravaan.data.exclusions import (
    EXCLUSIONS_VERSION,
    ExclusionSet,
    ReadPlan,
    read_exclusions,
    write_exclusions,
)
from ravaan.data.shards import ShardFile, ShardReader, SourceLayout

SIMPLE = SourceLayout(text_column="text", id_column="id")


def make_shard(tmp_path: Path, count: int = 50, source: str = "alpha") -> ShardFile:
    path = tmp_path / f"{source}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["text", "id"])
        writer.writeheader()
        writer.writerows({"text": f"document {i}", "id": f"d{i}"} for i in range(count))
    return ShardFile(
        source=source, path=path.name, local_path=path, sha256=f"{source:0>64}", split="train"
    )


def reader(shard: ShardFile, **kwargs) -> ShardReader:
    return ShardReader([shard], layout=SIMPLE, **kwargs)


# --- the file format --------------------------------------------------------


def test_round_trip_carries_ids_and_the_read_plan(tmp_path: Path) -> None:
    shard = make_shard(tmp_path)
    path = tmp_path / "removals.txt"

    write_exclusions(path, ["alpha:d1", "alpha:d7"], stage="6+7", readers=[reader(shard)])
    ids, header = read_exclusions(path)

    assert ids == {"alpha:d1", "alpha:d7"}
    assert header is not None
    assert header.stage == "6+7"
    assert header.count == 2
    assert header.version == EXCLUSIONS_VERSION
    assert [plan.source for plan in header.plans] == ["alpha"]


def test_the_file_is_still_a_plain_list_of_ids(tmp_path: Path) -> None:
    """A human reads these by hand and `grep -v '^#'` must still be the whole format."""
    shard = make_shard(tmp_path)
    path = tmp_path / "removals.txt"
    write_exclusions(path, ["alpha:d1", "alpha:d2"], stage="7", readers=[reader(shard)])

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("#")
    assert [line for line in lines if not line.startswith("#")] == ["alpha:d1", "alpha:d2"]


def test_no_carriage_returns_reach_disk(tmp_path: Path) -> None:
    """Session 4's bug. Four platform defaults have cost this repo now — see ravaan/console.py."""
    shard = make_shard(tmp_path)
    path = tmp_path / "removals.txt"
    write_exclusions(path, ["alpha:d1"], stage="7", readers=[reader(shard)])
    assert b"\r" not in path.read_bytes()


def test_a_headerless_list_still_loads_and_says_so(tmp_path: Path) -> None:
    """`reports/dedup_removals_wikipedia.txt` predates headers. Refusing it would be gratuitous."""
    path = tmp_path / "old.txt"
    path.write_text("alpha:d1\nalpha:d2\n", encoding="utf-8", newline="\n")

    ids, header = read_exclusions(path)
    assert ids == {"alpha:d1", "alpha:d2"}
    assert header is None

    exclusions = ExclusionSet.load([path])
    coverage = exclusions.check([reader(make_shard(tmp_path))])
    assert coverage.headerless == (str(path),)
    assert any("carries no header" in line for line in coverage.report())


def test_comments_and_blank_lines_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "removals.txt"
    path.write_text("# a note\n\nalpha:d1\n\n# another\nalpha:d2\n", encoding="utf-8", newline="\n")
    ids, header = read_exclusions(path)
    assert ids == {"alpha:d1", "alpha:d2"}
    assert header is None


def test_a_truncated_list_raises_rather_than_removing_less(tmp_path: Path) -> None:
    """A partial removal list produces a corpus, not an error — unless the count is checked."""
    shard = make_shard(tmp_path)
    path = tmp_path / "removals.txt"
    write_exclusions(path, [f"alpha:d{i}" for i in range(10)], stage="7", readers=[reader(shard)])

    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:-3]) + "\n", encoding="utf-8", newline="\n")

    with pytest.raises(ValueError, match="header says 10 ids, file holds 7"):
        read_exclusions(path)


def test_several_lists_union(tmp_path: Path) -> None:
    """Stage 10 is handed stages 6+7's list and stage 8's, and must honour both."""
    shard = make_shard(tmp_path)
    near = tmp_path / "near.txt"
    decon = tmp_path / "decon.txt"
    write_exclusions(near, ["alpha:d1", "alpha:d2"], stage="6+7", readers=[reader(shard)])
    write_exclusions(decon, ["alpha:d2", "alpha:d9"], stage="8", readers=[reader(shard)])

    exclusions = ExclusionSet.load([near, decon])
    assert len(exclusions) == 3
    assert {h.stage for h in exclusions.headers} == {"6+7", "8"}


# --- what makes a pass refuse ----------------------------------------------


def test_check_accepts_the_read_it_was_computed_over(tmp_path: Path) -> None:
    shard = make_shard(tmp_path)
    path = tmp_path / "removals.txt"
    write_exclusions(path, ["alpha:d1"], stage="7", readers=[reader(shard)])

    coverage = ExclusionSet.load([path]).check([reader(shard)])
    assert coverage.covered == ("alpha",)
    assert coverage.uncovered == ()
    assert not coverage.empty


def test_check_refuses_a_list_computed_under_a_different_limit(tmp_path: Path) -> None:
    """The load-bearing test. `plan_fingerprint` deliberately does not cover `--limit`.

    So a list from `--limit 20000` and a list over the corpus are fingerprint-identical, every id
    in the smaller one matches, and nothing downstream is out of place. Only the recorded limit
    separates them.
    """
    shard = make_shard(tmp_path)
    path = tmp_path / "removals.txt"
    write_exclusions(path, ["alpha:d1"], stage="7", readers=[reader(shard, limit=20)])

    assert reader(shard, limit=20).plan_fingerprint() == reader(shard).plan_fingerprint()

    with pytest.raises(ValueError, match="computed over a different read"):
        ExclusionSet.load([path]).check([reader(shard)])


def test_check_refuses_a_list_computed_at_a_different_sample_rate(tmp_path: Path) -> None:
    """A list from a 5% pass removes a twentieth of what it should, and every id in it matches."""
    shard = make_shard(tmp_path)
    path = tmp_path / "removals.txt"
    write_exclusions(path, ["alpha:d1"], stage="7", readers=[reader(shard, sample_rate=0.05)])

    with pytest.raises(ValueError, match="computed over a different read"):
        ExclusionSet.load([path]).check([reader(shard)])


def test_check_refuses_a_list_computed_over_different_files(tmp_path: Path) -> None:
    shard = make_shard(tmp_path)
    other = make_shard(tmp_path, source="alpha", count=60)
    other = ShardFile(
        source="alpha", path=other.path, local_path=other.local_path, sha256="f" * 64, split="train"
    )
    path = tmp_path / "removals.txt"
    write_exclusions(path, ["alpha:d1"], stage="7", readers=[reader(other)])

    with pytest.raises(ValueError, match="computed over a different read"):
        ExclusionSet.load([path]).check([reader(shard)])


def test_a_source_with_no_list_is_named_rather_than_assumed_clean(tmp_path: Path) -> None:
    """The freeze-order failure: a source that went through no stage 6/7 looks exactly like a
    source with nothing to remove. It is reported, not refused — a source legitimately has no list
    until its own pass has run."""
    alpha = make_shard(tmp_path, source="alpha")
    beta = make_shard(tmp_path, source="beta")
    path = tmp_path / "removals.txt"
    write_exclusions(path, ["alpha:d1"], stage="7", readers=[reader(alpha)])

    coverage = ExclusionSet.load([path]).check([reader(alpha), reader(beta)])
    assert coverage.covered == ("alpha",)
    assert coverage.uncovered == ("beta",)
    assert any("beta" in line and "NO exclusions" in line for line in coverage.report())


def test_no_list_at_all_reports_one_line_not_one_per_source(tmp_path: Path) -> None:
    """A measurement pass runs without exclusions legitimately and must not drown in warnings."""
    alpha = make_shard(tmp_path, source="alpha")
    beta = make_shard(tmp_path, source="beta")

    coverage = ExclusionSet.load([]).check([reader(alpha), reader(beta)])
    assert coverage.empty
    assert len(list(coverage.report())) == 1
    assert "no --exclude given" in next(iter(coverage.report()))


def test_a_reader_spanning_two_sources_is_refused(tmp_path: Path) -> None:
    """An exclusion list is recorded per source; a reader over two of them has no single plan."""
    alpha = make_shard(tmp_path, source="alpha")
    beta = make_shard(tmp_path, source="beta")
    with pytest.raises(ValueError, match="recorded per source"):
        ReadPlan.of(ShardReader([alpha, beta], layout=SIMPLE))


# --- runtime ---------------------------------------------------------------


def test_hits_are_counted_and_the_shortfall_is_visible() -> None:
    """On a matching, unlimited read every id must fire: exclusions are applied ahead of stage 2,
    so every one of them is a document the reader still emits. A shortfall means the two passes
    read different corpora."""
    exclusions = ExclusionSet(["a", "b", "c"])

    assert exclusions.excludes("a")
    assert not exclusions.excludes("z")
    assert exclusions.hits == 1
    assert exclusions.unapplied == 2
    assert any("never met" in line for line in exclusions.summary())

    exclusions.excludes("b")
    exclusions.excludes("c")
    assert exclusions.unapplied == 0
    assert not any("never met" in line for line in exclusions.summary())


def test_an_empty_set_is_falsy_and_silent() -> None:
    exclusions = ExclusionSet()
    assert not exclusions
    assert list(exclusions.summary()) == []
    assert not exclusions.excludes("anything")


def test_to_dict_reports_what_the_manifest_needs() -> None:
    exclusions = ExclusionSet(["a", "b"])
    exclusions.excludes("a")
    payload = exclusions.to_dict()
    assert payload["ids"] == 2
    assert payload["applied"] == 1
    assert payload["unapplied"] == 1
