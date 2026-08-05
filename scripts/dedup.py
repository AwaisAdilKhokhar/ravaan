#!/usr/bin/env python
"""Run pipeline stages 2→6 over real sources and report what exact dedup actually removes.

The companion to `scripts/probe.py`, which stops at stage 5. Stage 6 needs its own driver for one
structural reason: it is the first stage that is not a function of a single document. It reads the
corpus twice — once to build the group index, once to decide — so it cannot be folded into a
single-pass probe without giving up the property that makes it reproducible (see
`ravaan.data.dedup`).

Three questions it exists to answer, each of which the modules cannot answer about themselves:

* **Does normalizing before hashing find duplicates that raw hashing misses?** Session 5's Finding
  F says it should: the top 1% of domains carry 65.3% of Arabic-variant hits, and religious
  publishers republish the same texts across many domains. Every run reports both numbers, so the
  stage order 4 → 6 is justified by a measurement rather than by the argument that motivated it.
* **How much of this corpus is duplicated at all, and where?** The per-source keep rate, the
  largest groups with their text, and how much sits *across* sources — CommonCrawl crawls
  Wikipedia, so FineWeb2 contains Wikipedia, and stage 8 needs that number because Wikipedia is
  also where §8.2's held-out evaluation text comes from.
* **Is the win real or already counted?** Dedup yield is measured on stage 5's *survivors* by
  default. Half of Urdu Wikipedia is a template stub farm that stage 5 already removes on length,
  and measuring dedup on raw text would count that win twice. ``--no-quality`` measures the other
  way, deliberately.

    python scripts/dedup.py --source fineweb2-urd_Arab --limit 20000 --sample-rate 0.02
    python scripts/dedup.py --source fineweb2-urd_Arab --source urdu-wikipedia --limit 20000
    python scripts/dedup.py --source urdu-wikipedia --limit 20000 --variant raw
    python scripts/dedup.py --source roman-urdu-parl --split train --limit 200000

Requires the `[data]` extra for parquet sources.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Urdu on a Windows console is cp1252 by default, which raises rather than mangles.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from ravaan.data.dedup import DedupConfig, ExactDeduplicator  # noqa: E402
from ravaan.data.encoding import EncodingConfig, EncodingLog, validate_text  # noqa: E402
from ravaan.data.langid import LangIDConfig, LangIDLog, classify  # noqa: E402
from ravaan.data.normalization import NormalizationConfig, normalize_text  # noqa: E402
from ravaan.data.pii import PIIConfig, PIILog, redact, redact_text  # noqa: E402
from ravaan.data.quality import QualityConfig, QualityLog, check  # noqa: E402
from ravaan.data.shards import LAYOUTS, ShardReader  # noqa: E402


class Pipeline:
    """Stages 2→5 over a set of readers, yielding what reaches stage 6.

    Deterministic and stateless per document, so the two passes see the same text — which is what
    lets phase 2 recompute rather than hold a normalized corpus in memory. The stage 2–5 logs are
    filled on the first pass only; running them twice would double every count in the manifest.

    Stage 4 runs through :func:`normalize_text`, the fast path, and is not logged here: the
    per-rule counts are `scripts/probe.py`'s output, and paying 1.6× for them on both passes would
    buy a second copy of a number that is already committed.
    """

    def __init__(self, readers: list[ShardReader], *, quality: bool, urdu_side: bool) -> None:
        self.readers = readers
        self.quality = quality
        self.urdu_side = urdu_side
        self.encoding_config = EncodingConfig()
        self.langid_config = LangIDConfig()
        self.normalization_config = NormalizationConfig()
        self.stage2 = EncodingLog(config=self.encoding_config)
        self.stage3 = LangIDLog(config=self.langid_config)
        self.stage5: dict[str, QualityLog] = {}
        self.pii_config = PIIConfig()
        self.pii = PIILog(config=self.pii_config)
        self.logging = True

    def _redact(self, text: str) -> str:
        """PRD §6.3's PII pass. Logged on the first pass only, like every other stage here.

        Unlike stage 4 — whose per-rule counts are `scripts/probe.py`'s output — the counts are
        taken on the corpus pass rather than from a sample, because "N phone numbers and M email
        addresses removed" is a claim the release makes about the corpus, not a diagnostic.
        """
        if not self.logging:
            return redact_text(text, self.pii_config)
        result = redact(text, self.pii_config)
        self.pii.add(result)
        return result.text

    def _quality_config(self, source: str) -> QualityConfig:
        config = QualityConfig()
        if LAYOUTS.get(source) and LAYOUTS[source].unit == "sentence":
            config = config.for_sentences()
        if source not in self.stage5:
            self.stage5[source] = QualityLog(config=config)
        return config

    def __iter__(self) -> Iterator[tuple[str, str, str, str]]:
        """``(doc_id, normalized, raw, source)`` for every document reaching stage 6."""
        for reader in self.readers:
            for doc in reader:
                # Roman-Urdu-Parl's warning in PRD §6.2 is about the *Urdu* side: 6.37M pairs
                # collapse to ~1.09M unique Urdu sentences. Deduplicating the Roman column would
                # answer a different question than the one §6.1's budget depends on.
                text = doc.meta.get("Urdu text") if self.urdu_side else doc.text
                if not text:
                    continue
                checked = validate_text(text, self.encoding_config)
                if self.logging:
                    self.stage2.add(checked)
                if not checked.accepted:
                    continue
                repaired = checked.text or ""
                result = classify(repaired, self.langid_config)
                if self.logging:
                    self.stage3.add(result)
                normalized = normalize_text(repaired, self.normalization_config)
                if self.quality:
                    quality_config = self._quality_config(doc.source)
                    verdict = check(
                        normalized,
                        quality_config,
                        label=result.label,
                        scripts=result.scripts,
                        letters=result.letters,
                    )
                    if self.logging:
                        self.stage5[doc.source].add(verdict)
                    if not verdict.accepted:
                        continue
                # PRD §6.3's PII pass sits here, between stage 5 and stage 6: stage 5's
                # thresholds were validated against unredacted text, and every hash from stage 6
                # onward must be over the text the frozen corpus actually contains. `raw` below
                # is the pre-normalization string and feeds the alternate exact-dedup hash only;
                # it is measured, never written. See reports/pii.md §2.
                normalized = self._redact(normalized)
                yield doc.doc_id, normalized, repaired, doc.source
        self.logging = False


def _parse_source(spec: str, default_rate: float | None) -> tuple[str, float | None]:
    """``"name"`` or ``"name=0.2"`` -> ``(name, rate)``."""
    if "=" not in spec:
        return spec, default_rate
    name, _, raw = spec.partition("=")
    rate = float(raw)
    if not 0.0 < rate <= 1.0:
        raise SystemExit(f"--source {spec}: rate must be in (0, 1], got {rate}")
    return name, None if rate == 1.0 else rate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        metavar="NAME[=RATE]",
        help="source name from data/manifest.json; repeat to measure cross-source duplication. "
        "An optional per-source sampling rate overrides --sample-rate for that source — index one "
        "source completely and sample the other and a shared document is found with probability "
        "RATE rather than RATE^2, which is what makes cross-source overlap measurable without a "
        "full pass over the larger source (see --sample-rate)",
    )
    parser.add_argument("-m", "--manifest", default="data/manifest.json")
    parser.add_argument("--split", help="restrict to one split")
    parser.add_argument("--limit", type=int, default=20_000, help="documents per source")
    parser.add_argument(
        "--sample-rate",
        type=float,
        help="stable per-document sampling rate, for every source without its own. **A sampled "
        "pass cannot measure a duplicate rate**: a pair survives sampling at rate r with "
        "probability r^2, so 0.02 under-reports by 2,500x. Use it only for cross-source overlap "
        "against a completely-indexed source, or for a smoke test",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--config", help="stage-6 config JSON (default: shipped defaults)")
    parser.add_argument(
        "--variant",
        choices=("normalized", "raw"),
        help="which hash decides; the other is measured either way",
    )
    parser.add_argument(
        "--no-quality",
        action="store_true",
        help="index everything stage 3 kept, not only stage 5's survivors — double-counts the "
        "template stubs stage 5 already removes on length",
    )
    parser.add_argument(
        "--urdu-side",
        action="store_true",
        help="dedup the Urdu column of a parallel source (PRD §6.2's 6.37M -> ~1.09M warning)",
    )
    parser.add_argument(
        "--no-paragraphs",
        action="store_true",
        help="skip the line index — it is three dicts per distinct line and a full FineWeb2 shard "
        "produces ~12M of them",
    )
    parser.add_argument(
        "--index-only",
        action="store_true",
        help="stop after phase 1. The whole group structure — duplicate counts, largest groups, "
        "the raw-vs-normalized comparison and all cross-source overlap — is known once indexing "
        "finishes; phase 2 only adds the per-document verdicts and the character accounting. "
        "Halves the cost of a full-shard pass when the question is about groups",
    )
    parser.add_argument("--check-ids", nargs="+", help="report the fate of these document ids")
    parser.add_argument("--removals", help="write removed document ids here, one per line")
    parser.add_argument("--examples", type=int, default=10, help="duplicate groups to print")
    parser.add_argument("--json", help="write the full report here")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    config = DedupConfig.from_json_file(args.config) if args.config else DedupConfig()
    overrides: dict = {}
    if args.variant:
        overrides["variant"] = args.variant
    if args.no_paragraphs:
        overrides["paragraph_mode"] = "off"
    if overrides:
        config = DedupConfig.from_dict({**config.to_dict(), **overrides})

    sources = [_parse_source(spec, args.sample_rate) for spec in args.source]
    readers = [
        ShardReader.from_manifest(
            name,
            manifest_path=args.manifest,
            split=args.split,
            limit=args.limit,
            sample_rate=rate,
            seed=args.seed,
        )
        for name, rate in sources
    ]
    for (name, rate), reader in zip(sources, readers, strict=True):
        print(
            f"reading {name}: plan {reader.plan_fingerprint()} over {len(reader.files)} file(s)"
            + (f", sampled at {rate}" if rate else ""),
            file=sys.stderr,
        )

    pipeline = Pipeline(readers, quality=not args.no_quality, urdu_side=args.urdu_side)
    index = ExactDeduplicator(config)

    print("phase 1: indexing", file=sys.stderr)
    for doc_id, normalized, raw, source in pipeline:
        index.index(doc_id, normalized, raw=raw, source=source)
    index.seal()
    print(
        f"  {index.log.indexed:,} documents, {index.distinct_documents:,} distinct, "
        f"{index.log.duplicate_groups:,} duplicate groups",
        file=sys.stderr,
    )

    removed: list[str] = []
    snippets: dict[str, str] = {}
    checked: dict[str, dict] = {}
    tracked = index.tracked_groups

    if args.index_only:
        print("phase 2: skipped (--index-only)", file=sys.stderr)
    else:
        print("phase 2: deciding", file=sys.stderr)
        for doc_id, normalized, raw, source in pipeline:
            verdict = index.decide(doc_id, normalized, raw=raw, source=source)
            if not verdict.kept:
                removed.append(doc_id)
            if verdict.group in tracked and verdict.group not in snippets:
                snippets[verdict.group] = normalized[:300]
            if args.check_ids and doc_id in args.check_ids:
                checked[doc_id] = {**verdict.to_dict(), "chars": len(normalized)}

    payload = index.to_dict()
    if args.index_only:
        # Everything below is a phase-2 measurement and would otherwise be reported as a
        # confident zero. A run that did not count characters must not publish a character count.
        payload["phase2_skipped"] = True
        for key in (
            "documents", "documents_kept", "documents_removed", "keep_rate",
            "chars_in", "chars_kept", "char_keep_rate", "by_source", "kept_by_source",
            "removed_by_source", "removed_cross_source_by_source", "paragraph_units",
            "paragraph_distinct", "paragraph_duplicate_units", "paragraph_chars",
            "paragraph_chars_duplicated", "paragraph_chars_removable",
            "paragraph_removable_share", "paragraph_documents_changed", "paragraphs_removed",
            "paragraph_chars_removed", "paragraph_documents_emptied",
        ):
            payload.pop(key, None)
    payload["sources"] = args.source
    payload["limit"] = args.limit
    payload["sample_rate"] = args.sample_rate
    payload["seed"] = args.seed
    payload["quality_filtered"] = not args.no_quality
    payload["stage2_encoding"] = pipeline.stage2.to_dict()
    payload["stage3_langid"] = pipeline.stage3.to_dict()
    payload["stage5_quality"] = {s: log.to_dict() for s, log in sorted(pipeline.stage5.items())}
    payload["pii"] = pipeline.pii.to_dict()
    for group in payload["top_groups"]:
        group["text"] = snippets.get(group["group"], "")

    log = index.log
    if args.index_only:
        print(
            f"\nstage 6 (group structure only): {log.indexed:,} indexed, "
            f"{index.distinct_documents:,} distinct",
            file=sys.stderr,
        )
    else:
        print(
            f"\nstage 6: kept {log.documents_kept:,}/{log.documents:,} = "
            f"{100 * log.keep_rate:.2f}% of documents, "
            f"{100 * log.char_keep_rate:.2f}% of characters",
            file=sys.stderr,
        )
    print(
        f"  {log.duplicate_groups:,} duplicate groups, largest {log.largest_group:,}, "
        f"{log.duplicate_documents:,} documents removed",
        file=sys.stderr,
    )
    # The Finding F number. Both are counted on the same pass over the same documents, so the
    # difference is stage 4 and nothing else.
    print(
        f"  deciding on {config.variant}: {log.duplicate_documents:,} removed; "
        f"hashing {config.alternate_variant} instead would have removed "
        f"{log.alternate_duplicate_documents:,}",
        file=sys.stderr,
    )
    if log.cross_source_groups:
        print(f"  cross-source groups: {log.cross_source_groups:,}", file=sys.stderr)
        for pair, count in sorted(log.cross_source_pairs.items()):
            print(f"    {pair:<44} {count:>7,}", file=sys.stderr)
    for source in sorted(log.by_source):
        seen = log.by_source[source]
        cross = log.removed_cross_source_by_source[source]
        print(
            f"  {source:<24} {log.kept_by_source[source]:>8,}/{seen:<8,} "
            f"= {100 * log.kept_by_source[source] / seen:.2f}% kept  "
            f"({log.removed_by_source[source] - cross:,} internal + {cross:,} cross-source)",
            file=sys.stderr,
        )

    if config.paragraph_mode != "off" and not args.index_only:
        print(
            f"\n  paragraph level (measured over survivors, removing nothing): "
            f"{log.paragraph_units:,} lines, {log.paragraph_distinct:,} distinct; "
            f"{100 * log.paragraph_removable_share:.2f}% of line characters are a repeat of "
            f"another document's line",
            file=sys.stderr,
        )

    print("\n  largest duplicate groups", file=sys.stderr)
    for group in payload["top_groups"][: args.examples]:
        print(
            f"    {group['group']}  x{group['size']:<6} {','.join(group['sources']) or '?'}\n"
            f"      kept {group['kept'] or '?'}  e.g. {', '.join(group['duplicates'][:2])}\n"
            f"      {group['text'][:160]!r}",
            file=sys.stderr,
        )

    if args.check_ids:
        payload["checked_ids"] = checked
        print("\n  requested documents", file=sys.stderr)
        for doc_id in args.check_ids:
            record = checked.get(doc_id)
            if record is None:
                print(f"    {doc_id:<28} not read in this sample", file=sys.stderr)
            else:
                print(
                    f"    {doc_id:<28} kept={record['kept']} group={record['group']} "
                    f"size={record['group_size']} chars={record['chars']}",
                    file=sys.stderr,
                )

    if args.removals:
        Path(args.removals).write_text(
            "".join(f"{doc_id}\n" for doc_id in removed), encoding="utf-8", newline="\n"
        )
        print(f"\nwrote {len(removed):,} removed ids to {args.removals}", file=sys.stderr)

    report = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.json:
        Path(args.json).write_text(report + "\n", encoding="utf-8", newline="\n")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
