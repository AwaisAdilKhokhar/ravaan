"""Streaming shard reader — the iterator every stage from 3 onward consumes.

Stages 1, 2 and 4 each took text from wherever the caller had it. From stage 3 the pipeline runs
over the frozen corpus itself, repeatedly, so it needs one reader with one set of guarantees.
Three properties, in priority order:

1. **A prefix is not a sample.** FineWeb2's `urd_Arab` shard 001 is not sorted by CommonCrawl
   dump — 88 distinct dumps appear across it — but it is not shuffled either: row group 0 skews
   to CC-MAIN-2021/2022, row group 206 to CC-MAIN-2024. Reading the first N documents therefore
   measures one slice of the crawl's history, and measurements taken that way moved by 25–50%
   once corrected (session 4, Finding E). PRD §6.1 requires arm A's 25M corpus to be a subsample
   of arm B's 100M differing *in size and nothing else*; a prefix-based subsample would make arm
   A systematically older web text and confound the primary endpoint with crawl date. So the
   default read order is a seeded shuffle, and ``order="sequential"`` — the fast, biased one — is
   the option you have to ask for by name.

2. **Selection is stable under re-runs and independent of read order.** :func:`stable_unit` maps
   a document id to a uniform value in [0, 1) by hashing, so ``sample_rate`` and (later) stage 9's
   split assignment depend only on the id and a salt. Rerunning with a different seed, resuming
   from a checkpoint, or reading the file in a different order all select the *same* documents.
   Shuffling decides what you look at first; hashing decides what belongs to what, and the two
   must not be the same mechanism.

3. **Resumption is exact or it fails.** A checkpoint records the plan fingerprint — file digests,
   seed, order, sample rate — and :meth:`ShardReader.resume` refuses a checkpoint written under a
   different plan rather than silently resuming into a different document order. A 3.5G-character
   pass that dies at 80% should restart at 80%, and a resumed pass that quietly skipped or
   duplicated documents is worse than one that crashed.

The reader is the first component that genuinely needs the ``[data]`` extra: parquet has to be
parsed. CSV sources stay on the standard library.

    from ravaan.data.shards import ShardReader
    for doc in ShardReader.from_manifest("fineweb2-urd_Arab", limit=20_000, sample_rate=0.02):
        ...
"""

from __future__ import annotations

import contextlib
import csv
import hashlib
import json
import random
import sys
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

__all__ = [
    "SHARDS_VERSION",
    "ReadOrder",
    "Document",
    "ShardFile",
    "SourceLayout",
    "LAYOUTS",
    "CsvIndex",
    "ReaderPosition",
    "ShardReader",
    "stable_unit",
    "load_manifest_files",
]

# Bump when the *order* or *membership* of what the reader yields changes. A frozen corpus is
# only reproducible if the thing that enumerated it is versioned too.
SHARDS_VERSION = "1.0.0"

ReadOrder = Literal["shuffled", "sequential"]

_CSV_BLOCK_ROWS = 10_000  # CSV has no row groups; block it so resume has somewhere to land.

# CSV fields can be whole documents. The default limit (128 KiB) truncates them silently.
csv.field_size_limit(1 << 27)


# ---------------------------------------------------------------------------
# Stable selection
# ---------------------------------------------------------------------------


