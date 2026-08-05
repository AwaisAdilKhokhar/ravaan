#!/usr/bin/env python
"""Run pipeline stages 2→8 over real sources and report what the eval sets actually touch.

The fourth driver, after `scripts/probe.py` (2→5), `scripts/dedup.py` (2→6) and
`scripts/neardedup.py` (2→7). Stage 8 needs its own for a reason none of the others had: **it is
the only stage whose failure is silent.** A bad threshold at stage 5 deletes documents somebody
notices; a stage 8 that misses contamination removes nothing, raises nothing, and hands back a
clean corpus. The cost arrives months later, in §8.2's evaluation numbers.

Four questions it exists to answer:

* **Is the Roman-Urdu-Parl reference split already inside its own train split?** PRD §6.2 warns the
  source is machine-produced and its 6.37M pairs collapse to ~1.09M unique Urdu sentences. If the
  test rows are also train rows, the transliteration chrF number in §4.5's secondary endpoints is
  measuring memorisation. This is the acceptance test, and it is asked of **both columns**, because
  a parallel corpus can leak on either side.
* **Which half of §6.3.8 fires, and on what?** Finding L measured the hash half returning a
  confident zero on the wiki path. The two halves are counted separately here for exactly that
  reason — a single "contaminated" total would hide which instrument was blind.
* **How much of a *test set* is compromised?** Not the same question as how many training documents
  were removed, and much the more important of the two. `eval_coverage` is that number.
* **Where should the threshold sit?** ``--sweep`` re-decides at other containments from the same
  pass, exactly, and ``--hits-out`` writes the measured overlaps to read. Session 6's lesson.

**Sampling is honest here, and this is the one stage where that is true of a cross-document
measurement.** Finding G forbids sampling stages 6 and 7 because a *pair* statistic sampled at rate
r is measured at r². Stage 8 is not a pair statistic: the eval side is indexed **whole** and only
the corpus side is sampled, so a contaminated document is detected with probability r, not r². Same
exception Finding G names for the cross-source case. The absolute count still scales by 1/r; the
rate does not need to.

    python scripts/decontaminate.py --eval roman-urdu-parl:test:char \\
        --source roman-urdu-parl --limit 200000 --both-columns
    python scripts/decontaminate.py --eval roman-urdu-parl:test:char \\
        --source urdu-wikipedia --source fineweb2-urd_Arab --limit 0

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

from dataclasses import replace  # noqa: E402

from ravaan.data.decontamination import (  # noqa: E402
    DecontaminationConfig,
    Decontaminator,
    EvalSetSpec,
)
from ravaan.data.dedup import DedupConfig, ExactDeduplicator  # noqa: E402
from ravaan.data.encoding import EncodingConfig, EncodingLog, validate_text  # noqa: E402
from ravaan.data.exclusions import ExclusionSet, write_exclusions  # noqa: E402
from ravaan.data.langid import LangIDConfig, LangIDLog, classify  # noqa: E402
from ravaan.data.normalization import NormalizationConfig, normalize_text  # noqa: E402
from ravaan.data.pii import PIIConfig, PIILog, redact, redact_text  # noqa: E402
from ravaan.data.quality import QualityConfig, QualityLog, check  # noqa: E402
from ravaan.data.shards import LAYOUTS, ShardReader  # noqa: E402
from ravaan.data.splits import pair_key  # noqa: E402

URDU_COLUMN = "Urdu text"


class Pipeline:
    """Stages 2→5 over a set of readers, yielding what reaches stage 8.

    The same chain the other drivers run, with one addition: ``columns="both"`` emits each row of a
    parallel source **twice**, as ``id#roman`` and ``id#urdu``. Roman-Urdu-Parl is the
    transliteration test set's own source, so contamination can arrive on either side, and a driver
    that read one column would clear the corpus on evidence from half of it.
    """

    def __init__(
        self,
        readers: list[ShardReader],
        *,
        quality: bool,
        columns: str,
        exclusions: ExclusionSet | None = None,
    ) -> None:
        self.readers = readers
        self.quality = quality
        self.columns = columns
        self.exclusions = exclusions or ExclusionSet()
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

    def _variants(self, doc) -> list[tuple[str, str]]:
        if self.columns == "urdu":
            return [(doc.doc_id, doc.meta.get(URDU_COLUMN) or "")]
        if self.columns == "both" and doc.meta.get(URDU_COLUMN):
            return [
                (f"{doc.doc_id}#roman", doc.text or ""),
                (f"{doc.doc_id}#urdu", doc.meta[URDU_COLUMN]),
            ]
        return [(doc.doc_id, doc.text or "")]

    def __iter__(self) -> Iterator[tuple[str, str, str, str]]:
        """``(doc_id, normalized, raw, source)`` for every document reaching stage 8."""
        for reader in self.readers:
            for doc in reader:
                # Checked on the *row* id, ahead of `_variants` and of stage 2. A parallel row
                # removed by stage 6 or 7 leaves as a row: its halves are one document to every
                # stage that budgets them (§6.1's "~500K deduplicated pairs"), and dropping one
                # column while keeping the other is how a pair stops being a pair.
                if self.exclusions.excludes(doc.doc_id):
                    continue
                for doc_id, text in self._variants(doc):
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
                    yield doc_id, normalized, repaired, doc.source
        self.logging = False


def _parse_eval(spec: str) -> tuple[str, str, str]:
    """``"roman-urdu-parl:test:char"`` -> ``(source, split, unit)``. Split and unit are optional."""
    parts = spec.split(":")
    if not parts[0]:
        raise SystemExit(f"--eval needs a source name, got {spec!r}")
    source = parts[0]
    split = parts[1] if len(parts) > 1 and parts[1] else "test"
    unit = parts[2] if len(parts) > 2 and parts[2] else ""
    if unit and unit not in ("word", "char"):
        raise SystemExit(f"--eval {spec}: unit must be 'word' or 'char', got {unit!r}")
    return source, split, unit


def _spec_for(name: str, source: str, unit: str) -> EvalSetSpec:
    """Build a test set's spec from its *declared layout*, not from its row lengths.

    Sentence-unit sources get :meth:`EvalSetSpec.for_sentences` — character shingles, a 25-shingle
    floor and a 0.90 containment threshold, all three moved by reading real hits. Deciding from the
    layout rather than from measured row length keeps the choice reproducible from the manifest,
    which is the same argument `shards.py` makes for declaring columns instead of detecting them.

    An explicit ``UNIT`` on the command line overrides the unit only; the companion thresholds stay
    with whichever variant the layout selected, because they were measured together.
    """
    layout = LAYOUTS.get(source)
    spec = EvalSetSpec(name=name)
    if layout is not None and layout.unit == "sentence":
        spec = spec.for_sentences()
    if unit and unit != spec.shingle_unit:
        spec = replace(spec, shingle_unit=unit)
    return spec


def _parse_eval_file(spec: str) -> tuple[Path, str, str]:
    """``"data/heldout.jsonl:heldout-wiki:word"`` -> ``(path, name, unit)``.

    A Windows drive letter is a colon too, so the split is from the right and bounded.
    """
    parts = spec.rsplit(":", 2)
    if len(parts) == 3 and parts[2] in ("word", "char", "sentences"):
        path, name, unit = parts[0], parts[1], parts[2]
    elif len(parts) >= 2 and parts[-1] in ("word", "char", "sentences"):
        path, name, unit = ":".join(parts[:-1]), "", parts[-1]
    elif len(parts) >= 2 and parts[-1] and not Path(spec).exists():
        path, name, unit = ":".join(parts[:-1]), parts[-1], ""
    else:
        path, name, unit = spec, "", ""
    resolved = Path(path)
    if not resolved.exists():
        raise SystemExit(f"--eval-file {spec}: no such file {resolved}")
    return resolved, name or resolved.stem, unit


def load_eval_files(
    index: Decontaminator, specs: list[str], *, limit: int | None, normalize: bool = False
) -> dict:
    """Index test sets that live in a file rather than in the acquisition manifest.

    Three of §8.2's five test sets are not manifest sources and never will be: the held-out native
    split is *produced* by stage 9, and the ~200 human-written transliteration pairs and ~300
    real-OCR lines are hand-built artifacts. Reading them here is what unblocks the second
    decontamination run — the one Finding L was actually about, where §8.2 draws held-out text from
    Urdu Wikipedia while the same articles sit in the training data as crawled FineWeb2 HTML.

    The text is taken as written. Stage 9 already emitted it post-stage-4, and normalizing twice
    would be harmless but claiming a pass that did not happen would not be, so
    ``--eval-file-normalize`` is explicit for the hand-built sets that have not been through it.

    **Redaction is not optional and is not behind that flag.** See :func:`load_eval_sets`.
    """
    loaded: dict[str, dict] = {}
    encoding_config = EncodingConfig()
    normalization_config = NormalizationConfig()
    pii_config = PIIConfig()

    for spec in specs:
        path, name, unit = _parse_eval_file(spec)
        eval_spec = EvalSetSpec(name=name)
        if unit == "sentences":
            eval_spec = eval_spec.for_sentences()
        elif unit:
            eval_spec = replace(eval_spec, shingle_unit=unit)
        index.add_eval_set(eval_spec)
        loaded[name] = {
            "source": str(path),
            "split": "file",
            "items": 0,
            **{k: v for k, v in eval_spec.to_dict().items() if k != "name"},
        }

        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle):
                if limit is not None and loaded[name]["items"] >= limit:
                    break
                if not line.strip():
                    continue
                record = json.loads(line)
                text = record.get("text") or ""
                if not text:
                    continue
                if normalize:
                    checked = validate_text(text, encoding_config)
                    if not checked.accepted:
                        continue
                    text = normalize_text(checked.text or "", normalization_config)
                text = redact_text(text, pii_config)
                index.add_eval_item(name, record.get("doc_id") or f"{name}:{line_number}", text)
                loaded[name]["items"] += 1
    return loaded


def load_eval_sets(
    index: Decontaminator,
    specs: list[str],
    *,
    manifest: str,
    limit: int | None,
    both_columns: bool,
) -> dict[str, dict]:
    """Index every test set through stages 2→4, and report what went in.

    Stage 5 is deliberately **not** run on the eval side. A test set is an instrument, not corpus:
    quality-filtering it would silently drop the items stage 8 is least able to afford to lose, and
    an eval item that stage 5 would have rejected is still contamination if it is in the training
    data. Stages 2 and 4 do run, because the eval sets must be normalized by the same pass as the
    corpus or the comparison measures the normalizer rather than the overlap.

    **The PII pass runs on this side too, and it is not optional.** Same argument one stage on: the
    corpus side is redacted before it is ever hashed, so a training document whose only overlap with
    an eval item is a phone number matches nothing — the hit disappears and the document stays in.
    There is no configuration in which redacting one side and not the other is correct, so there is
    no flag for it. Running it twice is free: §6.3's placeholders carry no digits and no letters
    precisely so that redaction is idempotent, which is what lets this be unconditional even for
    stage 9's held-out split, which arrives already redacted.
    """
    encoding_config = EncodingConfig()
    normalization_config = NormalizationConfig()
    pii_config = PIIConfig()
    loaded: dict[str, dict] = {}

    for spec in specs:
        source, split, unit = _parse_eval(spec)
        reader = ShardReader.from_manifest(source, manifest_path=manifest, split=split, limit=limit)
        layout = LAYOUTS.get(source)
        parallel = both_columns and layout is not None and URDU_COLUMN in layout.meta_columns

        names = []
        if parallel:
            names = [f"{source}-{split}-roman", f"{source}-{split}-urdu"]
        else:
            names = [f"{source}-{split}"]
        for name in names:
            eval_spec = _spec_for(name, source, unit)
            index.add_eval_set(eval_spec)
            loaded[name] = {
                "source": source,
                "split": split,
                "items": 0,
                **{k: v for k, v in eval_spec.to_dict().items() if k != "name"},
            }

        for doc in reader:
            variants = (
                [(names[0], doc.text or ""), (names[1], doc.meta.get(URDU_COLUMN) or "")]
                if parallel
                else [(names[0], doc.text or "")]
            )
            for name, text in variants:
                if not text:
                    continue
                checked = validate_text(text, encoding_config)
                if not checked.accepted:
                    continue
                normalized = redact_text(
                    normalize_text(checked.text or "", normalization_config), pii_config
                )
                index.add_eval_item(name, doc.doc_id, normalized)
                loaded[name]["items"] += 1
    return loaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--eval-file",
        action="append",
        default=[],
        metavar="PATH[:NAME][:UNIT]",
        help="test set from a JSONL file with a `text` field, e.g. stage 9's held-out split. UNIT "
        "is word (default), char, or `sentences` for the measured sentence trio of EvalSetSpec."
        "for_sentences(). This is how §8.2's three non-manifest test sets are indexed",
    )
    parser.add_argument(
        "--eval-file-normalize",
        action="store_true",
        help="run stages 2 and 4 over --eval-file text. Off by default because stage 9 emits "
        "already-normalized text; needed for the hand-built sets that have not been through it",
    )
    parser.add_argument(
        "--eval",
        action="append",
        default=[],
        metavar="SOURCE[:SPLIT[:UNIT]]",
        help="test set to decontaminate against, e.g. `roman-urdu-parl:test:char`. SPLIT defaults "
        "to 'test'; UNIT defaults to 'char' for sentence-unit sources and 'word' otherwise",
    )
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        metavar="NAME[=RATE]",
        help="training source to check; an optional per-source sampling rate overrides "
        "--sample-rate. Unlike stages 6 and 7, sampling is honest here — the eval side is indexed "
        "whole, so a contaminated document is found with probability r rather than r^2",
    )
    parser.add_argument("-m", "--manifest", default="data/manifest.json")
    parser.add_argument("--split", help="restrict the training sources to one split")
    parser.add_argument(
        "--limit", type=int, default=20_000, help="documents per source; 0 for no limit"
    )
    parser.add_argument(
        "--eval-limit", type=int, default=0, help="eval items per set; 0 for no limit"
    )
    parser.add_argument("--sample-rate", type=float, help="stable per-document sampling rate")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--config", help="stage-8 config JSON (default: shipped defaults)")
    parser.add_argument("--threshold", type=float, help="override containment_threshold")
    parser.add_argument(
        "--retain-above", type=float, help="keep measured hits down to this containment"
    )
    parser.add_argument(
        "--sweep",
        nargs="+",
        type=float,
        help="also report removals at these containment thresholds, exactly, from the same pass",
    )
    parser.add_argument(
        "--both-columns",
        action="store_true",
        help="read both columns of a parallel source, as `id#roman` and `id#urdu`. Roman-Urdu-Parl "
        "is the transliteration test set's own source and can leak on either side",
    )
    parser.add_argument(
        "--urdu-side", action="store_true", help="read only the Urdu column of a parallel source"
    )
    parser.add_argument(
        "--no-quality", action="store_true", help="check everything stage 3 kept, not stage 5's"
    )
    parser.add_argument(
        "--exact-dedup",
        action="store_true",
        help="run stage 6 first, so contamination is counted against distinct documents. Off by "
        "default: unlike stage 7, stage 8's verdict is per document and does not double-count a "
        "duplicate group, so the extra corpus pass buys only a cleaner denominator",
    )
    parser.add_argument(
        "--no-exact-match",
        action="store_true",
        help="switch off both halves of the exact match, to measure the fuzzy half alone",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="FILE",
        help="a removal list from an earlier stage; repeat for several. The freeze order puts "
        "stage 8 after stage 7, so its denominator should be the deduplicated corpus — a "
        "contamination rate measured over text stage 7 has already removed is a rate about a "
        "corpus nobody trains on. Each file's header is checked against this pass's read plan",
    )
    parser.add_argument("--removals", help="write contaminated document ids here, one per line")
    parser.add_argument("--hits-out", help="write every measured hit here as JSONL, to read")
    parser.add_argument("--examples", type=int, default=10, help="hits to print")
    parser.add_argument("--json", help="write the full report here")
    return parser


def _parse_source(spec: str, default_rate: float | None) -> tuple[str, float | None]:
    if "=" not in spec:
        return spec, default_rate
    name, _, raw = spec.partition("=")
    rate = float(raw)
    if not 0.0 < rate <= 1.0:
        raise SystemExit(f"--source {spec}: rate must be in (0, 1], got {rate}")
    return name, None if rate == 1.0 else rate


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    config = (
        DecontaminationConfig.from_json_file(args.config)
        if args.config
        else DecontaminationConfig()
    )
    overrides: dict = {}
    if args.threshold is not None:
        overrides["containment_threshold"] = args.threshold
        overrides["retain_hits_above"] = min(config.retain_hits_above, args.threshold)
    if args.retain_above is not None:
        overrides["retain_hits_above"] = args.retain_above
    if args.no_exact_match:
        overrides["exact_document_match"] = False
        overrides["exact_line_match"] = False
    if overrides:
        config = DecontaminationConfig.from_dict({**config.to_dict(), **overrides})

    if args.both_columns and args.urdu_side:
        raise SystemExit("--both-columns and --urdu-side are mutually exclusive")
    columns = "both" if args.both_columns else ("urdu" if args.urdu_side else "text")

    if not args.eval and not args.eval_file:
        raise SystemExit("at least one of --eval or --eval-file is required")

    index = Decontaminator(config)
    print("stage 8: indexing eval sets", file=sys.stderr)
    loaded = load_eval_sets(
        index,
        args.eval,
        manifest=args.manifest,
        limit=args.eval_limit or None,
        both_columns=args.both_columns or args.urdu_side,
    )
    loaded.update(
        load_eval_files(
            index,
            args.eval_file,
            limit=args.eval_limit or None,
            normalize=args.eval_file_normalize,
        )
    )
    index.seal()
    for name, record in sorted(loaded.items()):
        print(
            f"  {name:<36} {record['items']:>8,} items, {record['shingle_unit']} shingles",
            file=sys.stderr,
        )
    print(
        f"  {index.log.eval_items:,} items total, {index.log.eval_shingles:,} distinct shingles, "
        f"{index.log.eval_lines:,} indexed lines, "
        f"{index.log.eval_items_unmeasurable:,} below min_shingles (exact-only)",
        file=sys.stderr,
    )

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
            + (f", sampled at {rate}" if rate else ""),
            file=sys.stderr,
        )

    exclusions = ExclusionSet.load(args.exclude)
    try:
        coverage = exclusions.check(readers)
    except ValueError as error:  # an operator mistake, not a stack trace
        raise SystemExit(str(error)) from error
    if args.exclude:
        print(f"excluding {len(exclusions):,} documents removed by earlier stages", file=sys.stderr)
    for line in coverage.report():
        print(line, file=sys.stderr)

    pipeline = Pipeline(
        readers, quality=not args.no_quality, columns=columns, exclusions=exclusions
    )
    exact: ExactDeduplicator | None = None

    if args.exact_dedup:
        exact = ExactDeduplicator(
            DedupConfig.from_dict({**DedupConfig().to_dict(), "paragraph_mode": "off"})
        )
        print("stage 6 phase 1: indexing", file=sys.stderr)
        for doc_id, normalized, raw, source in pipeline:
            exact.index(doc_id, normalized, raw=raw, source=source)
        exact.seal()
        print("stage 6 phase 2 + stage 8", file=sys.stderr)
        for doc_id, normalized, raw, source in pipeline:
            if exact.decide(doc_id, normalized, raw=raw, source=source).kept:
                index.check(doc_id, normalized, source=source)
    else:
        print("stage 8: checking the corpus", file=sys.stderr)
        for doc_id, normalized, _raw, source in pipeline:
            index.check(doc_id, normalized, source=source)

    log = index.log
    payload = index.to_dict()
    payload["eval_sets_loaded"] = loaded
    payload["sources"] = args.source
    payload["limit"] = args.limit
    payload["sample_rate"] = args.sample_rate
    payload["seed"] = args.seed
    payload["columns"] = columns
    payload["quality_filtered"] = not args.no_quality
    payload["exact_deduplicated"] = args.exact_dedup
    payload["stage2_encoding"] = pipeline.stage2.to_dict()
    payload["stage3_langid"] = pipeline.stage3.to_dict()
    payload["stage5_quality"] = {s: q.to_dict() for s, q in sorted(pipeline.stage5.items())}
    payload["pii"] = pipeline.pii.to_dict()
    payload["exclusions"] = exclusions.to_dict()
    payload["exclusion_coverage"] = coverage.to_dict()
    for line in exclusions.summary():
        print(line, file=sys.stderr)
    if exact is not None:
        payload["stage6_exact"] = exact.to_dict()

    print(
        f"\nstage 8: kept {log.kept:,}/{log.checked:,} = {100 * log.keep_rate:.4f}% of documents, "
        f"{100 * log.char_keep_rate:.4f}% of characters",
        file=sys.stderr,
    )
    print(
        f"  {log.removed:,} contaminated documents removed "
        f"({100 * log.contamination_rate:.4f}% of what was checked)",
        file=sys.stderr,
    )
    if log.removed_by_reason:
        print("\n  which half of §6.3.8 fired", file=sys.stderr)
        for reason, count in sorted(log.removed_by_reason.items()):
            print(f"    {reason:<20} {count:>10,}", file=sys.stderr)

    print(
        "\n  eval coverage — the share of each TEST SET found in the training corpus",
        file=sys.stderr,
    )
    for name, record in sorted(log.eval_coverage().items()):
        print(
            f"    {name:<36} {record['items_found_in_corpus']:>8,}/{record['items']:<8,} "
            f"= {100 * record['share']:.4f}%",
            file=sys.stderr,
        )

    if log.by_source:
        print("\n  by training source", file=sys.stderr)
        for source in sorted(log.by_source):
            seen = log.by_source[source]
            removed = log.removed_by_source.get(source, 0)
            print(
                f"    {source:<28} {removed:>8,}/{seen:<10,} = {100 * removed / seen:.4f}% removed",
                file=sys.stderr,
            )

    if log.containment_histogram:
        print(
            "\n  containment of retained hits (jaccard beside it — Finding M's gap)",
            file=sys.stderr,
        )
        for band in sorted(log.containment_histogram, reverse=True):
            print(
                f"    {band}  containment {log.containment_histogram[band]:>9,}"
                f"   jaccard {log.jaccard_histogram.get(band, 0):>9,}",
                file=sys.stderr,
            )

    hits = index.hits()
    if hits:
        print("\n  strongest hits", file=sys.stderr)
        for hit in hits[: args.examples]:
            print(
                f"    {hit.eval_set}/{hit.eval_id} in {hit.doc_id}\n"
                f"      containment {hit.containment:.3f}  jaccard {hit.jaccard:.3f}  "
                f"shingles {hit.intersection}/{hit.eval_shingles} of eval, "
                f"{hit.doc_shingles} in doc" + (f"  [{hit.exact}]" if hit.exact else ""),
                file=sys.stderr,
            )

    if args.sweep:
        payload["sweep"] = index.sweep(args.sweep)
        print(
            "\n  containment sweep (exact, from the retained hits of this one pass)",
            file=sys.stderr,
        )
        for row in payload["sweep"]:
            if "note" in row:
                print(f"    {row['threshold']:>5.2f} {row['note']}", file=sys.stderr)
                continue
            items = sum(row["eval_items_hit"].values())
            print(
                f"    {row['threshold']:>5.2f} {row['documents_removed']:>10,} documents, "
                f"{items:>8,} eval items",
                file=sys.stderr,
            )

    if args.removals:
        cut = config.containment_threshold
        # Written as *row* ids, with any `#roman` / `#urdu` suffix removed by the same function
        # stage 9 splits on. This pass reads a parallel row as two documents because contamination
        # arrives on one side or the other; every later stage reads it as one. A list naming
        # `id#roman` would match nothing downstream and remove nothing, which is the quiet failure
        # — the pass would report a removal it never made.
        removed = sorted({pair_key(hit.doc_id) for hit in hits if hit.containment >= cut})
        written = write_exclusions(args.removals, removed, stage="8", readers=readers)
        print(f"\nwrote {written:,} contaminated ids to {args.removals}", file=sys.stderr)

    if args.hits_out:
        with Path(args.hits_out).open("w", encoding="utf-8", newline="\n") as handle:
            for hit in hits:
                handle.write(json.dumps(hit.to_dict(), ensure_ascii=False) + "\n")
        print(f"wrote {len(hits):,} measured hits to {args.hits_out}", file=sys.stderr)

    report = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.json:
        Path(args.json).write_text(report + "\n", encoding="utf-8", newline="\n")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
