"""Corpus acquisition — stage 1 of the corpus pipeline (PRD §6.3.1).

The corpus itself is never redistributed (PRD §6.3 release policy: code, manifest, checksums and
statistics only). That makes this module the *entire* reproducibility story for the data: someone
who wants to rebuild Ravaan's corpus has `configs/data/sources.json` and nothing else. Three
properties follow from that, and the module is built around them.

1. **Revisions are pinned, and pinning is enforced.** FineWeb2 and Wikipedia both move. A source
   recorded as ``revision: "main"`` describes a different corpus every month, so
   :meth:`SourceManifest.validate` rejects anything that is not a 40-hex commit SHA. This is a
   hard error, not a warning — an unpinned source in the manifest is an irreproducible corpus,
   and the failure is silent unless something refuses to load it.

2. **Every file carries its SHA-256 up front, before it is downloaded.** Hugging Face stores
   large files in Git LFS, whose object id *is* the SHA-256 of the content, so the expected digest
   is published metadata rather than something we compute after trusting a download. Checksums
   recorded post-hoc only prove that the bytes did not change since we looked; these prove we got
   the bytes the pinned revision names. (If that assumption about the oid were wrong, every
   :func:`fetch_file` call would fail loudly on the first byte-mismatch rather than pass quietly.)

3. **The licence gate is executable.** PRD §6.3 promises one permissively licensed checkpoint.
   That promise is only as good as the most restrictive source in the corpus, and licence
   compatibility is exactly the kind of thing that gets checked once during planning and then
   drifts. :data:`LICENSES` encodes the terms; a source whose licence forbids derivative works
   or commercial use cannot enter ``sources`` at all — it can only be recorded under
   ``rejected``, with its reason, as provenance.

Rejected sources are kept in the manifest deliberately. PRD §6.1 requires the report to state
that the corpus cap is a *deliberate design decision* rather than a limitation; that claim is
only checkable if the things we chose not to use, and why, are on the record next to the things
we did.

Standard library only, like the rest of the corpus pipeline's load-bearing stages. `datasets` and
`huggingface_hub` are more convenient, but this is the code that decides which bytes the whole
project is built on, and it should be readable end to end without them. Reading parquet (stage 3
onward) is where `[data]` extras start.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

__all__ = [
    "ACQUISITION_VERSION",
    "MANIFEST_SCHEMA_VERSION",
    "LICENSES",
    "LicenseTerms",
    "SourceFile",
    "SourceSpec",
    "RejectedSource",
    "SourceManifest",
    "AcquisitionRecord",
    "resolve_url",
    "sha256_file",
    "verify_file",
    "fetch_file",
    "plan_fetch",
]

ACQUISITION_VERSION = "1.0.0"
MANIFEST_SCHEMA_VERSION = 1

_SHA1_RE = re.compile(r"\A[0-9a-f]{40}\Z")
_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")

HF_ENDPOINT = "https://huggingface.co"
_USER_AGENT = f"ravaan-acquisition/{ACQUISITION_VERSION}"
_CHUNK = 1 << 20  # 1 MiB


# ---------------------------------------------------------------------------
# Licences
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LicenseTerms:
    """The four properties that decide whether a source can be trained on and shipped.

    ``share_alike`` does not block a source. Whether model weights are a derivative work of the
    training text is unsettled, and the project's position is stated rather than assumed: no raw
    text is redistributed, and every share-alike source is attributed in the manifest and the
    technical report. Flagging it here keeps that obligation attached to the source instead of
    living in someone's memory.
    """

    spdx: str
    url: str
    allows_derivatives: bool
    permits_commercial_use: bool
    requires_attribution: bool
    share_alike: bool

    @property
    def permits_training(self) -> bool:
        return self.allows_derivatives and self.permits_commercial_use


def _license(spdx: str, url: str, **flags: bool) -> LicenseTerms:
    return LicenseTerms(spdx=spdx, url=url, **flags)


LICENSES: dict[str, LicenseTerms] = {
    "ODC-By-1.0": _license(
        "ODC-By-1.0",
        "https://opendatacommons.org/licenses/by/1-0/",
        allows_derivatives=True,
        permits_commercial_use=True,
        requires_attribution=True,
        share_alike=False,
    ),
    "Apache-2.0": _license(
        "Apache-2.0",
        "https://www.apache.org/licenses/LICENSE-2.0",
        allows_derivatives=True,
        permits_commercial_use=True,
        requires_attribution=True,
        share_alike=False,
    ),
    "CC-BY-SA-3.0": _license(
        "CC-BY-SA-3.0",
        "https://creativecommons.org/licenses/by-sa/3.0/",
        allows_derivatives=True,
        permits_commercial_use=True,
        requires_attribution=True,
        share_alike=True,
    ),
    "CC-BY-SA-4.0": _license(
        "CC-BY-SA-4.0",
        "https://creativecommons.org/licenses/by-sa/4.0/",
        allows_derivatives=True,
        permits_commercial_use=True,
        requires_attribution=True,
        share_alike=True,
    ),
    "CC-BY-4.0": _license(
        "CC-BY-4.0",
        "https://creativecommons.org/licenses/by/4.0/",
        allows_derivatives=True,
        permits_commercial_use=True,
        requires_attribution=True,
        share_alike=False,
    ),
    # Present so the gate can *name* what it refuses. A source under these cannot enter the
    # corpus; it can only appear under `rejected`.
    "CC-BY-NC-ND-4.0": _license(
        "CC-BY-NC-ND-4.0",
        "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        allows_derivatives=False,
        permits_commercial_use=False,
        requires_attribution=True,
        share_alike=False,
    ),
    "CC-BY-NC-4.0": _license(
        "CC-BY-NC-4.0",
        "https://creativecommons.org/licenses/by-nc/4.0/",
        allows_derivatives=True,
        permits_commercial_use=False,
        requires_attribution=True,
        share_alike=False,
    ),
}


class LicenseError(ValueError):
    """A source's licence is unknown to the gate, or forbids what the PRD promises to ship."""


