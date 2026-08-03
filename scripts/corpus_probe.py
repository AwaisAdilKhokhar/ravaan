#!/usr/bin/env python
"""Run stages 2 and 4 over a sample of a real corpus shard and report what they did.

This is the diagnostic the pipeline was missing: stage 2 and stage 4 were both built against
hand-written fixtures, which prove the rules do what they say but say nothing about whether the
rules *fire* on the material Ravaan actually has. A normalizer whose counts are all zero on real
FineWeb2 Urdu is either unnecessary or broken, and there is no way to tell which from the tests.

    python scripts/corpus_probe.py data/raw/urdu-wikipedia/20231101.ur/*.parquet --limit 5000
    python scripts/corpus_probe.py <shard> --limit 20000 --json reports/probe_fineweb.json

Not a substitute for PRD §6.3.5's 200 manually inspected samples — that is a human reading Urdu,
and it happens at stage 5. This tells you where to point them. Requires the `[data]` extra.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.data.encoding import EncodingConfig, EncodingLog, validate_text  # noqa: E402
from ravaan.data.normalization import (  # noqa: E402
    NormalizationConfig,
    NormalizationLog,
    normalize,
)

TEXT_COLUMNS = ("text", "content", "raw_content", "Data", "urdu", "document")


def _text_column(schema) -> str:
    for name in TEXT_COLUMNS:
        if name in schema.names:
            return name
    strings = [
        n for n, t in zip(schema.names, schema.types, strict=True) if "string" in str(t)
    ]
    if not strings:
        raise SystemExit(f"no string column found in {schema.names}")
    return strings[0]


def _spread(n_groups: int, needed: int) -> list[int]:
    """Row-group indices spaced evenly across the file.

    A prefix is not a sample. FineWeb2's `urd_Arab` shard 001 is not sorted by crawl dump — 88
    distinct dumps appear across it — but it is not shuffled either: row group 0 skews to
    CC-MAIN-2021/2022 and row group 206 skews to CC-MAIN-2024. Reading the first N documents
    therefore measures one slice of the crawl's history. Hence the default.
    """
    if needed >= n_groups:
        return list(range(n_groups))
    if needed <= 1:
        return [0]
    return sorted({round(i * (n_groups - 1) / (needed - 1)) for i in range(needed)})


def _read(paths: list[str], column: str | None, limit: int, head: bool):
    import pyarrow.parquet as pq

    taken = 0
    for path in paths:
        parquet = pq.ParquetFile(path)
        col = column or _text_column(parquet.schema_arrow)
        total_groups = parquet.metadata.num_row_groups
        if head:
            groups = range(total_groups)
        else:
            per_group = max(parquet.metadata.row_group(0).num_rows, 1)
            groups = _spread(total_groups, -(-(limit - taken) // per_group))
        for index in groups:
            for value in parquet.read_row_group(index, columns=[col]).column(0).to_pylist():
                if value is None:
                    continue
                yield value
                taken += 1
                if taken >= limit:
                    return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("paths", nargs="+", help="parquet shard(s)")
    parser.add_argument("--column", help="text column (default: auto-detect)")
    parser.add_argument("--limit", type=int, default=5000, help="documents to read")
    parser.add_argument(
        "--head",
        action="store_true",
        help="read from the start instead of spreading across row groups (biased; see _spread)",
    )
    parser.add_argument("--examples", type=int, default=3, help="changed documents to show")
    parser.add_argument("--seed", type=int, default=0, help="seed for example selection")
    parser.add_argument("--json", help="write the two stage logs here")
    args = parser.parse_args(argv)

    encoding_config, normalization_config = EncodingConfig(), NormalizationConfig()
    stage2 = EncodingLog(config=encoding_config)
    stage4 = NormalizationLog(config=normalization_config)
    rng = random.Random(args.seed)
    examples: list[tuple[str, str, dict]] = []

    for raw in _read(args.paths, args.column, args.limit, args.head):
        checked = validate_text(raw, encoding_config)
        stage2.add(checked)
        if not checked.accepted:
            continue
        result = normalize(checked.text or "", normalization_config)
        stage4.add(result)
        # Reservoir sample of documents the normalizer actually changed, so the examples are not
        # all drawn from the head of the shard.
        if result.changed:
            if len(examples) < args.examples:
                examples.append((result.original, result.normalized, result.counts))
            elif rng.random() < args.examples / stage4.documents_changed:
                examples[rng.randrange(args.examples)] = (
                    result.original,
                    result.normalized,
                    result.counts,
                )

    payload = {"stage2_encoding": stage2.to_dict(), "stage4_normalization": stage4.to_dict()}
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if stage4.documents:
        changed = 100 * stage4.documents_changed / stage4.documents
        print(f"\nnormalizer touched {changed:.1f}% of accepted documents", file=sys.stderr)
        per_doc = {k: v / stage4.documents for k, v in stage4.counts.items()}
        for rule, rate in sorted(per_doc.items(), key=lambda kv: -kv[1]):
            print(f"  {rule:<20} {rate:>10.2f} per document", file=sys.stderr)

    for i, (before, after, counts) in enumerate(examples, 1):
        print(f"\n--- example {i}: {sorted(counts)} ---", file=sys.stderr)
        print(f"  before: {before[:160]!r}", file=sys.stderr)
        print(f"  after : {after[:160]!r}", file=sys.stderr)

    if args.json:
        Path(args.json).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
