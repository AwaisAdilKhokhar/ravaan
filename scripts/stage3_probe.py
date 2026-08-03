#!/usr/bin/env python
"""Run stages 2 and 3 over a real source and report what the classifier actually decided.

The lesson of Finding D (session 4) is that fixture tests prove a rule does what it says and say
nothing about whether it fires on the right things: 57 passing unit tests sat on top of a mojibake
detector that would have deleted 3% of a clean corpus. Stage 3 decides which documents count as
Urdu, so every threshold in it gets pointed at real text before the freeze.

Three things it reports, and each answers a question the module cannot answer about itself:

* **Label distribution** — what stage 3 does to this source. A source where nothing is rejected
  and a source where everything is says the same thing: the classifier is not discriminating.
* **Agreement with FineWeb2's own GlotLID labels** (`language_score`, `top_langs`), where the
  source carries them. This is the only external language label available without acquiring a new
  source, and disagreement is informative in both directions.
* **Known-truth accuracy** with ``--expect``: Roman-Urdu-Parl's Roman column is ~6.37M sentences
  of Roman Urdu, which makes it a labelled test set for the one decision (Roman Urdu vs English)
  that PRD §6.3.3 leaves open.

    python scripts/stage3_probe.py --source fineweb2-urd_Arab --limit 20000 --sample-rate 0.02
    python scripts/stage3_probe.py --source roman-urdu-parl --split validation --expect roman_urdu
    python scripts/stage3_probe.py --paths reports/*.md --expect english

Requires the `[data]` extra for parquet sources.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.data.encoding import EncodingConfig, EncodingLog, validate_text  # noqa: E402
from ravaan.data.langid import LangIDConfig, LangIDLog, classify  # noqa: E402
from ravaan.data.normalization import NormalizationConfig, normalize  # noqa: E402
from ravaan.data.shards import Document, ShardReader  # noqa: E402

# Stage 4 rules whose rate per document is the site-correlation question from session 4: FineWeb2
# changes only 13.7% of documents but averages 0.83 yeh substitutions across all of them, so a
# minority carries ~6 each. If that minority is a set of publishers rather than a diffuse
# property of the language, it interacts with near-dedup (stage 7) and with arm A's subsample.
VARIANT_RULES = ("yeh", "heh", "kaf", "teh_marbuta", "alef")


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


def main(argv: list[str] | None = None) -> int:
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
    parser.add_argument("--json", help="write the full report here")
    args = parser.parse_args(argv)

    encoding_config = EncodingConfig()
    langid_config = LangIDConfig()
    stage2 = EncodingLog(config=encoding_config)
    stage3 = LangIDLog(config=langid_config)
    normalization_config = NormalizationConfig()

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
    print(f"reading {plan}", file=sys.stderr)

    rng = random.Random(args.seed)
    examples: dict[str, list[str]] = defaultdict(list)
    seen_per_label: Counter[str] = Counter()
    glotlid_agree = Counter()
    glotlid_scores: dict[str, list[float]] = defaultdict(list)
    site_docs: Counter[str] = Counter()
    site_chars: Counter[str] = Counter()
    site_variants: dict[str, Counter[str]] = defaultdict(Counter)
    site_changed: Counter[str] = Counter()

    for doc in documents:
        checked = validate_text(doc.text, encoding_config)
        stage2.add(checked)
        if not checked.accepted:
            continue
        result = classify(checked.text or "", langid_config)
        stage3.add(result)

        # Reservoir sample per label, so examples are not all from the head of the read order.
        seen_per_label[result.label] += 1
        bucket = examples[result.label]
        if len(bucket) < args.examples:
            bucket.append((checked.text or "")[:300])
        elif rng.random() < args.examples / seen_per_label[result.label]:
            bucket[rng.randrange(args.examples)] = (checked.text or "")[:300]

        # FineWeb2 ships GlotLID's verdict per document. Free external validation.
        language = doc.meta.get("language") if isinstance(doc.meta, dict) else None
        if language:
            script = doc.meta.get("language_script") or "?"
            glotlid_agree[f"{language}_{script} -> {result.label}"] += 1
            score = doc.meta.get("language_score")
            if isinstance(score, int | float):
                glotlid_scores[result.label].append(float(score))

        if args.sites and result.label in ("urdu", "code_switched"):
            domain = _domain(doc.meta.get("url") if isinstance(doc.meta, dict) else None)
            if domain:
                normalized = normalize(checked.text or "", normalization_config)
                site_docs[domain] += 1
                site_chars[domain] += len(checked.text or "")
                if normalized.changed:
                    site_changed[domain] += 1
                for rule in VARIANT_RULES:
                    site_variants[domain][rule] += normalized.counts.get(rule, 0)

    payload: dict[str, object] = {
        "source": args.source or args.paths,
        "stage2_encoding": stage2.to_dict(),
        "stage3_langid": stage3.to_dict(),
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))

    # --- human-readable summary on stderr ----------------------------------
    total = stage3.documents
    if total:
        print(f"\n{total} documents classified", file=sys.stderr)
        for label, count in stage3.labels.most_common():
            letters = stage3.letters_by_label[label]
            share = 100 * count / total
            print(
                f"  {label:<15} {count:>7}  {share:>5.1f}%  {letters / 1e6:>8.2f}M letters",
                file=sys.stderr,
            )
        print(
            f"  kept (urdu/roman/code-switched): {100 * stage3.keep_rate:.2f}%  "
            f"mixed documents: {stage3.mixed_documents}",
            file=sys.stderr,
        )
        if stage3.segment_letters:
            print(f"  segment letters: {dict(stage3.segment_letters)}", file=sys.stderr)

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
        # Rates per 1,000 characters, restricted to domains with enough text to mean anything.
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

    for label, texts in sorted(examples.items()):
        for text in texts[:1]:
            print(f"\n--- {label} ---\n  {text[:200]!r}", file=sys.stderr)

    if args.json:
        Path(args.json).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