class ManifestError(ValueError):
    """The source manifest is malformed — unpinned revision, bad digest, duplicate name."""


# ---------------------------------------------------------------------------
# Source specification
# ---------------------------------------------------------------------------

RepoType = Literal["dataset", "model"]
Split = Literal["train", "validation", "test", "all"]


@dataclass(frozen=True, slots=True)
class SourceFile:
    """One file inside a pinned repository revision.

    ``order`` is the fetch priority, not a shard index. FineWeb2's Urdu split is 6.9 GB and
    Ravaan needs ~120M clean tokens, so the default fetch takes the smallest prefix that clears
    the target rather than the whole split. Which files were actually consumed is recorded in
    ``data/manifest.json``, so a partial fetch stays exactly as reproducible as a full one.
    """

    path: str
    sha256: str
    size: int
    split: Split = "train"
    order: int = 0
    note: str = ""

    def __post_init__(self) -> None:
        if not _SHA256_RE.match(self.sha256):
            raise ManifestError(
                f"{self.path}: sha256 must be 64 lowercase hex, got {self.sha256!r}"
            )
        if self.size <= 0:
            raise ManifestError(f"{self.path}: size must be positive, got {self.size}")

    def to_dict(self) -> dict:
        return asdict(self)

    def identity(self) -> dict:
        """The fields that define *which bytes* this is. `order` and `note` are operational."""
        return {"path": self.path, "sha256": self.sha256, "size": self.size, "split": self.split}

    @classmethod
    def from_dict(cls, data: dict) -> SourceFile:
        return cls(**data)


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """A pinned, licence-checked corpus source."""

    name: str
    role: str
    repo_id: str
    revision: str
    license: str
    files: tuple[SourceFile, ...]
    repo_type: RepoType = "dataset"
    config: str = ""
    homepage: str = ""
    citation: str = ""
    attribution: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not _SHA1_RE.match(self.revision):
            raise ManifestError(
                f"{self.name}: revision must be a pinned 40-hex commit SHA, got "
                f"{self.revision!r}. A moving ref makes the corpus irreproducible."
            )
        if not self.files:
            raise ManifestError(f"{self.name}: no files listed")
        seen = set()
        for f in self.files:
            if f.path in seen:
                raise ManifestError(f"{self.name}: duplicate file {f.path!r}")
            seen.add(f.path)
        self.terms  # noqa: B018 — raises LicenseError on an unknown licence

    @property
    def terms(self) -> LicenseTerms:
        try:
            return LICENSES[self.license]
        except KeyError:
            raise LicenseError(
                f"{self.name}: licence {self.license!r} is not in the gate. Add it to LICENSES "
                f"with its terms — do not skip the check."
            ) from None

    @property
    def total_bytes(self) -> int:
        return sum(f.size for f in self.files)

    def ordered_files(self) -> tuple[SourceFile, ...]:
        return tuple(sorted(self.files, key=lambda f: (f.order, f.path)))

    def to_dict(self) -> dict:
        data = asdict(self)
        data["files"] = [f.to_dict() for f in self.files]
        return data

    def identity(self) -> dict:
        """Corpus identity: repo, pinned revision, licence, and exactly which files.

        Prose fields (``role``, ``notes``, ``citation``) and fetch hints (``order``) are excluded
        — improving a note or reordering a download does not make it a different corpus, and a
        fingerprint that said otherwise would invalidate a frozen corpus for a typo fix.
        """
        return {
            "name": self.name,
            "repo_id": self.repo_id,
            "repo_type": self.repo_type,
            "revision": self.revision,
            "config": self.config,
            "license": self.license,
            "files": sorted((f.identity() for f in self.files), key=lambda d: d["path"]),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SourceSpec:
        data = dict(data)
        data.pop("_comment", None)
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known
        if unknown:
            raise ManifestError(f"unknown source keys: {sorted(unknown)}")
        data["files"] = tuple(SourceFile.from_dict(f) for f in data.get("files", ()))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class RejectedSource:
    """A source that was considered and not used, kept as provenance for PRD §6.1."""

    name: str
    reason: str
    license: str = ""
    repo_id: str = ""
    citation: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> RejectedSource:
        data = dict(data)
        data.pop("_comment", None)
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown:
            raise ManifestError(f"unknown rejected-source keys: {sorted(unknown)}")
        return cls(**data)


@dataclass(frozen=True, slots=True)
class SourceManifest:
    """The declarative source list — `configs/data/sources.json` in memory."""

    sources: tuple[SourceSpec, ...]
    rejected: tuple[RejectedSource, ...] = ()
    schema_version: int = MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.schema_version != MANIFEST_SCHEMA_VERSION:
            raise ManifestError(
                f"schema_version {self.schema_version} != {MANIFEST_SCHEMA_VERSION}"
            )
        names: set[str] = set()
        for spec in self.sources:
            if spec.name in names:
                raise ManifestError(f"duplicate source name {spec.name!r}")
            names.add(spec.name)
            if not spec.terms.permits_training:
                raise LicenseError(
                    f"{spec.name}: {spec.license} does not permit a permissively licensed "
                    f"derivative (PRD §6.3). Move it to `rejected` with a reason."
                )

    def __getitem__(self, name: str) -> SourceSpec:
        for spec in self.sources:
            if spec.name == name:
                return spec
        raise KeyError(name)

    @property
    def total_bytes(self) -> int:
        return sum(s.total_bytes for s in self.sources)

    def share_alike_sources(self) -> tuple[SourceSpec, ...]:
        return tuple(s for s in self.sources if s.terms.share_alike)

    def attribution_lines(self) -> tuple[str, ...]:
        """Attribution text for every source that requires it — for the report and the card."""
        return tuple(
            f"{s.name} — {s.attribution or s.repo_id} ({s.license}, {s.terms.url})"
            for s in self.sources
            if s.terms.requires_attribution
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "acquisition_version": ACQUISITION_VERSION,
            "sources": [s.to_dict() for s in self.sources],
            "rejected": [r.to_dict() for r in self.rejected],
        }

    @classmethod
    def from_dict(cls, data: dict) -> SourceManifest:
        return cls(
            schema_version=data.get("schema_version", MANIFEST_SCHEMA_VERSION),
            sources=tuple(SourceSpec.from_dict(s) for s in data.get("sources", ())),
            rejected=tuple(RejectedSource.from_dict(r) for r in data.get("rejected", ())),
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> SourceManifest:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json_file(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",  # never os.linesep — a CRLF manifest hashes differently on Windows
        )

    def fingerprint(self) -> str:
        """Stable hash over what actually determines the corpus. See :meth:`SourceSpec.identity`.

        Deliberately excludes ``rejected`` as well: recording why we skipped a source does not
        change the corpus, and should not invalidate a frozen one.
        """
        payload = json.dumps(
            {
                "schema_version": self.schema_version,
                "sources": sorted(
                    (s.identity() for s in self.sources), key=lambda d: str(d["name"])
                ),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# URLs, hashing, verification
# ---------------------------------------------------------------------------


def resolve_url(spec: SourceSpec, file: SourceFile) -> str:
    """The pinned download URL. Uses the revision SHA, never a branch name."""
    prefix = "" if spec.repo_type == "model" else f"{spec.repo_type}s/"
    return f"{HF_ENDPOINT}/{prefix}{spec.repo_id}/resolve/{spec.revision}/{file.path}"


def local_path(spec: SourceSpec, file: SourceFile, root: str | Path) -> Path:
    return Path(root) / spec.name / file.path


def sha256_file(path: str | Path, chunk: int = _CHUNK) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class VerifyResult:
    path: Path
    ok: bool
    reason: str = ""
    sha256: str = ""
    size: int = 0


def verify_file(path: str | Path, file: SourceFile) -> VerifyResult:
    """Check an on-disk file against the digest the pinned revision publishes."""
    path = Path(path)
    if not path.exists():
        return VerifyResult(path, ok=False, reason="missing")
    size = path.stat().st_size
    if size != file.size:
        return VerifyResult(
            path, ok=False, reason=f"size {size} != expected {file.size}", size=size
        )
    digest = sha256_file(path)
    if digest != file.sha256:
        return VerifyResult(
            path, ok=False, reason="sha256 mismatch", sha256=digest, size=size
        )
    return VerifyResult(path, ok=True, sha256=digest, size=size)


def plan_fetch(spec: SourceSpec, max_bytes: int | None = None) -> tuple[SourceFile, ...]:
    """The prefix of ``spec``'s files, in fetch order, that fits inside ``max_bytes``.

    A file is never split: if the next file would exceed the budget the plan stops there. With no
    budget this is simply every file.
    """
    if max_bytes is None:
        return spec.ordered_files()
    taken: list[SourceFile] = []
    used = 0
    for f in spec.ordered_files():
        if used + f.size > max_bytes:
            break
        taken.append(f)
        used += f.size
    return tuple(taken)


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AcquisitionRecord:
    """One acquired file, as it appears in `data/manifest.json`."""

    source: str
    repo_id: str
    revision: str
    license: str
    path: str
    local_path: str
    sha256: str
    size: int
    split: str
    url: str
    verified_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def _open(url: str, offset: int = 0):
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    if offset:
        request.add_header("Range", f"bytes={offset}-")
    return urllib.request.urlopen(request)  # noqa: S310 — https, from a pinned manifest


def fetch_file(
    spec: SourceSpec,
    file: SourceFile,
    root: str | Path,
    *,
    resume: bool = True,
    progress: bool = False,
) -> AcquisitionRecord:
    """Download one pinned file, verify it, and return its manifest record.

    Downloads land in ``<path>.part`` and are renamed only after the digest matches, so an
    interrupted run can never leave a truncated file that looks complete to a later stage.
    """
    dest = local_path(spec, file, root)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        result = verify_file(dest, file)
        if result.ok:
            return _record(spec, file, dest, result.sha256)
        raise ValueError(f"{dest} exists but does not verify: {result.reason}")

    part = dest.with_suffix(dest.suffix + ".part")
    offset = part.stat().st_size if resume and part.exists() else 0
    if offset > file.size:
        offset = 0  # a stale part from a different revision — start over
    digest = hashlib.sha256()
    if offset:
        with open(part, "rb") as fh:
            while block := fh.read(_CHUNK):
                digest.update(block)

    url = resolve_url(spec, file)
    try:
        response = _open(url, offset)
    except urllib.error.HTTPError as exc:
        if offset and exc.code in (416, 501):  # range unsatisfiable / unsupported
            offset, digest = 0, hashlib.sha256()
            response = _open(url, 0)
        else:
            raise

    served_partial = response.status == 206
    if offset and not served_partial:
        offset, digest = 0, hashlib.sha256()  # server ignored the Range header

    with response, open(part, "ab" if offset else "wb") as fh:
        done = offset
        while block := response.read(_CHUNK):
            fh.write(block)
            digest.update(block)
            done += len(block)
            if progress:
                pct = 100 * done / file.size
                print(f"\r  {file.path}  {done / 1e6:,.0f}/{file.size / 1e6:,.0f} MB "
                      f"({pct:5.1f}%)", end="", file=sys.stderr)
    if progress:
        print(file=sys.stderr)

    actual = digest.hexdigest()
    if actual != file.sha256:
        # `replace`, not `rename`: on Windows renaming onto an existing `.bad` from a previous
        # failed attempt raises, which would mask the digest mismatch behind a FileExistsError.
        part.replace(part.with_suffix(".bad"))
        raise ValueError(
            f"{file.path}: sha256 {actual} != manifest {file.sha256}. The pinned revision does "
            f"not contain the bytes we expected — do not use this file."
        )
    part.replace(dest)
    return _record(spec, file, dest, actual)


def _record(spec: SourceSpec, file: SourceFile, dest: Path, digest: str) -> AcquisitionRecord:
    return AcquisitionRecord(
        source=spec.name,
        repo_id=spec.repo_id,
        revision=spec.revision,
        license=spec.license,
        path=file.path,
        local_path=str(dest),
        sha256=digest,
        size=file.size,
        split=file.split,
        url=resolve_url(spec, file),
        verified_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


def write_acquisition_manifest(
    records: Iterable[AcquisitionRecord],
    manifest: SourceManifest,
    path: str | Path,
    *,
    merge: bool = True,
) -> dict:
    """Write `data/manifest.json` — what was actually acquired, and under what terms.

    Merges with whatever is already there, keyed by ``(source, path)``. A 6.9 GB source gets
    fetched over several sessions and often one ``--source`` at a time; a manifest that only
    described the most recent invocation would claim the corpus was smaller than it is, and the
    stage-9 split would silently be built from files the manifest does not list.
    """
    path = Path(path)
    entries: dict[tuple[str, str], dict] = {}
    if merge and path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        for row in existing.get("files", ()):
            entries[(row["source"], row["path"])] = row
    for record in records:
        entries[(record.source, record.path)] = record.to_dict()

    files = [entries[key] for key in sorted(entries)]
    payload = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "acquisition_version": ACQUISITION_VERSION,
        "sources_fingerprint": manifest.fingerprint(),
        "written_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "files": files,
        "total_bytes": sum(row["size"] for row in files),
        "attribution": list(manifest.attribution_lines()),
        "share_alike_sources": [s.name for s in manifest.share_alike_sources()],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",  # never os.linesep — a CRLF manifest hashes differently on Windows
    )
    return payload


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

DEFAULT_SOURCES = Path(__file__).resolve().parents[2] / "configs" / "data" / "sources.json"


def _selected(manifest: SourceManifest, names: list[str] | None) -> Iterator[SourceSpec]:
    if not names:
        yield from manifest.sources
        return
    for name in names:
        yield manifest[name]


def _human(n: int) -> str:
    return f"{n / 1e9:.2f} GB" if n >= 1e9 else f"{n / 1e6:.1f} MB"


def _cmd_plan(args, manifest: SourceManifest) -> int:
    budget = int(args.max_bytes) if args.max_bytes else None
    total = 0
    for spec in _selected(manifest, args.source):
        files = plan_fetch(spec, budget)
        print(f"{spec.name}  [{spec.license}]  {spec.repo_id}@{spec.revision[:12]}")
        for f in files:
            print(f"    {f.split:<10} {_human(f.size):>10}  {f.path}")
            total += f.size
        skipped = len(spec.files) - len(files)
        if skipped:
            print(f"    ... {skipped} file(s) over budget, not planned")
    print(f"\ntotal to fetch: {_human(total)}")
    print(f"sources fingerprint: {manifest.fingerprint()}")
    if manifest.rejected:
        print("\nrejected sources (provenance, PRD §6.1):")
        for r in manifest.rejected:
            print(f"    {r.name}: {r.reason}")
    return 0


def _cmd_fetch(args, manifest: SourceManifest) -> int:
    budget = int(args.max_bytes) if args.max_bytes else None
    records: list[AcquisitionRecord] = []
    for spec in _selected(manifest, args.source):
        for f in plan_fetch(spec, budget):
            print(f"{spec.name}: {f.path}", file=sys.stderr)
            records.append(fetch_file(spec, f, args.root, progress=True))
    payload = write_acquisition_manifest(records, manifest, args.manifest)
    print(f"wrote {args.manifest}: {len(records)} file(s), {_human(payload['total_bytes'])}")
    return 0


def _cmd_verify(args, manifest: SourceManifest) -> int:
    failures = 0
    declared: set[tuple[str, str]] = set()
    for spec in _selected(manifest, args.source):
        for f in spec.ordered_files():
            declared.add((spec.name, f.path))
            path = local_path(spec, f, args.root)
            if not path.exists() and args.skip_missing:
                continue
            result = verify_file(path, f)
            status = "ok" if result.ok else f"FAIL ({result.reason})"
            print(f"{status:<28} {spec.name}/{f.path}")
            failures += not result.ok

    # The other direction: an entry acquired earlier and since dropped from sources.json. The
    # file on disk still verifies against a digest nothing declares any more, so checking
    # sources.json against disk cannot catch it — and a stage that globs `data/raw` would
    # silently train on it.
    acquired = Path(args.manifest)
    if not args.source and acquired.exists():
        recorded = json.loads(acquired.read_text(encoding="utf-8")).get("files", ())
        orphans = [r for r in recorded if (r["source"], r["path"]) not in declared]
        for row in orphans:
            print(f"{'ORPHAN (not in sources.json)':<28} {row['source']}/{row['path']}")
        failures += len(orphans)
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("-s", "--sources", default=str(DEFAULT_SOURCES), help="sources.json")
    parser.add_argument("--root", default="data/raw", help="download root (default: data/raw)")
    parser.add_argument("--source", action="append", help="restrict to this source (repeatable)")
    parser.add_argument("--max-bytes", type=float, help="fetch budget in bytes, e.g. 3e9")
    parser.add_argument("--manifest", default="data/manifest.json", help="acquisition manifest")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("plan", help="show what would be fetched, and the licence terms")
    sub.add_parser("fetch", help="download, verify against the pinned digests, record")

    verify = sub.add_parser("verify", help="re-verify files already on disk")
    verify.add_argument("--skip-missing", action="store_true")

    args = parser.parse_args(argv)
    manifest = SourceManifest.from_json_file(args.sources)

    return {"plan": _cmd_plan, "fetch": _cmd_fetch, "verify": _cmd_verify}[args.command](
        args, manifest
    )


if __name__ == "__main__":
    raise SystemExit(main())
