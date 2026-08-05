#!/usr/bin/env python
"""Run pipeline stages 2→5 then stage 9 over real sources, and write the partition.

The fifth driver, after `scripts/probe.py` (2→5), `scripts/dedup.py` (2→6), `scripts/neardedup.py`
(2→7) and `scripts/decontaminate.py` (2→8). Stage 9 is two-phase for the same reason stage 6 is:
the band boundaries are a property of the whole corpus, so nothing can be decided on first sight of
a document. What is different is that **phase 2 needs nothing from phase 1 but a few integers** —
so a plan measured once can be applied by every later pass with `--plan-in`, and the freeze does
not have to re-measure to write the corpus.

Four questions it exists to answer:

* **Is there enough corpus?** Gate G1 (PRD §11) is a threshold on clean tokens, with a fallback
  ladder — 25–100M means arm A only, below 25M means stop. The report states the verdict and the
  number it rests on rather than leaving the gate to be eyeballed.
* **Can both arms actually be filled?** An arm whose budget the pool cannot meet is reported as
  ``unmet``, per population. This is the number G1's ladder needs and the one a "the splitter ran
  fine" summary would hide.
* **What does the held-out split contain?** ``--heldout-out`` writes it as JSONL so stage 8 can
  index it as an eval set — the second decontamination run, which is the one Finding L was about
  and which could not happen until this stage existed.
* **How wrong is the fertility estimate?** The tokenizer is Week 5 and stage 9 is Weeks 3–4, so
  token budgets are converted from measured characters. The report prints the characters-per-word
  it measured beside the ratio each population was solved with, and the plan carries the histogram
  so Week 5 can re-solve without a corpus pass (`ravaan-splits plan.json --chars-per-token
  urdu=3.9` — measured at 0.3 s against the ~20 minutes the pass that produced it took).

    python scripts/split.py --source urdu-wikipedia --limit 0 \\
        --plan-out reports/split_plan.json --heldout-out data/heldout.jsonl
    python scripts/split.py --source fineweb2-urd_Arab=0.05 --plan-in reports/split_plan.json

Requires the `[data]` extra for parquet sources.
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
from ravaan.data.pii import PIIConfig, PIILog, redact, redact_text  # noqa: E402
from ravaan.data.quality import QualityConfig, QualityLog, check  # noqa: E402
from ravaan.data.shards import LAYOUTS, ShardReader  # noqa: E402
from ravaan.data.splits import SplitAssigner, SplitConfig, SplitPlan  # noqa: E402

URDU_COLUMN = "Urdu text"


class Pipeline:
    """Stages 2→5 over a set of readers, yielding what reaches stage 9.

    Yields ``(doc_id, normalized, label, source)``. The stage-3 label is carried because it *is*
    the population: §6.1 budgets native Urdu, Roman Urdu and code-switched text separately, and
    stage 9's mixture is defined over exactly those three.

    A parallel row is emitted **once**, under its Roman-side label, with its Urdu column riding
    along in the same row rather than being split off as a second document. Emitting both columns
    would count one sentence pair in two populations and double the corpus on paper; keeping them
    together is also what §6.1's "~500K deduplicated pairs" presupposes, since a pair whose halves
    landed in different splits is not a pair.
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
                yield doc.doc_id, normalized, result.label, doc.source
        self.logging = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        metavar="NAME[=RATE]",
        help="source to partition; an optional per-source sampling rate overrides --sample-rate. "
        "Sampling is honest here — a split assignment is a per-document property, so a sampled "
        "phase 1 estimates the band quantiles rather than squaring the rate as stages 6 and 7 do",
    )
    parser.add_argument("-m", "--manifest", default="data/manifest.json")
    parser.add_argument("--split", help="restrict the sources to one acquisition split")
    parser.add_argument(
        "--limit", type=int, default=20_000, help="documents per source; 0 for no limit"
    )
    parser.add_argument("--sample-rate", type=float, help="stable per-document sampling rate")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--config", help="stage-9 config JSON (default: shipped defaults)")
    parser.add_argument(
        "--plan-in",
        help="apply bands solved by an earlier pass instead of measuring — one pass, not two",
    )
    parser.add_argument("--plan-out", help="write the solved plan (with its histogram) here")
    parser.add_argument(
        "--measure-only",
        action="store_true",
        help="run phase 1 and stop. The freeze's 'measure once over all sources, then apply that "
        "one plan everywhere' is exactly this, and running it as a two-phase pass doubles the "
        "most expensive read in the project for a phase 2 whose output is thrown away",
    )
    parser.add_argument(
        "--assignments-out", help="write every assignment here as JSONL, for stage 10"
    )
    parser.add_argument(
        "--heldout-out",
        help="write validation and test documents here as JSONL, with text — this is the eval "
        "set the second stage-8 run indexes",
    )
    parser.add_argument(
        "--no-quality", action="store_true", help="partition everything stage 3 kept, not stage 5's"
    )
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

    config = SplitConfig.from_json_file(args.config) if args.config else SplitConfig()
    sources = [_parse_source(spec, args.sample_rate) for spec in args.source]
    rates = {rate for _, rate in sources}
    if len(rates) > 1 and args.plan_in is None:
        raise SystemExit(
            f"phase 1 cannot solve bands from sources sampled at different rates {sorted(rates)} "
            "— the budgets are scaled by one rate. Measure at one rate, or pass --plan-in"
        )
    sample_rate = next(iter(rates)) if rates else None

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

    pipeline = Pipeline(readers, quality=not args.no_quality)
    assigner = SplitAssigner(config, sample_rate=sample_rate)

    if args.plan_in:
        plan = SplitPlan.from_json_file(args.plan_in)
        assigner.load_plan(plan)
        print(f"stage 9: applying bands from {args.plan_in}", file=sys.stderr)
    else:
        print("stage 9 phase 1: measuring", file=sys.stderr)
        for doc_id, normalized, label, _source in pipeline:
            assigner.measure(doc_id, normalized, label)
        plan = assigner.seal()
        print(
            f"  measured {assigner.log.measured:,} documents into {config.buckets:,} buckets",
            file=sys.stderr,
        )

    if args.measure_only:
        if args.plan_in:
            raise SystemExit("--measure-only and --plan-in are opposites; pick one")
        if args.plan_out:
            plan.to_json_file(args.plan_out)
            print(f"wrote the plan to {args.plan_out}", file=sys.stderr)
        # Phase 1 measures per population into the histogram, so the pool totals are available
        # without assigning anything. This is what the freeze needs to size the corpus and what
        # Gate G1's mixture check reads; the arm and split counts are phase 2's and are not here.
        print("\nstage 9 phase 1 — pool totals, before any assignment", file=sys.stderr)
        for population in config.populations:
            chars = sum(plan.histogram.get(population, []))
            scaled = chars * assigner.log.scale
            tokens = scaled / config.chars_per_token[population]
            print(
                f"    {population:<14} {chars:>15,} chars measured  "
                f"{scaled / 1e6:>10.1f}M scaled  ~{tokens / 1e6:>8.2f}M tokens  "
                f"unmet_arms={plan.bands[population].unmet_arms or '()'}",
                file=sys.stderr,
            )
        payload = {
            "measure_only": True,
            "sources": args.source,
            "sample_rate": sample_rate,
            "config_fingerprint": config.fingerprint(),
            "pool_chars": {
                p: sum(plan.histogram.get(p, [])) for p in config.populations
            },
            "bands": {p: b.to_dict() for p, b in sorted(plan.bands.items())},
            "stage2_encoding": pipeline.stage2.to_dict(),
            "stage3_langid": pipeline.stage3.to_dict(),
            "stage5_quality": {s: q.to_dict() for s, q in sorted(pipeline.stage5.items())},
            "pii": pipeline.pii.to_dict(),
        }
        report = json.dumps(payload, indent=2, ensure_ascii=False)
        if args.json:
            Path(args.json).write_text(report + "\n", encoding="utf-8", newline="\n")
        else:
            print(report)
        return 0

    print("stage 9 phase 2: assigning", file=sys.stderr)
    heldout_written = 0
    with contextlib.ExitStack() as stack:
        # newline="\n" on every corpus write. Session 4 shipped CRLF into normalized text through
        # Path.write_text's os.linesep default, which changes a corpus file's checksum on one
        # platform only; the held-out file below is exactly such a corpus file.
        def opened(path: str | None):
            if not path:
                return None
            return stack.enter_context(Path(path).open("w", encoding="utf-8", newline="\n"))

        assignments = opened(args.assignments_out)
        heldout = opened(args.heldout_out)

        for doc_id, normalized, label, source in pipeline:
            assignment = assigner.assign(doc_id, normalized, label, source=source)
            if assignments is not None:
                assignments.write(json.dumps(assignment.to_dict(), ensure_ascii=False) + "\n")
            if heldout is not None and assignment.split in ("validation", "test"):
                heldout.write(
                    json.dumps(
                        {
                            "doc_id": doc_id,
                            "split": assignment.split,
                            "population": assignment.population,
                            "source": source,
                            "text": normalized,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                heldout_written += 1

    payload = assigner.to_dict()
    payload["sources"] = args.source
    payload["limit"] = args.limit
    payload["seed"] = args.seed
    payload["quality_filtered"] = not args.no_quality
    payload["plan_in"] = args.plan_in
    payload["stage2_encoding"] = pipeline.stage2.to_dict()
    payload["stage3_langid"] = pipeline.stage3.to_dict()
    payload["stage5_quality"] = {s: q.to_dict() for s, q in sorted(pipeline.stage5.items())}
    payload["pii"] = pipeline.pii.to_dict()

    log = assigner.log
    print(
        f"\nstage 9: assigned {log.assigned:,} documents, "
        f"{log.unassigned:,} outside the budgeted populations",
        file=sys.stderr,
    )

    for population in config.populations:
        band = plan.bands[population]
        record = payload["populations"][population]
        print(f"\n  {population}", file=sys.stderr)
        for split in ("train", "validation", "test"):
            entry = record["splits"][split]
            print(
                f"    {split:<11} {entry['documents']:>9,} docs  "
                f"{entry['chars']:>14,} chars  ~{entry['tokens_estimated'] / 1e6:>8.2f}M tokens",
                file=sys.stderr,
            )
        for arm in config.arm_names:
            entry = record["arms"][arm]
            flag = "   UNMET" if arm in band.unmet_arms else ""
            # On a sampled pass the budget was scaled, so the full target is the wrong thing to
            # compare the realized size against — it makes a correct arm look 95% short at r=0.05.
            target = entry["target_tokens_this_pass"]
            note = (
                f"(target {target / 1e6:.2f}M at r={assigner.sample_rate}, "
                f"{entry['target_tokens'] / 1e6:.2f}M full)"
                if assigner.sample_rate
                else f"(target {target / 1e6:.2f}M)"
            )
            print(
                f"    arm {arm:<7} {entry['documents']:>9,} docs  "
                f"{entry['chars']:>14,} chars  ~{entry['tokens_estimated'] / 1e6:>8.2f}M tokens  "
                f"{note}{flag}",
                file=sys.stderr,
            )
        print(
            f"    fertility: {record['chars_per_word_measured']:.2f} chars/word measured, "
            f"solved at {record['chars_per_token']} chars/token "
            f"= {record['chars_per_word_measured'] / record['chars_per_token']:.2f} tokens/word",
            file=sys.stderr,
        )

    print("\n  arms, totalled across populations — this is §4.3's U", file=sys.stderr)
    for arm in config.arm_names:
        entry = payload["arms"][arm]
        print(
            f"    arm {arm}: {entry['documents']:>9,} docs  "
            f"~{entry['tokens_estimated'] / 1e6:>8.2f}M tokens of "
            f"{entry['target_tokens'] / 1e6:.0f}M target",
            file=sys.stderr,
        )

    gate = payload["gate_g1"]
    scaled = (
        f" (from {gate['clean_tokens_measured'] / 1e6:.1f}M measured at r={gate['sample_rate']})"
        if gate["sample_rate"]
        else ""
    )
    print(
        f"\n  GATE G1: {gate['verdict'].upper()} — "
        f"~{gate['clean_tokens_estimated'] / 1e6:.1f}M clean tokens against a "
        f"{gate['threshold'] / 1e6:.0f}M threshold{scaled}",
        file=sys.stderr,
    )
    # The aggregate is not the whole gate (PRD v2.2 §11): an arm is drawn from the pools at a
    # fixed mixture, so the binding constraint is usually one population and not the total.
    print(
        f"    aggregate: {gate['verdict_aggregate']}   "
        f"mixture: {gate['verdict_mixture']}   "
        f"arms fundable at the mixture: {gate['arms_fundable'] or 'none'}",
        file=sys.stderr,
    )
    for population, entry in gate["populations"].items():
        margin = entry["margin"]
        flag = "  SHORT" if margin is not None and margin < 1.0 else ""
        print(
            f"    {population:<14} ~{entry['supply_tokens'] / 1e6:>8.2f}M supply against "
            f"{entry['required_tokens'] / 1e6:>7.2f}M for arm {gate['required_for_arm']} "
            f"+ held-out = {margin:.2f}x{flag}",
            file=sys.stderr,
        )
    if payload.get("unmet_heldout"):
        # Printed before the arms because it is the upstream cause when both fire: the held-out
        # bands are solved first, so a pool below §6.1's ~5K sequences starves train and every arm
        # then reports unmet for a reason that is not its own.
        print(
            f"  UNMET HELD-OUT (the pool is smaller than §6.1's ~5K sequences): "
            f"{payload['unmet_heldout']}",
            file=sys.stderr,
        )
    if payload.get("unmet_arms"):
        print(f"  unmet arms: {payload['unmet_arms']}", file=sys.stderr)

    if args.plan_out:
        plan.to_json_file(args.plan_out)
        print(f"\nwrote the plan to {args.plan_out}", file=sys.stderr)
    if args.assignments_out:
        print(
            f"wrote {log.assigned + log.unassigned:,} assignments to {args.assignments_out}",
            file=sys.stderr,
        )
    if args.heldout_out:
        print(
            f"wrote {heldout_written:,} held-out documents to {args.heldout_out}", file=sys.stderr
        )

    report = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.json:
        Path(args.json).write_text(report + "\n", encoding="utf-8", newline="\n")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
