#!/usr/bin/env python
"""Run pipeline stages 2→5 over a real source and report what they actually did.

The lesson of Finding D (session 4) is that fixture tests prove a rule does what it says and say
nothing about whether it fires on the right things: 57 passing unit tests sat on top of a mojibake
detector that would have deleted 3% of a clean corpus. Every threshold in stages 2, 3 and 5
therefore gets pointed at real text before the freeze, and this is the thing that points it.

It replaces `corpus_probe.py` (stages 2+4, read parquet by hand, predated the shard reader) and
`stage3_probe.py` (stages 2+3). Both covered ground this covers, and two probes that disagree
about how to sample are worse than one.

What it reports, and the question each answers that the modules cannot answer about themselves:

* **Stage 5 metric distributions.** Percentiles for every quality metric, per source. This is the
  output that sets thresholds: the inherited Gopher repetition values reject 13.7% of FineWeb2,
  and the only way to know that is to look at the distribution rather than at the constant.
* **Sole rejections.** Documents rejected by exactly one rule family. A rule with no sole
  rejections is agreeing with another rule, not filtering the corpus.
* **Label distribution** (stage 3) — a source where nothing is rejected and a source where
  everything is say the same thing: the classifier is not discriminating.
* **Agreement with FineWeb2's own GlotLID labels**, where the source carries them. The only
  external language label available without acquiring a new source.
* **Known-truth accuracy** with ``--expect``: Roman-Urdu-Parl's Roman column is a labelled test
  set for the Roman-Urdu-vs-English decision PRD §6.3.3 left open.
* **Per-domain variant rates** with ``--sites`` — Finding F, that Arabic-variant spelling is a
  property of publishers rather than of the language.

    python scripts/probe.py --source fineweb2-urd_Arab --limit 20000 --sample-rate 0.02
    python scripts/probe.py --source urdu-wikipedia --limit 20000 --sites
    python scripts/probe.py --source roman-urdu-parl --split validation --expect roman_urdu
    python scripts/probe.py --paths reports/*.md --expect english

Requires the `[data]` extra for parquet sources.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

from ravaan.data.encoding import EncodingConfig, EncodingLog, validate_text  # noqa: E402
from ravaan.data.langid import LangIDConfig, LangIDLog, classify  # noqa: E402
from ravaan.data.normalization import (  # noqa: E402
    NormalizationConfig,
    NormalizationLog,
    normalize,
)
from ravaan.data.pii import PIIConfig, PIILog, PIIResult, redact  # noqa: E402
from ravaan.data.quality import QualityConfig, QualityLog, check  # noqa: E402
from ravaan.data.shards import LAYOUTS, Document, ShardReader  # noqa: E402

# Stage 4 rules whose per-character rate is Finding F: FineWeb2 changes only 13.7% of documents
# but averages 0.83 yeh substitutions across all of them, so a minority carries ~6 each.
VARIANT_RULES = ("yeh", "heh", "kaf", "teh_marbuta", "alef")

PERCENTILES = (0.01, 0.05, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)

# Digit runs left in a PII context window after redaction — i.e. numbers the pass did not catch.
# Six is below any phone number this corpus writes and above a year, a price group or a page
# number, so the linguistic context a reader needs survives intact. See `_pii_contexts`.
_RESIDUAL_DIGITS_RE = re.compile(r"\d[\d .‐-―-]{4,}\d|\d{6,}")

# Stage-5 metrics worth a distribution. The repetition family is where the published thresholds
# turned out not to transfer, so every member of it is reported separately.
QUALITY_METRICS: tuple[str, ...] = (
    "chars",
    "words",
    "script_ratio",
    "url_ratio",
    "html_ratio",
    "dup_line_ratio",
    "max_top_ngram",
    "max_dup_ngram",
)


def _pii_contexts(result: PIIResult, config: PIIConfig, width: int = 55) -> list[str]:
    """A context window around each redaction, taken from the **redacted** text.

    This is the output a human reads to decide whether the PII pass is matching phone numbers or
    dates, and it has to be adjudicable without being a contact list. Two things stand between it
    and being one, and the second was found by grepping the committed report rather than by
    reasoning about it.

    * The window is cut from the **redacted** text. Windowing the input would be one line shorter
      and would print the match itself.
    * Residual digit runs are then masked to their **length**. Cutting from the redacted text is
      not sufficient, because a number the pass *missed* still sits there in full — 29 of them in
      the first committed run of this probe, including live Indian mobile numbers the pattern
      cannot see (`reports/pii.md` §6). `{10d}` keeps the finding that an uncaught ten-digit run
      is there, which is the only part a reader needs, and publishes no one's number.
    """
    windows: list[str] = []
    delta = 0
    for match in result.matches:
        placeholder = (
            config.email_placeholder if match.category == "email" else config.phone_placeholder
        )
        start = match.start + delta
        end = start + len(placeholder)
        delta += len(placeholder) - (match.end - match.start)
        window = " ".join(result.text[max(0, start - width) : end + width].split())
        windows.append(
            _RESIDUAL_DIGITS_RE.sub(
                lambda m: f"{{{sum(ch.isdigit() for ch in m.group())}d}}", window
            )
        )
    return windows


def _paragraphs(paths: list[str], min_chars: int) -> list[Document]:
    """Plain-text files split into paragraphs — for checking against non-corpus text."""
    docs: list[Document] = []
    for path in paths:
        raw = Path(path).read_text(encoding="utf-8")
        for index, block in enumerate(raw.split("\n\n")):
            block = block.strip()
            if len(block) >= min_chars:
                docs.append(Document(source=path, doc_id=f"{path}:{index}", text=block))
    return docs


def _percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)
    out = {
        f"p{int(p * 100)}": round(ordered[min(int(p * len(ordered)), len(ordered) - 1)], 5)
        for p in PERCENTILES
    }
    out["max"] = round(ordered[-1], 5)
    out["mean"] = round(sum(ordered) / len(ordered), 5)
    return out


def _site_row(domain: str, docs: int, chars: int, hits: int, changed: float) -> dict:
    return {
        "domain": domain,
        "docs": docs,
        "kchars": round(chars / 1000, 1),
        # Per 1,000 characters, not per document. Rates per document conflate the property with
        # length, and the domains at the top of this table publish book-length pages: a religious
        # library with 3,500 variant hits in six documents may simply have six very long
        # documents. Per-character is the rate the question was actually about.
        "variants_per_kchar": round(1000 * hits / chars, 2) if chars else 0.0,
        "changed_pct": round(changed, 1),
    }


def _domain(url: str | None) -> str:
    if not url:
        return ""
    host = urlsplit(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source", help="source name from data/manifest.json")
    source.add_argument("--paths", nargs="+", help="plain-text files, split into paragraphs")
    parser.add_argument("-m", "--manifest", default="data/manifest.json")
    parser.add_argument("--split", help="restrict to one split")
    parser.add_argument("--limit", type=int, default=20_000, help="documents to read")
    parser.add_argument(
        "--sample-rate",
        type=float,
        help="stable per-document sampling rate; with --limit this spreads the sample over many "
        "more row groups than a bare limit would touch",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--expect", help="known-truth label for every document in this source")
    parser.add_argument("--sites", action="store_true", help="per-domain stage-4 variant rates")
    parser.add_argument("--min-chars", type=int, default=200, help="--paths paragraph minimum")
    parser.add_argument("--examples", type=int, default=2, help="examples to show per label")
    parser.add_argument("--quality-config", help="stage-5 config JSON (default: shipped defaults)")
    parser.add_argument("--pii-config", help="PII config JSON (default: shipped defaults)")
    parser.add_argument(
        "--pii-examples",
        type=int,
        default=25,
        help="redaction context windows to keep per category, for reading what fired",
    )
    parser.add_argument("--json", help="write the full report here")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    encoding_config = EncodingConfig()
    langid_config = LangIDConfig()
    normalization_config = NormalizationConfig()
    quality_config = (
        QualityConfig.from_json_file(args.quality_config)
        if args.quality_config
        else QualityConfig()
    )
    # Roman-Urdu-Parl rows are single sentences; the document-length and line-repetition rules
    # would reject the whole source. The layout already declares the unit, so read it rather than
    # asking the operator to remember.
    unit = LAYOUTS[args.source].unit if args.source in LAYOUTS else "document"
    if unit == "sentence":
        quality_config = quality_config.for_sentences()

    pii_config = PIIConfig.from_json_file(args.pii_config) if args.pii_config else PIIConfig()

    stage2 = EncodingLog(config=encoding_config)
    stage3 = LangIDLog(config=langid_config)
    stage4 = NormalizationLog(config=normalization_config)
    stage5 = QualityLog(config=quality_config)
    stage_pii = PIILog(config=pii_config)

    if args.paths:
        documents: object = _paragraphs(args.paths, args.min_chars)[: args.limit]
        plan = f"{len(args.paths)} text file(s)"
    else:
        reader = ShardReader.from_manifest(
            args.source,
            manifest_path=args.manifest,
            split=args.split,
            limit=args.limit,
            sample_rate=args.sample_rate,
            seed=args.seed,
        )
        documents = reader
        plan = f"plan {reader.plan_fingerprint()} over {len(reader.files)} file(s)"
    print(f"reading {plan}  (stage-5 unit: {unit})", file=sys.stderr)

    rng = random.Random(args.seed)
    examples: dict[str, list[str]] = defaultdict(list)
    rejected_examples: dict[str, list[tuple[str, str]]] = defaultdict(list)
    seen_per_label: Counter[str] = Counter()
    seen_per_family: Counter[str] = Counter()
    pii_examples: dict[str, list[dict]] = defaultdict(list)
    pii_seen: Counter[str] = Counter()
    glotlid_agree: Counter[str] = Counter()
    glotlid_scores: dict[str, list[float]] = defaultdict(list)
    site_docs: Counter[str] = Counter()
    site_chars: Counter[str] = Counter()
    site_variants: dict[str, Counter[str]] = defaultdict(Counter)
    site_changed: Counter[str] = Counter()
    metric_values: dict[str, list[float]] = defaultdict(list)

    for doc in documents:
        checked = validate_text(doc.text, encoding_config)
        stage2.add(checked)
        if not checked.accepted:
            continue

        # Stage 3 runs on pre-normalization text on purpose: Arabic-keyboard Urdu still writes که
        # for کہ, and folding first merges the evidence that separates Urdu from Persian.
        result = classify(checked.text or "", langid_config)
        stage3.add(result)

        normalized = normalize(checked.text or "", normalization_config)
        stage4.add(normalized)

        quality = check(
            normalized.normalized,
            quality_config,
            label=result.label,
            scripts=result.scripts,
            letters=result.letters,
        )
        stage5.add(quality)

        for name in QUALITY_METRICS:
            metric_values[name].append(float(getattr(quality.metrics, name)))

        # PRD §6.3's PII pass, in the position it runs in at the freeze: after stage 5, on the
        # normalized text. It is measured on every document rather than on stage 5's survivors,
        # because a rejected document still tells you what the two patterns fire on.
        pii = redact(normalized.normalized, pii_config)
        stage_pii.add(pii)
        for match, window in zip(pii.matches, _pii_contexts(pii, pii_config), strict=True):
            pii_seen[match.category] += 1
            bucket = pii_examples[match.category]
            entry = {"doc_id": doc.doc_id, "shape": match.shape, "context": window}
            if len(bucket) < args.pii_examples:
                bucket.append(entry)
            elif rng.random() < args.pii_examples / pii_seen[match.category]:
                bucket[rng.randrange(args.pii_examples)] = entry

        # Reservoir sample per label, so examples are not all from the head of the read order.
        seen_per_label[result.label] += 1
        bucket = examples[result.label]
        if len(bucket) < args.examples:
            bucket.append((checked.text or "")[:300])
        elif rng.random() < args.examples / seen_per_label[result.label]:
            bucket[rng.randrange(args.examples)] = (checked.text or "")[:300]

        # The same reservoir over *rejections*, keyed by rule family. This is the part that gets
        # read by a human: a threshold is only defensible once you have looked at what it deletes.
        for family in quality.families:
            seen_per_family[family] += 1
            hits = rejected_examples[family]
            entry = (doc.doc_id, normalized.normalized[:300])
            if len(hits) < args.examples:
                hits.append(entry)
            elif rng.random() < args.examples / seen_per_family[family]:
                hits[rng.randrange(args.examples)] = entry

        # FineWeb2 ships GlotLID's verdict per document. Free external validation.
        language = doc.meta.get("language") if isinstance(doc.meta, dict) else None
        if language:
            script = doc.meta.get("language_script") or "?"
            glotlid_agree[f"{language}_{script} -> {result.label}"] += 1
            glotlid_score = doc.meta.get("language_score")
            if isinstance(glotlid_score, int | float):
                glotlid_scores[result.label].append(float(glotlid_score))

        if args.sites and result.label in ("urdu", "code_switched"):
            domain = _domain(doc.meta.get("url") if isinstance(doc.meta, dict) else None)
            if domain:
                site_docs[domain] += 1
                site_chars[domain] += len(checked.text or "")
                if normalized.changed:
                    site_changed[domain] += 1
                for rule in VARIANT_RULES:
                    site_variants[domain][rule] += normalized.counts.get(rule, 0)

    payload: dict[str, object] = {
        "source": args.source or args.paths,
        "split": args.split,
        "limit": args.limit,
        "sample_rate": args.sample_rate,
        "seed": args.seed,
        "stage2_encoding": stage2.to_dict(),
        "stage3_langid": stage3.to_dict(),
        "stage4_normalization": stage4.to_dict(),
        "stage5_quality": stage5.to_dict(),
        "stage5_distributions": {
            name: _percentiles(values) for name, values in sorted(metric_values.items())
        },
        "stage5_rejected_examples": {
            family: [{"doc_id": d, "text": t} for d, t in hits]
            for family, hits in sorted(rejected_examples.items())
        },
        "pii": stage_pii.to_dict(),
        "pii_examples": {c: hits for c, hits in sorted(pii_examples.items())},
    }

    # --- human-readable summary on stderr ----------------------------------
    total = stage3.documents
    if total:
        print(f"\n{total} documents classified (stage 3)", file=sys.stderr)
        for label, count in stage3.labels.most_common():
            letters = stage3.letters_by_label[label]
            print(
                f"  {label:<15} {count:>7}  {100 * count / total:>5.1f}%  "
                f"{letters / 1e6:>8.2f}M letters",
                file=sys.stderr,
            )
        print(
            f"  kept (urdu/roman/code-switched): {100 * stage3.keep_rate:.2f}%  "
            f"mixed documents: {stage3.mixed_documents}  "
            f"by prior: {100 * stage3.documents_by_prior / total:.2f}%",
            file=sys.stderr,
        )

    if stage4.documents:
        print(
            f"\nstage 4: {100 * stage4.documents_changed / stage4.documents:.1f}% of documents "
            f"changed, {stage4.chars_in / 1e6:.2f}M -> {stage4.chars_out / 1e6:.2f}M chars",
            file=sys.stderr,
        )

    if stage5.documents:
        print(
            f"\nstage 5: kept {stage5.documents_kept}/{stage5.documents} "
            f"= {100 * stage5.keep_rate:.2f}% of documents, "
            f"{100 * stage5.char_keep_rate:.2f}% of characters",
            file=sys.stderr,
        )
        print("  family              fired    sole", file=sys.stderr)
        for family, count in stage5.families.most_common():
            print(
                f"  {family:<18} {count:>6}  {stage5.sole_rejections.get(family, 0):>6}",
                file=sys.stderr,
            )
        if not stage5.families:
            print("  (nothing rejected — this stage is an assertion on this source)",
                  file=sys.stderr)
        print("\n  distributions", file=sys.stderr)
        for name in QUALITY_METRICS:
            stats = _percentiles(metric_values.get(name, []))
            if not stats:
                continue
            print(
                f"    {name:<16} p50={stats['p50']:>10.4f} p90={stats['p90']:>10.4f} "
                f"p99={stats['p99']:>10.4f} max={stats['max']:>10.4f}",
                file=sys.stderr,
            )

    if stage_pii.documents:
        print(
            f"\nPII: redacted {stage_pii.documents_redacted}/{stage_pii.documents} documents "
            f"= {100 * stage_pii.documents_redacted / stage_pii.documents:.2f}%, "
            f"{sum(stage_pii.counts.values())} matches, "
            f"{stage_pii.chars_in - stage_pii.chars_out} characters",
            file=sys.stderr,
        )
        for category, count in stage_pii.counts.most_common():
            print(f"  {category:<8} {count:>7}", file=sys.stderr)
        # The shapes are the precision instrument: a false positive is a date, a year range or an
        # ISBN, and those do not have a phone number's shape.
        for key, count in stage_pii.shapes.most_common(12):
            print(f"    {key:<40} {count:>6}", file=sys.stderr)
        if not stage_pii.counts:
            print("  (nothing matched — this pass is an assertion on this source)",
                  file=sys.stderr)

    if args.expect:
        correct = stage3.labels.get(args.expect, 0)
        accuracy = correct / total if total else 0.0
        payload["expected_label"] = args.expect
        payload["accuracy"] = round(accuracy, 5)
        print(f"\naccuracy against --expect {args.expect}: {100 * accuracy:.2f}%", file=sys.stderr)
        for label, count in stage3.labels.most_common():
            if label != args.expect:
                print(f"  confused as {label:<15} {count:>7}", file=sys.stderr)

    if glotlid_agree:
        payload["glotlid_agreement"] = dict(glotlid_agree.most_common(20))
        print("\nFineWeb2's own GlotLID label -> our label", file=sys.stderr)
        for pair, count in glotlid_agree.most_common(12):
            print(f"  {pair:<40} {count:>7}", file=sys.stderr)
        for label, scores in sorted(glotlid_scores.items()):
            mean = sum(scores) / len(scores)
            print(
                f"  mean GlotLID confidence for our {label:<14} {mean:.3f}  (n={len(scores)})",
                file=sys.stderr,
            )

    if args.sites and site_docs:
        eligible = [d for d, n in site_docs.items() if n >= 5 and site_chars[d] >= 20_000]
        rows = sorted(
            (
                (
                    1000 * sum(site_variants[d].values()) / site_chars[d],
                    d,
                    site_docs[d],
                    site_chars[d],
                    sum(site_variants[d].values()),
                    100 * site_changed[d] / site_docs[d],
                )
                for d in eligible
            ),
            reverse=True,
        )
        variants_total = sum(sum(c.values()) for c in site_variants.values())
        ranked = sorted((sum(site_variants[d].values()) for d in site_docs), reverse=True)
        top_share = sum(ranked[: max(len(ranked) // 100, 1)]) / (variants_total or 1)
        chars_total = sum(site_chars.values())
        payload["sites"] = {
            "domains": len(site_docs),
            "domains_measured": len(eligible),
            "chars": chars_total,
            "variant_hits": variants_total,
            "variants_per_kchar_overall": round(1000 * variants_total / (chars_total or 1), 2),
            "share_from_top_1pct_of_domains": round(top_share, 4),
            "highest_rate": [_site_row(d, n, c, h, ch) for _, d, n, c, h, ch in rows[:15]],
            "lowest_rate": [_site_row(d, n, c, h, ch) for _, d, n, c, h, ch in rows[-15:]],
        }
        print(
            f"\n{len(site_docs)} domains, {len(eligible)} with >=5 documents and >=20k chars; "
            f"top 1% of domains carry {100 * top_share:.1f}% of all variant hits; "
            f"corpus-wide {1000 * variants_total / (chars_total or 1):.2f} variants/kchar",
            file=sys.stderr,
        )
        for rate, domain, docs, chars, _, changed in rows[:10] + rows[-5:]:
            print(
                f"  {domain:<32} {docs:>4} docs {chars / 1000:>8.0f}k chars "
                f"{rate:>7.2f} /kchar {changed:>5.1f}% changed",
                file=sys.stderr,
            )

    for family, hits in sorted(rejected_examples.items()):
        for _, text in hits[:1]:
            print(f"\n--- rejected by {family} ---\n  {text[:200]!r}", file=sys.stderr)

    if args.json:
        Path(args.json).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
