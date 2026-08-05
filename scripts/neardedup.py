#!/usr/bin/env python
"""Run pipeline stages 2→7 over real sources and report what near-dedup actually clusters.

The third driver, after `scripts/probe.py` (stages 2→5) and `scripts/dedup.py` (stages 2→6). Stage
7 needs its own for the same reason stage 6 did — it is not a function of a single document — plus
one that is new here: **it decides on an estimate**, so the run has to hand back the evidence the
threshold was chosen from, not just the verdicts it produced.

Four questions it exists to answer:

* **Does stage 7 find the population stage 8 needs it to have found?** Finding L: Urdu Wikipedia
  articles also sit inside FineWeb2 as crawled HTML — processed wikitext against a rendered page,
  never byte-identical, which is why stage 6 found exactly zero of them. ``--host-filter`` pulls
  that population out of the shard directly instead of hoping a sample lands on it.
* **Is it inert on the primary source, as Finding H predicts?** FineWeb2 removed 31.02% of
  ``urd_Arab`` by its own MinHash pass before we saw it, so the honest expectation is "assertion,
  not filter" — the fourth stage in a row for which that is the true report.
* **Where is the threshold?** ``--sweep`` re-clusters at several thresholds from one pass, and
  ``--pairs-out`` writes the measured pairs to read. Session 6's lesson is that a threshold is
  moved by documents, not chosen from a distribution.
* **Is the win real or already counted?** Stage 7 runs on **stage 6's survivors** by default.
  Finding J measured what skipping that does one stage earlier: 99.6% of the apparent dedup win on
  Wikipedia was stage 5's length floor counted twice. Every exact duplicate is also a near
  duplicate at J = 1.0, so a stage 7 run on pre-stage-6 text claims stage 6's removals as its own.
  ``--no-exact-dedup`` measures the other way, deliberately.

    python scripts/neardedup.py --source urdu-wikipedia --limit 0
    python scripts/neardedup.py --source urdu-wikipedia --source fineweb2-urd_Arab \
        --host-filter fineweb2-urd_Arab=wikipedia --limit 0        # Finding L's acceptance test
    python scripts/neardedup.py --source fineweb2-urd_Arab --limit 200000 --sweep 0.6 0.7 0.8 0.9

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
from ravaan.data.exclusions import write_exclusions  # noqa: E402
from ravaan.data.langid import LangIDConfig, LangIDLog, classify  # noqa: E402
from ravaan.data.minhash import MinHashConfig, MinHashDeduplicator  # noqa: E402
from ravaan.data.normalization import NormalizationConfig, normalize_text  # noqa: E402
from ravaan.data.pii import PIIConfig, PIILog, redact, redact_text  # noqa: E402
from ravaan.data.quality import QualityConfig, QualityLog, check  # noqa: E402
from ravaan.data.shards import LAYOUTS, ShardReader  # noqa: E402


class Pipeline:
    """Stages 2→5 over a set of readers, yielding what reaches stage 6.

    The same chain `scripts/dedup.py` runs, with one addition: an optional per-source substring
    filter on the ``url`` column, applied *before* any stage. It exists for Finding L. The wiki-host
    documents are 0.154% of FineWeb2 shard 001, so reaching them by sampling means reading the
    shard many times over; naming them costs one pass and answers the question exactly.
    """

    def __init__(
        self,
        readers: list[ShardReader],
        *,
        quality: bool,
        urdu_side: bool,
        host_filters: dict[str, str],
    ) -> None:
        self.readers = readers
        self.quality = quality
        self.urdu_side = urdu_side
        self.host_filters = host_filters
        self.encoding_config = EncodingConfig()
        self.langid_config = LangIDConfig()
        self.normalization_config = NormalizationConfig()
        self.stage2 = EncodingLog(config=self.encoding_config)
        self.stage3 = LangIDLog(config=self.langid_config)
        self.stage5: dict[str, QualityLog] = {}
        self.filtered_out: dict[str, int] = {}
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
                wanted = self.host_filters.get(doc.source)
                if wanted and wanted not in str(doc.meta.get("url", "")):
                    # Counted on the first pass only, like the stage 2-5 logs above it. Stage 6
                    # reads the corpus twice, and a filter counter that accumulated across both
                    # would report a source as twice its own size.
                    if self.logging:
                        self.filtered_out[doc.source] = self.filtered_out.get(doc.source, 0) + 1
                    continue
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
                # onward must be over the text the frozen corpus actually contains. See
                # reports/pii.md §2.
                normalized = self._redact(normalized)
                yield doc.doc_id, normalized, repaired, doc.source
        self.logging = False


def _parse_pair(spec: str, what: str) -> tuple[str, str]:
    if "=" not in spec:
        raise SystemExit(f"--{what} needs NAME=VALUE, got {spec!r}")
    name, _, value = spec.partition("=")
    return name, value


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
        help="source name from data/manifest.json; repeat to measure cross-source clustering. "
        "An optional per-source sampling rate overrides --sample-rate for that source",
    )
    parser.add_argument("-m", "--manifest", default="data/manifest.json")
    parser.add_argument("--split", help="restrict to one split")
    parser.add_argument(
        "--limit", type=int, default=20_000, help="documents per source; 0 for no limit"
    )
    parser.add_argument(
        "--sample-rate",
        type=float,
        help="stable per-document sampling rate. **A sampled pass cannot measure a duplicate "
        "rate** (Finding G): a pair survives sampling at rate r with probability r^2. Near-dedup "
        "is a pair statistic exactly as exact dedup is, so this carries the same warning — use it "
        "for cross-source work against a completely-indexed source, or for a smoke test",
    )
    parser.add_argument(
        "--host-filter",
        action="append",
        default=[],
        metavar="NAME=SUBSTRING",
        help="keep only documents of NAME whose url contains SUBSTRING. Finding L's acceptance "
        "test is `fineweb2-urd_Arab=wikipedia`: 2,388 documents in shard 001 come from wiki hosts "
        "and not one is byte-identical to its counterpart in the wikimedia dump",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--config", help="stage-7 config JSON (default: shipped defaults)")
    parser.add_argument("--threshold", type=float, help="override similarity_threshold")
    parser.add_argument("--shingle-size", type=int, help="override shingle_size")
    parser.add_argument("--shingle-unit", choices=("word", "char"), help="override shingle_unit")
    parser.add_argument(
        "--bands",
        type=int,
        help="override the LSH banding, with --rows; bands * rows must equal num_bins. The shipped "
        "(16, 8) puts the S-curve's inflection at 0.707 and has only 6%% recall at J = 0.5, so a "
        "run asking about the 0.5-0.7 region needs (32, 4) — inflection 0.420 — or it measures the "
        "bands rather than the corpus",
    )
    parser.add_argument("--rows", type=int, help="override the LSH rows per band, with --bands")
    parser.add_argument(
        "--retain-above",
        type=float,
        help="keep measured pairs down to this similarity, independently of the removal threshold. "
        "The two are separate questions: what stage 7 *deletes* is a corpus decision, what it "
        "*measures* is the evidence a later decision gets made on. Finding L's asymmetric pairs "
        "sit well below any sane removal threshold and still have to be visible",
    )
    parser.add_argument(
        "--sweep",
        nargs="+",
        type=float,
        help="also report clustering at these thresholds, exactly, from the same pass",
    )
    parser.add_argument(
        "--no-quality",
        action="store_true",
        help="index everything stage 3 kept, not only stage 5's survivors",
    )
    parser.add_argument(
        "--no-exact-dedup",
        action="store_true",
        help="skip stage 6 — near-dedup then re-counts every exact duplicate as a near one, which "
        "is Finding J's double-count one stage on. For the comparison run, not for a result",
    )
    parser.add_argument(
        "--urdu-side",
        action="store_true",
        help="dedup the Urdu column of a parallel source (PRD §6.2's 6.37M -> ~1.09M warning)",
    )
    parser.add_argument("--check-ids", nargs="+", help="report the fate of these document ids")
    parser.add_argument(
        "--check-pairs",
        nargs="+",
        metavar="ID_A=ID_B",
        help="report the measured similarity and containment of these named pairs, whether or not "
        "banding proposed them — Finding I's four stubs are checked this way",
    )
    parser.add_argument("--removals", help="write removed document ids here, one per line")
    parser.add_argument("--pairs-out", help="write every measured pair here as JSONL, to read")
    parser.add_argument("--examples", type=int, default=10, help="clusters to print")
    parser.add_argument("--json", help="write the full report here")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    config = MinHashConfig.from_json_file(args.config) if args.config else MinHashConfig()
    overrides: dict = {}
    if args.threshold is not None:
        overrides["similarity_threshold"] = args.threshold
        # A threshold below the retention floor would make --sweep silently incomplete, and the
        # config refuses it. Drop the floor with the threshold rather than making the caller do it.
        overrides["retain_pairs_above"] = min(config.retain_pairs_above, args.threshold)
    if args.retain_above is not None:
        overrides["retain_pairs_above"] = args.retain_above
    if args.shingle_size is not None:
        overrides["shingle_size"] = args.shingle_size
    if args.shingle_unit is not None:
        overrides["shingle_unit"] = args.shingle_unit
    if (args.bands is None) != (args.rows is None):
        raise SystemExit("--bands and --rows must be given together — their product is num_bins")
    if args.bands is not None:
        overrides["bands"] = args.bands
        overrides["rows"] = args.rows
    if overrides:
        config = MinHashConfig.from_dict({**config.to_dict(), **overrides})

    host_filters = dict(_parse_pair(spec, "host-filter") for spec in args.host_filter)
    sources = [_parse_source(spec, args.sample_rate) for spec in args.source]
    readers = [
        ShardReader.from_manifest(
            name,
            manifest_path=args.manifest,
            split=args.split,
            limit=args.limit or None,
            sample_rate=rate,
            seed=args.seed,
        )
        for name, rate in sources
    ]
    for (name, rate), reader in zip(sources, readers, strict=True):
        print(
            f"reading {name}: plan {reader.plan_fingerprint()} over {len(reader.files)} file(s)"
            + (f", sampled at {rate}" if rate else "")
            + (f", url contains {host_filters[name]!r}" if name in host_filters else ""),
            file=sys.stderr,
        )

    pipeline = Pipeline(
        readers,
        quality=not args.no_quality,
        urdu_side=args.urdu_side,
        host_filters=host_filters,
    )
    index = MinHashDeduplicator(config)
    exact: ExactDeduplicator | None = None
    # Stage 6's removals, kept so `--removals` can write one list for the pass rather than only
    # stage 7's half. A stage-9 run handed only the near-duplicates would measure its pool over
    # every exact duplicate this pass had already decided to drop.
    exact_removed: list[str] = []

    if args.no_exact_dedup:
        print("stage 6: skipped (--no-exact-dedup)", file=sys.stderr)
        for doc_id, normalized, _raw, source in pipeline:
            index.index(doc_id, normalized, source=source)
    else:
        # Stage 6 is two-phase by construction, and stage 7 sketches during its second pass rather
        # than in a third: the survivors are known there, and sketching is the expensive half.
        exact = ExactDeduplicator(DedupConfig.from_dict({**DedupConfig().to_dict(),
                                                         "paragraph_mode": "off"}))
        print("stage 6 phase 1: indexing", file=sys.stderr)
        for doc_id, normalized, raw, source in pipeline:
            exact.index(doc_id, normalized, raw=raw, source=source)
        exact.seal()
        print(
            f"  {exact.log.indexed:,} documents, {exact.distinct_documents:,} distinct, "
            f"{exact.log.duplicate_groups:,} exact duplicate groups",
            file=sys.stderr,
        )
        print("stage 6 phase 2 + stage 7 sketching", file=sys.stderr)
        for doc_id, normalized, raw, source in pipeline:
            if exact.decide(doc_id, normalized, raw=raw, source=source).kept:
                index.index(doc_id, normalized, source=source)
            else:
                exact_removed.append(doc_id)

    print(
        f"stage 7: sketching done — {index.log.indexed:,} documents "
        f"({index.log.skipped_short:,} below min_shingles), banding",
        file=sys.stderr,
    )
    index.build()

    payload = index.to_dict()
    payload["sources"] = args.source
    payload["limit"] = args.limit
    payload["sample_rate"] = args.sample_rate
    payload["host_filters"] = host_filters
    payload["host_filtered_out"] = pipeline.filtered_out
    payload["seed"] = args.seed
    payload["quality_filtered"] = not args.no_quality
    payload["exact_deduplicated"] = not args.no_exact_dedup
    payload["stage2_encoding"] = pipeline.stage2.to_dict()
    payload["stage3_langid"] = pipeline.stage3.to_dict()
    payload["stage5_quality"] = {s: log.to_dict() for s, log in sorted(pipeline.stage5.items())}
    payload["pii"] = pipeline.pii.to_dict()
    if exact is not None:
        payload["stage6_exact"] = exact.to_dict()

    log = index.log
    print(
        f"\nstage 7: kept {log.documents_kept:,}/{log.indexed:,} = "
        f"{100 * log.keep_rate:.2f}% of documents, {100 * log.char_keep_rate:.2f}% of characters",
        file=sys.stderr,
    )
    print(
        f"  {log.clusters:,} clusters, largest {log.largest_cluster:,}, "
        f"{log.duplicate_documents:,} documents removed",
        file=sys.stderr,
    )
    print(
        f"  banding proposed {log.candidate_pairs:,} candidate pairs at threshold "
        f"{config.band_threshold:.3f}; {log.verified_pairs:,} verified at "
        f"{config.similarity_threshold:.2f} (precision {log.band_precision:.3f}); "
        f"{log.retained_pairs:,} retained for the sweep",
        file=sys.stderr,
    )
    if log.eligible:
        print(f"  mean shingles per eligible document: {log.shingles_total / log.eligible:.1f}",
              file=sys.stderr)
    if log.cross_source_clusters:
        print(f"  cross-source clusters: {log.cross_source_clusters:,}", file=sys.stderr)
        for pair, count in sorted(log.cross_source_pairs.items()):
            print(f"    {pair:<44} {count:>7,}", file=sys.stderr)
    else:
        print("  cross-source clusters: 0", file=sys.stderr)
    for source in sorted(log.by_source):
        seen = log.by_source[source]
        cross = log.removed_cross_source_by_source[source]
        print(
            f"  {source:<24} {log.kept_by_source[source]:>8,}/{seen:<8,} "
            f"= {100 * log.kept_by_source[source] / seen:.2f}% kept  "
            f"({log.removed_by_source[source] - cross:,} internal + {cross:,} cross-source)",
            file=sys.stderr,
        )

    print("\n  similarity of retained pairs", file=sys.stderr)
    for band, count in sorted(log.similarity_histogram.items(), reverse=True):
        contained = log.containment_histogram.get(band, 0)
        print(f"    {band}  jaccard {count:>8,}   containment {contained:>8,}", file=sys.stderr)

    if payload["top_clusters"]:
        print("\n  largest clusters", file=sys.stderr)
        for cluster in payload["top_clusters"][: args.examples]:
            print(
                f"    #{cluster['cluster']:<5} x{cluster['size']:<6} "
                f"{','.join(cluster['sources']) or '?'}\n"
                f"      kept {cluster['kept'] or '?'}  e.g. {', '.join(cluster['duplicates'][:2])}",
                file=sys.stderr,
            )

    if args.sweep:
        payload["sweep"] = index.sweep(args.sweep)
        print("\n  threshold sweep (exact, from the retained pairs of this one pass)",
              file=sys.stderr)
        print(f"    {'thr':>5} {'pairs':>10} {'clusters':>10} {'removed':>10} {'largest':>8}",
              file=sys.stderr)
        for row in payload["sweep"]:
            print(
                f"    {row['threshold']:>5.2f} {row['verified_pairs']:>10,} "
                f"{row['clusters']:>10,} {row['duplicate_documents']:>10,} "
                f"{row['largest_cluster']:>8,}",
                file=sys.stderr,
            )

    if args.check_ids:
        checked = {}
        for doc_id in args.check_ids:
            try:
                checked[doc_id] = index.verdict(doc_id).to_dict()
            except KeyError:
                checked[doc_id] = {"doc_id": doc_id, "note": "not read in this pass"}
        payload["checked_ids"] = checked
        print("\n  requested documents", file=sys.stderr)
        for doc_id, record in checked.items():
            print(f"    {doc_id:<32} {record}", file=sys.stderr)

    if args.check_pairs:
        pairs = []
        print("\n  requested pairs", file=sys.stderr)
        for spec in args.check_pairs:
            left, right = _parse_pair(spec, "check-pairs")
            try:
                measured = _measure_pair(index, left, right)
            except KeyError as error:
                print(f"    {left} vs {right}: {error}", file=sys.stderr)
                continue
            pairs.append(measured)
            print(
                f"    {left} vs {right}: jaccard {measured['similarity']:.3f}  "
                f"containment {measured['containment']:.3f}  "
                f"shingles {measured['left_shingles']}/{measured['right_shingles']}",
                file=sys.stderr,
            )
        payload["checked_pairs"] = pairs

    if args.removals:
        # Stage 7's removals plus stage 6's, when stage 6 ran here — they are one list because
        # they are one pass, and a stage-9 run handed only the near-duplicates would put every
        # exact duplicate back into the pool it is measuring.
        removed = list(index.removed_ids())
        if exact is not None:
            removed.extend(sorted(exact_removed))
        written = write_exclusions(
            args.removals,
            removed,
            stage="6+7" if exact is not None else "7",
            readers=readers,
        )
        print(f"\nwrote {written:,} removed ids to {args.removals}", file=sys.stderr)

    if args.pairs_out:
        with Path(args.pairs_out).open("w", encoding="utf-8", newline="\n") as handle:
            for example in index.pair_examples():
                handle.write(json.dumps(example.to_dict(), ensure_ascii=False) + "\n")
        print(f"wrote measured pair examples to {args.pairs_out}", file=sys.stderr)

    report = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.json:
        Path(args.json).write_text(report + "\n", encoding="utf-8", newline="\n")
    else:
        print(report)
    return 0


def _measure_pair(index: MinHashDeduplicator, left: str, right: str) -> dict:
    """Similarity of two named documents, whether or not banding ever proposed them.

    Finding I's four stubs are the reason this exists: the interesting question about them is what
    their similarity *is*, and a pair that never became a candidate has no entry anywhere in the
    normal reporting path. Reaching into the sketches directly is the honest way to ask.
    """
    from ravaan.data.minhash import _agreement, containment_from_jaccard

    positions = []
    for doc_id in (left, right):
        position = index._position.get(doc_id)
        if position is None:
            raise KeyError(f"{doc_id} was not read in this pass")
        if not index._sigs[position]:
            raise KeyError(f"{doc_id} is below min_shingles and was never sketched")
        positions.append(position)
    similarity = _agreement(*(index._sigs[p] for p in positions)) / index.config.num_bins
    sizes = [index._sizes[p] for p in positions]
    return {
        "left": left,
        "right": right,
        "similarity": similarity,
        "containment": containment_from_jaccard(similarity, *sizes),
        "left_shingles": sizes[0],
        "right_shingles": sizes[1],
    }


if __name__ == "__main__":
    raise SystemExit(main())