def stable_unit(doc_id: str, salt: str = "") -> float:
    """Map a document id to a uniform value in [0, 1), deterministically and order-independently.

    This is the selection primitive for ``sample_rate`` here, and for stage 9's split assignment
    and arm A's 25M subsample later. Hashing rather than shuffling is the point: two runs that
    read the corpus in different orders, or resume at different offsets, must still put the same
    document in the same split. A shuffle cannot promise that; a hash of the id does, for free,
    with no state.

    blake2b rather than the builtin ``hash``, which is salted per process by PYTHONHASHSEED and
    would silently reassign every document on every run.
    """
    digest = hashlib.blake2b(f"{salt}\x00{doc_id}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2**64


def _rng(*parts: object) -> random.Random:
    """A generator seeded by an *integer* derived from the parts.

    Seeded through blake2b rather than by handing `random.Random` the tuple or string directly:
    tuple seeds were removed in 3.14 and string seeds go through a hash whose stability across
    releases is not something a frozen corpus should depend on. Integer seeding is documented and
    unchanged, so the same checkpoint resumes into the same order on any interpreter.
    """
    key = "\x00".join(str(part) for part in parts).encode()
    return random.Random(int.from_bytes(hashlib.blake2b(key, digest_size=16).digest(), "big"))


# ---------------------------------------------------------------------------
# What a document is
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Document:
    """One unit of corpus text, with enough provenance to trace it back to a pinned file.

    ``meta`` carries the source's own columns (``url``, ``dump``, ``date``, ``language_score``,
    the parallel Urdu side of a Roman-Urdu-Parl row) untouched. Stage 3 reads ``url`` from it to
    test whether Arabic-variant spelling is site-correlated; stage 7 will read it to keep
    near-duplicate clusters explainable.
    """

    source: str
    doc_id: str
    text: str
    meta: dict[str, Any] = field(default_factory=dict)
    path: str = ""
    block: int = -1
    row: int = -1

    def unit(self, salt: str = "") -> float:
        return stable_unit(self.doc_id, salt)


# ---------------------------------------------------------------------------
# Source layouts
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SourceLayout:
    """Which column holds the text, which holds the id, and what else is worth keeping.

    Declared per source rather than auto-detected. Auto-detection picks "the first string column"
    and would happily hand stage 3 the ``url`` column of a file whose schema changed — a corpus
    made of URLs would score as English and vanish at stage 3, looking exactly like a language
    filter doing its job.
    """

    text_column: str
    id_column: str | None = None
    meta_columns: tuple[str, ...] = ()
    unit: str = "document"  # "document" | "sentence" — Roman-Urdu-Parl rows are sentence pairs

    def document_id(self, source: str, path: str, block: int, row: int, value: Any) -> str:
        """Prefer the source's own id; fall back to a position that is stable for a pinned file.

        The fallback is only sound because acquisition pins revisions and verifies digests: for a
        given SHA-256, row 41 of ``test_set.csv`` is the same sentence forever. Without stage 1's
        pinning this would be a bug.
        """
        if value is not None and value != "":
            return f"{source}:{value}"
        return f"{source}:{path}:{block}:{row}"


LAYOUTS: dict[str, SourceLayout] = {
    "fineweb2-urd_Arab": SourceLayout(
        text_column="text",
        id_column="id",
        # `url` answers the site-correlation question; `dump`/`date` are what Finding E is about;
        # `language`/`language_script`/`language_score` are FineWeb2's own GlotLID output, which
        # is the only external language label stage 3 can check itself against without acquiring
        # a new source. (`top_langs` is also in the schema and is the empty string `{}` for every
        # row of this shard, so it is not read.)
        meta_columns=(
            "url",
            "dump",
            "date",
            "language",
            "language_script",
            "language_score",
            "minhash_cluster_size",
        ),
    ),
    "urdu-wikipedia": SourceLayout(
        text_column="text",
        id_column="id",
        meta_columns=("url", "title"),
    ),
    "roman-urdu-parl": SourceLayout(
        text_column="Roman-Urdu text",
        id_column=None,  # no id column; position under a pinned digest is the id
        meta_columns=("Urdu text",),
        unit="sentence",
    ),
}


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ShardFile:
    """One acquired file, as `data/manifest.json` records it."""

    source: str
    path: str  # path *within* the source, as pinned upstream — platform independent
    local_path: Path
    sha256: str
    split: str = "train"

    @property
    def suffix(self) -> str:
        return self.local_path.suffix.lower()


def load_manifest_files(
    manifest_path: str | Path = "data/manifest.json",
    *,
    source: str | None = None,
    split: str | None = None,
) -> list[ShardFile]:
    """Read `data/manifest.json` and return its files, optionally filtered.

    Sorted by ``(source, path)`` so the read plan does not depend on the order in which files
    happened to be downloaded — a 6.9 GB source arrives over several sessions.
    """
    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    root = Path(manifest_path).resolve().parent.parent
    files: list[ShardFile] = []
    for record in payload.get("files", []):
        if source is not None and record["source"] != source:
            continue
        if split is not None and record.get("split") != split:
            continue
        # The manifest stores whatever separator the fetching platform used. Normalize, then
        # resolve relative to the repo root so a manifest written on Windows reads on Linux.
        local = Path(str(record["local_path"]).replace("\\", "/"))
        files.append(
            ShardFile(
                source=record["source"],
                path=record["path"],
                local_path=local if local.is_absolute() else root / local,
                sha256=record["sha256"],
                split=record.get("split", "train"),
            )
        )
    files.sort(key=lambda f: (f.source, f.path))
    return files


# ---------------------------------------------------------------------------
# CSV block index
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CsvIndex:
    """Header, row count, and the byte offset where each block of rows starts."""

    header: tuple[str, ...]
    rows: int
    offsets: tuple[int, ...]
    block_rows: int = _CSV_BLOCK_ROWS

    def to_dict(self) -> dict[str, Any]:
        return {
            "shards_version": SHARDS_VERSION,
            "header": list(self.header),
            "rows": self.rows,
            "offsets": list(self.offsets),
            "block_rows": self.block_rows,
        }


def _decoded_lines(handle) -> Iterator[str]:
    """Lines from a binary handle, one at a time, leaving ``tell()`` meaningful between records."""
    while True:
        line = handle.readline()
        if not line:
            return
        yield line.decode("utf-8")


def _csv_index_path(shard: ShardFile) -> Path:
    return shard.local_path.with_suffix(shard.local_path.suffix + ".blocks.json")


def _build_csv_index(shard: ShardFile, block_rows: int = _CSV_BLOCK_ROWS) -> CsvIndex:
    offsets: list[int] = []
    with shard.local_path.open("rb") as handle:
        lines = _decoded_lines(handle)
        reader = csv.reader(lines)
        header = tuple(next(reader, []))
        rows = 0
        while True:
            position = handle.tell()
            record = next(reader, None)
            if record is None:
                break
            if rows % block_rows == 0:
                offsets.append(position)
            rows += 1
    index = CsvIndex(header=header, rows=rows, offsets=tuple(offsets), block_rows=block_rows)
    # A cache that cannot be written is not an error — the index is simply rebuilt next time.
    with contextlib.suppress(OSError):  # a read-only corpus mount, say
        _csv_index_path(shard).write_text(
            json.dumps({"sha256": shard.sha256, **index.to_dict()}) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return index


def _load_csv_index(shard: ShardFile) -> CsvIndex | None:
    """Read a cached index, but only if it describes *these* bytes.

    Keyed on the digest acquisition pinned, not on mtime: a shard replaced by another revision
    has the same name and a different content, and stale offsets would land mid-record.
    """
    path = _csv_index_path(shard)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("sha256") != shard.sha256 or payload.get("shards_version") != SHARDS_VERSION:
        return None
    return CsvIndex(
        header=tuple(payload["header"]),
        rows=payload["rows"],
        offsets=tuple(payload["offsets"]),
        block_rows=payload.get("block_rows", _CSV_BLOCK_ROWS),
    )


# ---------------------------------------------------------------------------
# Position and checkpointing
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReaderPosition:
    """Where a pass got to. ``row`` is the offset *within* the block, not within the file."""

    file_index: int = 0
    block_index: int = 0
    row: int = 0
    emitted: int = 0
    selected: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


# ---------------------------------------------------------------------------
# The reader
# ---------------------------------------------------------------------------


class ShardReader:
    """Iterate a source's files as :class:`Document`s, in a seeded shuffled order by default.

    ``limit`` caps documents *yielded*; ``sample_rate`` decides membership by
    :func:`stable_unit`, so the two compose: ``limit=20_000, sample_rate=0.02`` reads a spread of
    roughly a thousand row groups instead of the twenty a bare limit would touch.
    """

    def __init__(
        self,
        files: Sequence[ShardFile],
        *,
        layout: SourceLayout | None = None,
        order: ReadOrder = "shuffled",
        seed: int = 0,
        limit: int | None = None,
        sample_rate: float | None = None,
        sample_salt: str = "",
        skip_empty: bool = True,
    ) -> None:
        if order not in ("shuffled", "sequential"):
            raise ValueError(f"order must be 'shuffled' or 'sequential', got {order!r}")
        if sample_rate is not None and not 0.0 < sample_rate <= 1.0:
            raise ValueError(f"sample_rate must be in (0, 1], got {sample_rate!r}")
        if not files:
            raise ValueError("no files to read")

        sources = {f.source for f in files}
        if layout is None:
            if len(sources) != 1:
                raise ValueError(f"layout required when reading several sources: {sorted(sources)}")
            source = next(iter(sources))
            if source not in LAYOUTS:
                raise KeyError(
                    f"no layout declared for source {source!r}; add one to shards.LAYOUTS "
                    "rather than auto-detecting the text column"
                )
            layout = LAYOUTS[source]

        self.files = list(files)
        self.layout = layout
        self.order = order
        self.seed = seed
        self.limit = limit
        self.sample_rate = sample_rate
        self.sample_salt = sample_salt
        self.skip_empty = skip_empty
        self.position = ReaderPosition()
        self._start = ReaderPosition()

    # --- plan identity -----------------------------------------------------

    def plan_fingerprint(self) -> str:
        """Hash of everything that determines *which documents, in what order*.

        File digests rather than paths: the same shard moved to another directory is the same
        read plan, and a shard replaced by a different revision is not.
        """
        payload = json.dumps(
            {
                "version": SHARDS_VERSION,
                "files": [[f.source, f.path, f.sha256] for f in self.files],
                "layout": asdict(self.layout),
                "order": self.order,
                "seed": self.seed,
                "sample_rate": self.sample_rate,
                "sample_salt": self.sample_salt,
                "skip_empty": self.skip_empty,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    # --- checkpointing -----------------------------------------------------

    def save_checkpoint(self, path: str | Path) -> None:
        payload = {
            "shards_version": SHARDS_VERSION,
            "plan_fingerprint": self.plan_fingerprint(),
            "position": self.position.to_dict(),
        }
        Path(path).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n"
        )

    def resume(self, path: str | Path) -> ShardReader:
        """Continue from a checkpoint, or refuse.

        A checkpoint from a different plan describes offsets into a different document order.
        Resuming it would skip and duplicate documents in a pattern nothing downstream could
        detect — the corpus would simply be wrong. So it is an error, not a warning.
        """
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        expected = self.plan_fingerprint()
        if payload.get("plan_fingerprint") != expected:
            raise ValueError(
                f"checkpoint {path} was written for plan {payload.get('plan_fingerprint')!r}, "
                f"this reader is plan {expected!r} — refusing to resume into a different order"
            )
        self._start = ReaderPosition(**payload["position"])
        self.position = self._start
        return self

    # --- iteration ---------------------------------------------------------

    def __iter__(self) -> Iterator[Document]:
        emitted = self._start.emitted
        selected = self._start.selected
        limit = self.limit

        for file_index in range(self._start.file_index, len(self.files)):
            shard = self.files[file_index]
            resuming = file_index == self._start.file_index
            blocks = self._block_plan(shard, file_index)
            block_start = self._start.block_index if resuming else 0

            for block_position in range(block_start, len(blocks)):
                block_index = blocks[block_position]
                row_start = (
                    self._start.row if resuming and block_position == block_start else 0
                )
                # Rows keep the position they hold *in the file*, not the one the shuffle gave
                # them. A source without an id column identifies documents by position, and an
                # id that depended on the read seed would rename every document on every run —
                # breaking stable sampling, stage 9's splits and stage 6's dedup at once. So the
                # permutation moves the pair, never the number inside it.
                rows = list(enumerate(self._read_block(shard, block_index)))
                if self.order == "shuffled":
                    _rng("rows", self.seed, file_index, block_index).shuffle(rows)

                for offset in range(row_start, len(rows)):
                    row_index, (text, raw_id, meta) = rows[offset]
                    selected += 1
                    self.position = ReaderPosition(
                        file_index, block_position, offset + 1, emitted, selected
                    )
                    if self.skip_empty and not (text and text.strip()):
                        continue
                    doc_id = self.layout.document_id(
                        shard.source, shard.path, block_index, row_index, raw_id
                    )
                    if (
                        self.sample_rate is not None
                        and stable_unit(doc_id, self.sample_salt) >= self.sample_rate
                    ):
                        continue
                    yield Document(
                        source=shard.source,
                        doc_id=doc_id,
                        text=text,
                        meta=meta,
                        path=shard.path,
                        block=block_index,
                        row=row_index,
                    )
                    emitted += 1
                    self.position = ReaderPosition(
                        file_index, block_position, offset + 1, emitted, selected
                    )
                    if limit is not None and emitted >= limit:
                        return

    def _block_plan(self, shard: ShardFile, file_index: int) -> list[int]:
        """Block indices in the order they will be read."""
        count = self._block_count(shard)
        blocks = list(range(count))
        if self.order == "shuffled":
            _rng("blocks", self.seed, file_index).shuffle(blocks)
        return blocks

    # --- format handling ---------------------------------------------------

    def _block_count(self, shard: ShardFile) -> int:
        if shard.suffix == ".parquet":
            return self._parquet_file(shard).metadata.num_row_groups
        if shard.suffix == ".csv":
            return len(self._csv_index(shard).offsets)
        raise ValueError(f"unsupported shard format: {shard.local_path}")

    def _read_block(self, shard: ShardFile, block_index: int) -> list[tuple[str, Any, dict]]:
        if shard.suffix == ".parquet":
            return self._read_parquet_block(shard, block_index)
        return self._read_csv_block(shard, block_index)

    # parquet ---------------------------------------------------------------

    def _parquet_file(self, shard: ShardFile):
        cached = getattr(self, "_pq_cache", None)
        if cached is not None and cached[0] == shard.local_path:
            return cached[1]
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:  # pragma: no cover - depends on the installed extra
            raise ImportError(
                "reading parquet shards needs the [data] extra: pip install -e '.[data]'"
            ) from exc
        parquet = pq.ParquetFile(shard.local_path)
        self._pq_cache = (shard.local_path, parquet)
        return parquet

    def _read_parquet_block(self, shard: ShardFile, index: int) -> list[tuple[str, Any, dict]]:
        parquet = self._parquet_file(shard)
        available = set(parquet.schema_arrow.names)
        if self.layout.text_column not in available:
            raise KeyError(
                f"{shard.local_path} has no column {self.layout.text_column!r}; "
                f"schema is {sorted(available)}"
            )
        columns = [self.layout.text_column]
        if self.layout.id_column and self.layout.id_column in available:
            columns.append(self.layout.id_column)
        columns += [c for c in self.layout.meta_columns if c in available and c not in columns]

        table = parquet.read_row_group(index, columns=columns)
        batch = table.to_pydict()
        texts = batch[self.layout.text_column]
        ids = batch.get(self.layout.id_column) if self.layout.id_column else None
        skip = {self.layout.text_column, self.layout.id_column}
        meta_keys = [c for c in columns if c not in skip]
        return [
            (
                texts[i] or "",
                ids[i] if ids is not None else None,
                {key: batch[key][i] for key in meta_keys},
            )
            for i in range(len(texts))
        ]

    # csv -------------------------------------------------------------------
    #
    # CSV has no row groups, so blocks are byte offsets found by one pass over the file and
    # cached beside it. The obvious alternative — re-reading from the top for every block —
    # is quadratic, and Roman-Urdu-Parl's train split is 1.2 GB of 6.37M rows.
    #
    # The index is built in *binary*: offsets are then plain byte positions rather than the
    # opaque cookies text mode returns, so a cache written by one interpreter is readable by
    # the next. Lines are fed to `csv.reader` one at a time, which is what lets `tell()` sit
    # exactly on a record boundary — the reader pulls a line only when it needs one, and stops
    # as soon as a record is complete, so no lookahead skews the offset.

    def _csv_index(self, shard: ShardFile) -> CsvIndex:
        cache: dict[Path, CsvIndex] = getattr(self, "_csv_index_cache", {})
        if shard.local_path in cache:
            return cache[shard.local_path]
        index = _load_csv_index(shard) or _build_csv_index(shard)
        cache[shard.local_path] = index
        self._csv_index_cache = cache
        return index

    def _read_csv_block(self, shard: ShardFile, index: int) -> list[tuple[str, Any, dict]]:
        plan = self._csv_index(shard)
        if self.layout.text_column not in plan.header:
            raise KeyError(
                f"{shard.local_path} has no column {self.layout.text_column!r}; "
                f"header is {plan.header}"
            )
        rows: list[tuple[str, Any, dict]] = []
        with shard.local_path.open("rb") as handle:
            handle.seek(plan.offsets[index])
            reader = csv.reader(_decoded_lines(handle))
            for record in reader:
                fields = dict(zip(plan.header, record, strict=False))
                rows.append(
                    (
                        fields.get(self.layout.text_column) or "",
                        fields.get(self.layout.id_column) if self.layout.id_column else None,
                        {k: fields.get(k) for k in self.layout.meta_columns if k in fields},
                    )
                )
                if len(rows) >= _CSV_BLOCK_ROWS:
                    break
        return rows

    # --- construction ------------------------------------------------------

    @classmethod
    def from_manifest(
        cls,
        source: str,
        *,
        manifest_path: str | Path = "data/manifest.json",
        split: str | None = None,
        **kwargs: Any,
    ) -> ShardReader:
        files = load_manifest_files(manifest_path, source=source, split=split)
        if not files:
            raise ValueError(
                f"manifest {manifest_path} lists no files for source={source!r} split={split!r}"
            )
        return cls(files, **kwargs)


# ---------------------------------------------------------------------------
# CLI — peek at a source without writing a script
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("source", help="source name as it appears in data/manifest.json")
    parser.add_argument("-m", "--manifest", default="data/manifest.json")
    parser.add_argument("--split", help="restrict to one split")
    parser.add_argument("-n", "--limit", type=int, default=5, help="documents to print")
    parser.add_argument("--sample-rate", type=float, help="stable per-document sampling rate")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="read in file order — biased towards one slice of the crawl; see module docstring",
    )
    parser.add_argument("--chars", type=int, default=200, help="characters of text to show")
    args = parser.parse_args(argv)

    reader = ShardReader.from_manifest(
        args.source,
        manifest_path=args.manifest,
        split=args.split,
        order="sequential" if args.sequential else "shuffled",
        seed=args.seed,
        limit=args.limit,
        sample_rate=args.sample_rate,
    )
    print(f"plan {reader.plan_fingerprint()} over {len(reader.files)} file(s)", file=sys.stderr)
    for doc in reader:
        print(json.dumps({
            "doc_id": doc.doc_id,
            "block": doc.block,
            "row": doc.row,
            "chars": len(doc.text),
            "text": doc.text[: args.chars],
            "meta": doc.meta,
        }, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
