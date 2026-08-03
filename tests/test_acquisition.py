"""Engineering invariants for corpus acquisition (PRD §8.1 — CI, never a results table).

No test here touches the network. The point of stage 1 is that the *manifest* is the corpus's
reproducibility story, so these tests check the manifest, the licence gate and the verification
logic — all of which are exactly as load-bearing offline as online.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ravaan.data.acquisition import (
    LICENSES,
    MANIFEST_SCHEMA_VERSION,
    LicenseError,
    ManifestError,
    SourceFile,
    SourceManifest,
    SourceSpec,
    fetch_file,
    local_path,
    plan_fetch,
    resolve_url,
    sha256_file,
    verify_file,
    write_acquisition_manifest,
)

SOURCES_JSON = Path(__file__).resolve().parents[1] / "configs" / "data" / "sources.json"

PAYLOAD = "سلام دنیا\n".encode()
PAYLOAD_SHA = hashlib.sha256(PAYLOAD).hexdigest()


def _file(**kwargs) -> SourceFile:
    defaults = {"path": "a.parquet", "sha256": PAYLOAD_SHA, "size": len(PAYLOAD)}
    return SourceFile(**{**defaults, **kwargs})


def _spec(**kwargs) -> SourceSpec:
    return SourceSpec(
        **{
            "name": "fixture",
            "role": "test fixture",
            "repo_id": "org/repo",
            "revision": "a" * 40,
            "license": "Apache-2.0",
            "files": (_file(),),
            **kwargs,
        }
    )


# --- The shipped manifest ---------------------------------------------------


@pytest.fixture(scope="module")
def shipped() -> SourceManifest:
    return SourceManifest.from_json_file(SOURCES_JSON)


def test_shipped_sources_load_and_validate(shipped: SourceManifest) -> None:
    assert shipped.schema_version == MANIFEST_SCHEMA_VERSION
    assert shipped.sources


def test_shipped_manifest_has_exactly_the_three_prd_sources(shipped: SourceManifest) -> None:
    # PRD §6.2 lists three and says the other six were dropped. Adding a fourth silently would
    # change the corpus mix and confound arm A against arm B.
    assert {s.name for s in shipped.sources} == {
        "fineweb2-urd_Arab",
        "roman-urdu-parl",
        "urdu-wikipedia",
    }


def test_every_revision_is_pinned_to_a_commit_sha(shipped: SourceManifest) -> None:
    for spec in shipped.sources:
        assert len(spec.revision) == 40
        assert spec.revision not in ("main", "master", "refs/heads/main")


def test_every_file_carries_a_sha256_and_a_size(shipped: SourceManifest) -> None:
    for spec in shipped.sources:
        for f in spec.files:
            assert len(f.sha256) == 64
            assert f.size > 0


def test_every_shipped_licence_permits_a_permissive_checkpoint(shipped: SourceManifest) -> None:
    # PRD §6.3 promises one permissively licensed checkpoint. That promise is only as good as
    # the most restrictive source in the corpus.
    for spec in shipped.sources:
        assert spec.terms.permits_training, spec.name


def test_share_alike_sources_are_flagged_and_attributed(shipped: SourceManifest) -> None:
    names = {s.name for s in shipped.share_alike_sources()}
    assert "urdu-wikipedia" in names  # CC BY-SA
    lines = shipped.attribution_lines()
    assert len(lines) == len(shipped.sources)  # all three require attribution
    assert any("Wikipedia" in line for line in lines)


def test_rejected_sources_are_recorded_with_reasons(shipped: SourceManifest) -> None:
    # PRD §6.1 requires the report to say the corpus cap is a deliberate decision. That is only
    # checkable if what we chose not to use, and why, is on the record.
    assert shipped.rejected
    for r in shipped.rejected:
        assert r.reason.strip()
    assert any("UrduLM" in r.name or "ALIF" in r.name for r in shipped.rejected)


def test_fetch_order_puts_the_cheapest_sufficient_files_first(shipped: SourceManifest) -> None:
    fineweb = shipped["fineweb2-urd_Arab"]
    first = fineweb.ordered_files()[0]
    assert first.size == min(f.size for f in fineweb.files if f.split == "train")

    parl = shipped["roman-urdu-parl"]
    assert parl.ordered_files()[0].split == "test"  # the §8.2 eval split, without the 1.19 GB train


# --- The licence gate -------------------------------------------------------


def test_an_unknown_licence_is_a_hard_error_not_a_default() -> None:
    with pytest.raises(LicenseError, match="not in the gate"):
        _spec(license="WTFPL-ish")


@pytest.mark.parametrize("spdx", ["CC-BY-NC-ND-4.0", "CC-BY-NC-4.0"])
def test_a_non_commercial_source_cannot_enter_the_corpus(spdx: str) -> None:
    # The gate has to be able to name what it refuses, so these licences are defined — but a
    # source under one of them may only appear under `rejected`.
    with pytest.raises(LicenseError, match="does not permit"):
        SourceManifest(sources=(_spec(license=spdx),))


def test_every_defined_licence_states_all_four_terms() -> None:
    for spdx, terms in LICENSES.items():
        assert terms.spdx == spdx
        assert terms.url.startswith("https://")
        assert isinstance(terms.share_alike, bool)


# --- Manifest validation ----------------------------------------------------


@pytest.mark.parametrize("revision", ["main", "master", "a" * 39, "A" * 40, "", "v1.0"])
def test_an_unpinned_revision_is_rejected(revision: str) -> None:
    with pytest.raises(ManifestError, match="pinned 40-hex"):
        _spec(revision=revision)


@pytest.mark.parametrize("sha", ["", "abc", "z" * 64, PAYLOAD_SHA.upper()])
def test_a_malformed_digest_is_rejected(sha: str) -> None:
    with pytest.raises(ManifestError, match="sha256 must be"):
        _file(sha256=sha)


def test_a_non_positive_size_is_rejected() -> None:
    with pytest.raises(ManifestError, match="size must be positive"):
        _file(size=0)


def test_duplicate_file_paths_are_rejected() -> None:
    with pytest.raises(ManifestError, match="duplicate file"):
        _spec(files=(_file(), _file()))


def test_a_source_with_no_files_is_rejected() -> None:
    with pytest.raises(ManifestError, match="no files"):
        _spec(files=())


def test_duplicate_source_names_are_rejected() -> None:
    with pytest.raises(ManifestError, match="duplicate source name"):
        SourceManifest(sources=(_spec(), _spec()))


def test_unknown_source_keys_are_rejected() -> None:
    with pytest.raises(ManifestError, match="unknown source keys"):
        SourceSpec.from_dict(
            {
                "name": "x",
                "role": "r",
                "repo_id": "org/repo",
                "revision": "a" * 40,
                "license": "Apache-2.0",
                "files": [_file().to_dict()],
                "licence": "Apache-2.0",  # British spelling: a typo, not a field
            }
        )


# --- Round trip and fingerprint --------------------------------------------


def test_manifest_round_trips_through_json(tmp_path: Path, shipped: SourceManifest) -> None:
    path = tmp_path / "sources.json"
    shipped.to_json_file(path)
    assert SourceManifest.from_json_file(path) == shipped


def test_fingerprint_is_stable_and_tracks_the_sources(shipped: SourceManifest) -> None:
    assert shipped.fingerprint() == SourceManifest.from_json_file(SOURCES_JSON).fingerprint()
    assert len(shipped.fingerprint()) == 12

    moved = SourceManifest(sources=(_spec(),))
    assert moved.fingerprint() != shipped.fingerprint()


def test_fingerprint_ignores_prose_and_fetch_order() -> None:
    # Reordering a download or fixing a typo in a note must not invalidate a frozen corpus.
    base = SourceManifest(sources=(_spec(files=(_file(path="a"), _file(path="b", order=1))),))
    reordered = SourceManifest(
        sources=(
            _spec(
                notes="rewritten note",
                role="clearer role",
                citation="added later",
                files=(_file(path="a", order=9, note="hint"), _file(path="b")),
            ),
        )
    )
    assert base.fingerprint() == reordered.fingerprint()


@pytest.mark.parametrize(
    "change",
    [
        {"revision": "b" * 40},
        {"repo_id": "org/other"},
        {"license": "CC-BY-4.0"},
        {"name": "renamed"},
        {"config": "urd_Arab_v2"},
        {"files": (_file(sha256="0" * 64),)},
        {"files": (_file(path="different.parquet"),)},
        {"files": (_file(), _file(path="extra.parquet"))},
    ],
)
def test_fingerprint_changes_when_the_corpus_does(change: dict) -> None:
    assert (
        SourceManifest(sources=(_spec(**change),)).fingerprint()
        != SourceManifest(sources=(_spec(),)).fingerprint()
    )


def test_fingerprint_ignores_rejected_sources() -> None:
    # Noting why we skipped a source does not change the corpus, and must not invalidate a
    # frozen one.
    from ravaan.data.acquisition import RejectedSource

    bare = SourceManifest(sources=(_spec(),))
    annotated = SourceManifest(
        sources=(_spec(),),
        rejected=(RejectedSource(name="something", reason="not needed"),),
    )
    assert bare.fingerprint() == annotated.fingerprint()


# --- URLs -------------------------------------------------------------------


def test_download_url_uses_the_pinned_revision_never_a_branch(shipped: SourceManifest) -> None:
    spec = shipped["urdu-wikipedia"]
    url = resolve_url(spec, spec.files[0])
    assert url == (
        "https://huggingface.co/datasets/wikimedia/wikipedia/resolve/"
        f"{spec.revision}/{spec.files[0].path}"
    )
    assert "/main/" not in url


def test_model_repos_get_the_bare_url_form() -> None:
    spec = _spec(repo_type="model", repo_id="org/model")
    assert resolve_url(spec, spec.files[0]) == (
        f"https://huggingface.co/org/model/resolve/{'a' * 40}/a.parquet"
    )


# --- Hashing and verification ----------------------------------------------


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    path = tmp_path / "blob.bin"
    path.write_bytes(PAYLOAD)
    assert sha256_file(path) == PAYLOAD_SHA


def test_sha256_file_is_chunk_size_independent(tmp_path: Path) -> None:
    path = tmp_path / "blob.bin"
    path.write_bytes(PAYLOAD * 1000)
    assert sha256_file(path, chunk=7) == sha256_file(path, chunk=1 << 20)


def test_verify_passes_on_the_expected_bytes(tmp_path: Path) -> None:
    path = tmp_path / "blob.bin"
    path.write_bytes(PAYLOAD)
    result = verify_file(path, _file())
    assert result.ok
    assert result.sha256 == PAYLOAD_SHA


def test_verify_reports_a_missing_file(tmp_path: Path) -> None:
    result = verify_file(tmp_path / "absent.bin", _file())
    assert not result.ok
    assert result.reason == "missing"


def test_verify_catches_a_truncated_download(tmp_path: Path) -> None:
    path = tmp_path / "blob.bin"
    path.write_bytes(PAYLOAD[:-1])
    result = verify_file(path, _file())
    assert not result.ok
    assert "size" in result.reason


def test_verify_catches_a_same_length_corruption(tmp_path: Path) -> None:
    # The case a size check alone would miss.
    path = tmp_path / "blob.bin"
    corrupt = bytearray(PAYLOAD)
    corrupt[0] ^= 0xFF
    path.write_bytes(bytes(corrupt))
    result = verify_file(path, _file())
    assert not result.ok
    assert result.reason == "sha256 mismatch"


# --- Fetch planning ---------------------------------------------------------


def test_plan_without_a_budget_takes_everything() -> None:
    spec = _spec(
        files=(
            _file(path="big.parquet", size=100, order=1),
            _file(path="small.parquet", size=10, order=0),
        )
    )
    assert [f.path for f in plan_fetch(spec)] == ["small.parquet", "big.parquet"]


def test_plan_stops_at_the_budget_and_never_splits_a_file() -> None:
    spec = _spec(
        files=(
            _file(path="small.parquet", size=10, order=0),
            _file(path="big.parquet", size=100, order=1),
        )
    )
    assert [f.path for f in plan_fetch(spec, max_bytes=50)] == ["small.parquet"]
    assert plan_fetch(spec, max_bytes=5) == ()
    assert len(plan_fetch(spec, max_bytes=110)) == 2


def test_ties_in_order_break_on_path_for_determinism() -> None:
    spec = _spec(
        files=(
            _file(path="b.parquet", size=1),
            _file(path="a.parquet", size=1),
        )
    )
    assert [f.path for f in spec.ordered_files()] == ["a.parquet", "b.parquet"]


# --- Fetch, offline ---------------------------------------------------------


def test_fetch_short_circuits_on_an_already_verified_file(tmp_path: Path) -> None:
    # No network: a file already on disk that matches the pinned digest is accepted as-is.
    spec, file = _spec(), _file()
    dest = local_path(spec, file, tmp_path)
    dest.parent.mkdir(parents=True)
    dest.write_bytes(PAYLOAD)

    record = fetch_file(spec, file, tmp_path)
    assert record.sha256 == PAYLOAD_SHA
    assert record.revision == spec.revision
    assert record.license == "Apache-2.0"
    assert Path(record.local_path) == dest


def test_fetch_refuses_to_reuse_a_file_that_does_not_verify(tmp_path: Path) -> None:
    spec, file = _spec(), _file()
    dest = local_path(spec, file, tmp_path)
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"wrong bytes entirely")

    with pytest.raises(ValueError, match="does not verify"):
        fetch_file(spec, file, tmp_path)


# --- The acquisition manifest ----------------------------------------------


def test_acquisition_manifest_records_what_was_actually_taken(tmp_path: Path) -> None:
    spec, file = _spec(), _file()
    dest = local_path(spec, file, tmp_path)
    dest.parent.mkdir(parents=True)
    dest.write_bytes(PAYLOAD)
    record = fetch_file(spec, file, tmp_path)

    manifest = SourceManifest(sources=(spec,))
    out = tmp_path / "manifest.json"
    payload = write_acquisition_manifest([record], manifest, out)

    assert payload["sources_fingerprint"] == manifest.fingerprint()
    assert payload["total_bytes"] == len(PAYLOAD)
    assert payload["files"][0]["sha256"] == PAYLOAD_SHA
    assert payload["files"][0]["url"].startswith("https://huggingface.co/datasets/")
    assert json.loads(out.read_text(encoding="utf-8")) == payload


def _acquire(tmp_path: Path, spec: SourceSpec, file: SourceFile, body: bytes):
    dest = local_path(spec, file, tmp_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return fetch_file(spec, file, tmp_path)


def test_a_second_fetch_adds_to_the_manifest_instead_of_replacing_it(tmp_path: Path) -> None:
    # A 6.9 GB source arrives over several sessions, often one --source at a time. A manifest
    # that described only the last invocation would understate the corpus, and stage 9 would
    # split over files the manifest does not list.
    spec = _spec(files=(_file(path="a.parquet"), _file(path="b.parquet")))
    out = tmp_path / "manifest.json"
    manifest = SourceManifest(sources=(spec,))

    first = _acquire(tmp_path, spec, spec.files[0], PAYLOAD)
    write_acquisition_manifest([first], manifest, out)
    second = _acquire(tmp_path, spec, spec.files[1], PAYLOAD)
    payload = write_acquisition_manifest([second], manifest, out)

    assert [row["path"] for row in payload["files"]] == ["a.parquet", "b.parquet"]
    assert payload["total_bytes"] == 2 * len(PAYLOAD)


def test_refetching_the_same_file_updates_its_entry_rather_than_duplicating(
    tmp_path: Path,
) -> None:
    spec, file = _spec(), _file()
    out = tmp_path / "manifest.json"
    manifest = SourceManifest(sources=(spec,))

    record = _acquire(tmp_path, spec, file, PAYLOAD)
    write_acquisition_manifest([record], manifest, out)
    payload = write_acquisition_manifest([record], manifest, out)

    assert len(payload["files"]) == 1
    assert payload["total_bytes"] == len(PAYLOAD)


def test_verify_flags_a_file_no_longer_declared_in_sources(tmp_path: Path, capsys) -> None:
    # Checking sources.json against disk cannot catch a file that was acquired earlier and has
    # since been dropped from sources.json: it still verifies against a digest nothing declares
    # any more, and a stage that globs data/raw would train on it.
    from ravaan.data.acquisition import main

    spec, file = _spec(), _file()
    dest = local_path(spec, file, tmp_path / "raw")
    dest.parent.mkdir(parents=True)
    dest.write_bytes(PAYLOAD)

    sources = tmp_path / "sources.json"
    SourceManifest(sources=(spec,)).to_json_file(sources)
    acquired = tmp_path / "manifest.json"
    write_acquisition_manifest([fetch_file(spec, file, tmp_path / "raw")], SourceManifest(
        sources=(spec,)
    ), acquired)

    # Now drop the source's file from sources.json, leaving the manifest entry orphaned.
    SourceManifest(sources=(_spec(files=(_file(path="other.parquet"),)),)).to_json_file(sources)

    exit_code = main(
        [
            "-s", str(sources),
            "--root", str(tmp_path / "raw"),
            "--manifest", str(acquired),
            "verify", "--skip-missing",
        ]
    )
    assert exit_code == 1
    assert "ORPHAN" in capsys.readouterr().out


def test_merge_can_be_switched_off(tmp_path: Path) -> None:
    spec = _spec(files=(_file(path="a.parquet"), _file(path="b.parquet")))
    out = tmp_path / "manifest.json"
    manifest = SourceManifest(sources=(spec,))

    write_acquisition_manifest([_acquire(tmp_path, spec, spec.files[0], PAYLOAD)], manifest, out)
    payload = write_acquisition_manifest(
        [_acquire(tmp_path, spec, spec.files[1], PAYLOAD)], manifest, out, merge=False
    )
    assert [row["path"] for row in payload["files"]] == ["b.parquet"]
