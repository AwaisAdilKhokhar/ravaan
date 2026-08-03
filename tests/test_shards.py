"""Engineering invariants for the shard reader (PRD §8.1 — CI, never a results table).

The properties under test are the ones a corpus is *ruined* by silently: a sample that is really
a prefix, a document id that changes when the read order does, and a checkpoint that resumes into
a different order than it was written for.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from ravaan.data.shards import (
    LAYOUTS,
    ShardFile,
    ShardReader,
    SourceLayout,
    load_manifest_files,
    stable_unit,
)

SIMPLE = SourceLayout(text_column="text", id_column="id", meta_columns=("url",))


def write_csv(path: Path, rows: list[dict], header: list[str] | None = None) -> ShardFile:
    header = header or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    return ShardFile(
        source="test", path=path.name, local_path=path, sha256="0" * 64, split="train"
    )


def make_shard(tmp_path: Path, count: int = 100, name: str = "shard.csv") -> ShardFile:
    rows = [
        {"text": f"document number {i}", "id": f"d{i}", "url": f"https://site{i % 7}.example/{i}"}
        for i in range(count)
    ]
    return write_csv(tmp_path / name, rows)


# --- Stable selection -------------------------------------------------------
# The reason `sample_rate` hashes instead of shuffling. Stage 9's splits and arm A's 25M
# subsample will use the same primitive, and PRD §6.1 requires the two arms to differ in size
# and nothing else — which is only true if membership does not move when the reader does.


def test_stable_unit_is_deterministic_and_salted() -> None:
    assert stable_unit("doc-1") == stable_unit("doc-1")
    assert stable_unit("doc-1") != stable_unit("doc-2")
    assert stable_unit("doc-1", "splits") != stable_unit("doc-1", "subsample")
    assert 0.0 <= stable_unit("doc-1") < 1.0


def test_stable_unit_pins_its_exact_values() -> None:
    """A regression guard against reaching for the builtin `hash`, or changing the digest.

    PYTHONHASHSEED salts `hash` per process, so a corpus split built on it would reassign every
    document on every run. Pinning literal values means any change to the mapping — a different
    algorithm, a different digest size, a different salt separator — has to be a deliberate act
    that also bumps SHARDS_VERSION, not an accident that silently repartitions a frozen corpus.
    """
    assert stable_unit("ravaan") == 0.05111436731995191
    assert stable_unit("ravaan", "splits") == 0.011765447676121275


def test_sample_membership_is_identical_across_read_seeds(tmp_path: Path) -> None:
    shard = make_shard(tmp_path, 500)

    def ids(seed: int) -> set[str]:
        return {d.doc_id for d in ShardReader([shard], layout=SIMPLE, seed=seed, sample_rate=0.2)}

    assert ids(0) == ids(1) == ids(99)
    assert 60 < len(ids(0)) < 140  # ~0.2 of 500, loosely


def test_document_ids_do_not_move_when_the_shuffle_does(tmp_path: Path) -> None:
    """Positional ids must name the row in the *file*, not the row in the permutation."""
    rows = [{"text": f"line {i}", "url": ""} for i in range(50)]
    shard = write_csv(tmp_path / "noid.csv", rows, header=["text", "url"])
    layout = SourceLayout(text_column="text")

    def mapping(seed: int) -> dict[str, str]:
        return {d.doc_id: d.text for d in ShardReader([shard], layout=layout, seed=seed)}

    assert mapping(0) == mapping(5)


# --- A prefix is not a sample (Finding E) -----------------------------------


def test_shuffled_is_the_default_and_sequential_must_be_asked_for(tmp_path: Path) -> None:
    shard = make_shard(tmp_path, 200)
    default = [d.text for d in ShardReader([shard], layout=SIMPLE, limit=20)]
    sequential = [
        d.text for d in ShardReader([shard], layout=SIMPLE, limit=20, order="sequential")
    ]
    assert sequential == [f"document number {i}" for i in range(20)]
    assert default != sequential


def test_shuffled_order_is_reproducible_for_a_given_seed(tmp_path: Path) -> None:
    shard = make_shard(tmp_path, 200)
    first = [d.doc_id for d in ShardReader([shard], layout=SIMPLE, seed=3, limit=30)]
    again = [d.doc_id for d in ShardReader([shard], layout=SIMPLE, seed=3, limit=30)]
    other = [d.doc_id for d in ShardReader([shard], layout=SIMPLE, seed=4, limit=30)]
    assert first == again
    assert first != other


def test_every_document_is_yielded_exactly_once(tmp_path: Path) -> None:
    shard = make_shard(tmp_path, 250)
    ids = [d.doc_id for d in ShardReader([shard], layout=SIMPLE)]
    assert len(ids) == 250
    assert len(set(ids)) == 250


def test_invalid_order_is_rejected(tmp_path: Path) -> None:
    shard = make_shard(tmp_path, 10)
    with pytest.raises(ValueError, match="order must be"):
        ShardReader([shard], layout=SIMPLE, order="random")  # type: ignore[arg-type]


# --- Resumption is exact or it fails ---------------------------------------


def test_resume_continues_exactly_where_it_stopped(tmp_path: Path) -> None:
    shard = make_shard(tmp_path, 400)
    whole = [d.doc_id for d in ShardReader([shard], layout=SIMPLE)]

    first = ShardReader([shard], layout=SIMPLE, limit=137)
    part = [d.doc_id for d in first]
    checkpoint = tmp_path / "ckpt.json"
    first.save_checkpoint(checkpoint)

    rest = ShardReader([shard], layout=SIMPLE).resume(checkpoint)
    part += [d.doc_id for d in rest]

    assert part == whole


def test_resume_refuses_a_checkpoint_from_a_different_plan(tmp_path: Path) -> None:
    shard = make_shard(tmp_path, 100)
    reader = ShardReader([shard], layout=SIMPLE, seed=0, limit=10)
    list(reader)
    checkpoint = tmp_path / "ckpt.json"
    reader.save_checkpoint(checkpoint)

    with pytest.raises(ValueError, match="refusing to resume"):
        ShardReader([shard], layout=SIMPLE, seed=1).resume(checkpoint)


def test_plan_fingerprint_tracks_digest_not_path(tmp_path: Path) -> None:
    shard = make_shard(tmp_path, 10)
    moved = ShardFile(
        source=shard.source,
        path=shard.path,
        local_path=tmp_path / "elsewhere.csv",
        sha256=shard.sha256,
    )
    replaced = ShardFile(
        source=shard.source, path=shard.path, local_path=shard.local_path, sha256="1" * 64
    )
    base = ShardReader([shard], layout=SIMPLE).plan_fingerprint()
    assert ShardReader([moved], layout=SIMPLE).plan_fingerprint() == base
    assert ShardReader([replaced], layout=SIMPLE).plan_fingerprint() != base


# --- CSV block index --------------------------------------------------------


def test_csv_index_survives_embedded_newlines_and_commas(tmp_path: Path) -> None:
    rows = [
        {"text": 'a "quoted" field, with a comma', "id": "a"},
        {"text": "a field\nspanning\nthree lines", "id": "b"},
        {"text": "plain", "id": "c"},
    ]
    shard = write_csv(tmp_path / "tricky.csv", rows, header=["text", "id"])
    layout = SourceLayout(text_column="text", id_column="id")
    got = {d.doc_id: d.text for d in ShardReader([shard], layout=layout)}
    assert got["test:b"] == "a field\nspanning\nthree lines"
    assert got["test:a"].endswith("with a comma")


def test_csv_index_cache_is_keyed_on_the_digest(tmp_path: Path) -> None:
    shard = make_shard(tmp_path, 40)
    list(ShardReader([shard], layout=SIMPLE))
    cache = tmp_path / "shard.csv.blocks.json"
    assert cache.exists()
    payload = json.loads(cache.read_text(encoding="utf-8"))
    assert payload["sha256"] == shard.sha256
    assert payload["rows"] == 40

    # A cache written for other bytes must not be trusted: stale offsets land mid-record.
    stale = ShardFile(
        source=shard.source, path=shard.path, local_path=shard.local_path, sha256="9" * 64
    )
    assert len(list(ShardReader([stale], layout=SIMPLE))) == 40


# --- Layouts ---------------------------------------------------------------


def test_layouts_are_declared_not_guessed(tmp_path: Path) -> None:
    shard = ShardFile(
        source="mystery-source", path="x.csv", local_path=tmp_path / "x.csv", sha256="0" * 64
    )
    with pytest.raises(KeyError, match="no layout declared"):
        ShardReader([shard])


def test_declared_layouts_match_the_manifest_sources() -> None:
    # If a source is acquired but has no layout, stage 3 cannot read it; catching that here is
    # cheaper than catching it in the middle of a 3.5G-character pass.
    manifest = Path("data/manifest.json")
    if not manifest.exists():  # pragma: no cover - corpus is not committed
        pytest.skip("no local corpus manifest")
    sources = {f.source for f in load_manifest_files(manifest)}
    assert sources <= set(LAYOUTS), f"sources without a layout: {sorted(sources - set(LAYOUTS))}"


def test_missing_text_column_is_an_error_not_a_guess(tmp_path: Path) -> None:
    rows = [{"body": "some text", "id": "a"}]
    shard = write_csv(tmp_path / "other.csv", rows, header=["body", "id"])
    with pytest.raises(KeyError, match="has no column 'text'"):
        list(ShardReader([shard], layout=SIMPLE))


def test_manifest_paths_are_read_platform_independently(tmp_path: Path) -> None:
    manifest = tmp_path / "data" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "source": "s",
                        "path": "a.csv",
                        "local_path": "data\\raw\\s\\a.csv",  # written on Windows
                        "sha256": "0" * 64,
                        "split": "train",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (file,) = load_manifest_files(manifest)
    assert file.local_path.parts[-3:] == ("raw", "s", "a.csv")


# --- Empty documents --------------------------------------------------------


def test_empty_documents_are_skipped_but_still_counted(tmp_path: Path) -> None:
    rows = [{"text": t, "id": str(i)} for i, t in enumerate(["a real document", "", "   ", "x y"])]
    shard = write_csv(tmp_path / "sparse.csv", rows, header=["text", "id"])
    layout = SourceLayout(text_column="text", id_column="id")
    reader = ShardReader([shard], layout=layout, order="sequential")
    documents = list(reader)
    assert [d.text for d in documents] == ["a real document", "x y"]
    assert reader.position.selected == 4  # all four rows were visited
    assert reader.position.emitted == 2
