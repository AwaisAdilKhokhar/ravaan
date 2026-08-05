#!/usr/bin/env python
"""Run pipeline stages 2→5, apply stage 9's partition, and pack — stage 10 (PRD §6.3.10).

The sixth driver, and the last one before the freeze. It exists to answer two questions, and the
first one has to be answered *before* the corpus is written rather than after.

* **How wrong was the fertility estimate?** Stage 9's band boundaries are solved from a declared
  ``chars_per_token`` because §7's tokenizer is Week 5 and the freeze is Weeks 3–4. This stage
  counts tokens for the first time, so it is where that estimate is retired. ``--measure-only``
  does exactly that and nothing else: no shards, no disk, just the measured ratio per population
  and — with ``--resolve-plan`` — the stage-9 bands re-solved against it, so the movement in each
  arm cut is visible before anything is committed to. Fertility is a per-document ratio, so a
  sampled pass measures it honestly (Finding G's test), which makes this cheap.

* **What does the packed corpus contain?** Sequence counts, separator overhead, dropped tails and
  per-population token totals, plus a manifest naming the tokenizer that produced the ids.

Order matters here. Re-solving *after* writing means the arm cuts move under a corpus that has
already been packed to the old ones, so::

    # 1. measure, and see what the estimate cost
    python scripts/pack.py --source urdu-wikipedia --limit 0 --sample-rate 0.05 \\
        --measure-only --resolve-plan reports/stage9/plan_wikipedia.json

    # 2. re-solve stage 9 against the measurement, then pack against the corrected plan
    ravaan-splits reports/stage9/plan_wikipedia.json --chars-per-token urdu=3.87 \\
        --out reports/stage9/plan_wikipedia_resolved.json
    python scripts/pack.py --source urdu-wikipedia --limit 0 \\
        --plan-in reports/stage9/plan_wikipedia_resolved.json --out data/packed

Until §7's tokenizer is frozen the default tokenizer is a placeholder, and the writer refuses it
unless ``--allow-placeholder`` says so in as many words. Its fertility is a property of UTF-8, not
of Urdu, so a corpus written with it is a plumbing check and never a freeze.

Requires the `[data]` extra for parquet sources; `--tokenizer` needs `[tokenizer]`.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Urdu on a Windows console is cp1252 by default, which raises rather than mangles.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from ravaan.data.encoding import EncodingConfig, EncodingLog, validate_text  # noqa: E402
from ravaan.data.langid import LangIDConfig, LangIDLog, classify  # noqa: E402
from ravaan.data.normalization import NormalizationConfig, normalize_text  # noqa: E402
from ravaan.data.packing import (  # noqa: E402
    ByteTokenizer,
    CorpusPacker,
    PackedWriter,
    PackingConfig,
    SentencePieceTokenizer,
    Tokenizer,
)
from ravaan.data.pii import PIIConfig, PIILog, redact  # noqa: E402
from ravaan.data.quality import QualityConfig, QualityLog, check  # noqa: E402
from ravaan.data.shards import LAYOUTS, ShardReader  # noqa: E402
from ravaan.data.splits import SplitAssigner, SplitConfig, SplitPlan  # noqa: E402

URDU_COLUMN = "Urdu text"


class Pipeline:
    """Stages 2→5 over a set of readers, yielding what reaches stage 9.

    Yields ``(doc_id, normalized, label, source)``. Identical in shape to `scripts/split.py`'s,
    because stage 10 has to see exactly the text stage 9 partitioned — the assignment is a hash of
    the id, but the *characters* stage 9 budgeted are post-stage-4, and packing anything else would
    make the measured fertility describe a corpus nobody trained on.
    """

    def __init__(self, readers: list[ShardReader], *, quality: bool = True) -> None:
        self.readers = readers
        self.quality = quality
        self.encoding_config = EncodingConfig()
        self.langid_config = LangIDConfig()
        self.normalization_config = NormalizationConfig()
        self.stage2 = EncodingLog(config=self.encoding_config)
        self.stage3 = LangIDLog(config=self.langid_config)
        self.stage5: dict[str, QualityLog] = {}
        self.pii_config = PIIConfig()
        self.pii = PIILog(config=self.pii_config)

    def _redact(self, text: str) -> str:
        """PRD §6.3's PII pass. This driver reads once, so it always logs.

        The counts are taken here rather than sampled by `scripts/probe.py`, because "N phone
        numbers and M email addresses removed" is a claim the release makes about the corpus.
        This is also the pass that writes it.
        """
        result = redact(text, self.pii_config)
        self.pii.add(result)
        return result.text

    def _quality_config(self, source: str) -> QualityConfig:
        config = QualityConfig()
        layout = LAYOUTS.get(source)
        if layout is not None and layout.unit == "sentence":
            config = config.for_sentences()
        if source not in self.stage5:
            self.stage5[source] = QualityLog(config=config)
        return config

    def __iter__(self) -> Iterator[tuple[str, str, str, str]]:
        for reader in self.readers:
            for doc in reader:
                text = doc.text or ""
                if not text:
                    continue
                checked = validate_text(text, self.encoding_config)
                self.stage2.add(checked)
                if not checked.accepted:
                    continue
                repaired = checked.text or ""
                result = classify(repaired, self.langid_config)
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
                    self.stage5[doc.source].add(verdict)
                    if not verdict.accepted:
                        continue
                # PRD §6.3's PII pass sits here, between stage 5 and stage 6: stage 5's
                # thresholds were validated against unredacted text, and the packed token stream
                # is the corpus, so this is the last point at which redaction can still be
                # what gets trained on. See reports/pii.md §2.
                normalized = self._redact(normalized)
                yield doc.doc_id, normalized, result.label, doc.source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--source", action="append", required=True, metavar="NAME[=RATE]")
    parser.add_argument("-m", "--manifest", default="data/manifest.json")
    parser.add_argument("--split", help="restrict the sources to one acquisition split")
    parser.add_argument(
        "--limit", type=int, default=20_000, help="documents per source; 0 for no limit"
    )
    parser.add_argument("--sample-rate", type=float, help="stable per-document sampling rate")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--config", help="stage-10 config JSON (default: shipped defaults)")
    parser.add_argument("--splits-config", help="stage-9 config JSON, if not carried by --plan-in")
    parser.add_argument(
        "--plan-in",
        help="stage-9 plan to apply. Required to write a corpus: bands solved per source give "
        "each source its own held-out share instead of the corpus's",
    )
    parser.add_argument(
        "--tokenizer",
        help="path to §7's SentencePiece model. Without it the placeholder is used and only "
        "--measure-only or --allow-placeholder will run",
    )
    parser.add_argument("--out", help="root to write packed shards under")
    parser.add_argument("--manifest-out", help="write the corpus manifest here")
    parser.add_argument(
        "--measure-only",
        action="store_true",
        help="measure fertility and write nothing — the pass that has to happen before the corpus "
        "is packed, because the arm cuts move when the ratio does",
    )
    parser.add_argument(
        "--resolve-plan",
        help="with --measure-only: re-solve this stage-9 plan against the measured fertility and "
        "print how far every band moved",
    )
    parser.add_argument(
        "--allow-placeholder",
        action="store_true",
        help="write shards with the placeholder tokenizer. A plumbing check, never a freeze",
    )
    parser.add_argument("--no-quality", action="store_true")
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


def load_tokenizer(path: str | None) -> Tokenizer:
    return SentencePieceTokenizer(path) if path else ByteTokenizer()


def _resolve_report(plan: SplitPlan, measured: dict[str, float]) -> Iterator[str]:
    """How far every band moves when the estimate is replaced by the measurement.

    Printed as bucket cuts rather than as tokens because the cut is the thing that actually
    changes: a band holds its token budget by construction, and what moves is how much of the
    corpus that budget reaches.
    """
    updated = {**plan.config.chars_per_token}
    for population, ratio in measured.items():
        if population in updated:
            updated[population] = ratio
    from dataclasses import replace  # noqa: PLC0415

    resolved = plan.resolve(replace(plan.config, chars_per_token=updated))
    yield ""
    yield "  stage 9 re-solved against the measured fertility"
    for population in sorted(plan.bands):
        before, after = plan.bands[population], resolved.bands[population]
        old, new = plan.config.chars_per_token[population], updated[population]
        yield f"    {population}: {old} -> {new:.4f} chars/token"
        for arm in sorted(before.arm_cuts):
            a, b = before.arm_cuts[arm], after.arm_cuts[arm]
            drift = (b - a) / a * 100 if a else 0.0
            yield f"      arm {arm} cut {a:>7,} -> {b:>7,} buckets  ({drift:+.1f}%)"
    yield ""
    yield "  ravaan-splits <plan.json> " + " ".join(
        f"--chars-per-token {p}={r:.4f}" for p, r in sorted(measured.items())
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.measure_only and not args.out:
        raise SystemExit("--out is required unless --measure-only")
    if not args.measure_only and not args.plan_in:
        raise SystemExit(
            "--plan-in is required to write a corpus. Bands solved per source calibrate each "
            "source's held-out share to that source rather than to the corpus; measure once over "
            "everything and apply the one plan everywhere"
        )

    config = PackingConfig.from_json_file(args.config) if args.config else PackingConfig()
    tokenizer = load_tokenizer(args.tokenizer)

    if args.plan_in:
        plan = SplitPlan.from_json_file(args.plan_in)
        split_config = plan.config
    else:
        plan = None
        split_config = (
            SplitConfig.from_json_file(args.splits_config) if args.splits_config else SplitConfig()
        )
    if split_config.sequence_length != config.sequence_length:
        raise SystemExit(
            f"stage 9 sized its held-out bands at {split_config.sequence_length}-token sequences "
            f"and stage 10 packs at {config.sequence_length} — §6.1's '~5K sequences' would mean "
            "two different amounts of text"
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
    sample_rate = next(iter({rate for _, rate in sources}), None)

    assigner = SplitAssigner(split_config, sample_rate=sample_rate)
    if plan is not None:
        assigner.load_plan(plan)
    packer = CorpusPacker(config, tokenizer, sample_rate=sample_rate)

    writer = None
    if not args.measure_only:
        writer = PackedWriter(
            args.out, config, tokenizer, allow_placeholder=args.allow_placeholder
        )

    pipeline = Pipeline(readers, quality=not args.no_quality)
    if plan is None:
        # No plan: phase 1 has to run before anything can be assigned, so this is a two-pass
        # measurement over a materialized list. Only sane at --limit; the freeze always has a plan.
        documents = list(pipeline)
        for doc_id, text, label, _ in documents:
            assigner.measure(doc_id, text, label)
        assigner.seal()
        stream = iter(documents)
    else:
        stream = iter(pipeline)

    for doc_id, text, label, source in stream:
        assignment = assigner.assign(doc_id, text, label, source=source)
        if not assignment.assigned:
            continue
        emitted = packer.add(
            text, assignment.population, assignment.split, assignment.arms
        )
        for name, sequence in emitted:
            if writer is not None:
                writer.add(name, sequence)
    packer.finish()
    if writer is not None:
        writer.close()

    log = packer.log
    print(f"\nstage 10 — tokenizer {tokenizer.tokenizer_id}", file=sys.stderr)
    print("\n  fertility, measured against stage 9's estimate", file=sys.stderr)
    for population, entry in log.fertility_report().items():
        estimated = split_config.chars_per_token.get(population)
        measured = entry["chars_per_token_measured"]
        drift = f"{(measured - estimated) / estimated * 100:+.1f}%" if estimated else "—"
        print(
            f"    {population:<14} {measured:>7.3f} chars/token measured against "
            f"{estimated if estimated else '—'} estimated  ({drift})   "
            f"separators {entry['separator_share'] * 100:.2f}%   "
            f"{entry['bytes_per_token_measured']:.3f} bytes/token",
            file=sys.stderr,
        )

    print("\n  streams", file=sys.stderr)
    for name in sorted(log.encoded_tokens):
        print(
            f"    {name:<24} {log.sequences[name]:>8,} seq  "
            f"{log.tokens[name]:>12,} tokens  {log.documents[name]:>9,} docs  "
            f"dropped {log.dropped_tokens[name]:>4,}",
            file=sys.stderr,
        )

    if args.resolve_plan or (args.measure_only and plan is not None):
        target = SplitPlan.from_json_file(args.resolve_plan) if args.resolve_plan else plan
        with contextlib.suppress(ValueError):  # a histogram-stripped plan cannot be re-solved
            for line in _resolve_report(target, log.measured_chars_per_token()):
                print(line, file=sys.stderr)

    payload: dict = {"stage10": log.to_dict(), "pii": pipeline.pii.to_dict()}
    if writer is not None:
        payload["corpus"] = writer.manifest(log)
        if args.manifest_out:
            writer.write_manifest(args.manifest_out, log)
            print(
                f"\nwrote {len(writer.shards):,} shards under {args.out} "
                f"and the manifest to {args.manifest_out}",
                file=sys.stderr,
            )

    report = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.json:
        Path(args.json).write_text(report + "\n", encoding="utf-8", newline="\n")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
