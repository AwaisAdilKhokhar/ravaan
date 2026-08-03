#!/usr/bin/env python
"""Draw and score the 200-sample manual validation of stage 5 (PRD §6.3.5).

§6.3.5 requires the quality rules to be "validated against 200 manually inspected random
samples". That sentence is the deliverable, not the filter: thresholds picked from a distribution
are a hypothesis about what the corpus contains, and the only thing that turns them into a claim
is a person reading the documents and disagreeing.

Two modes.

``draw`` reads the corpus through :class:`~ravaan.data.shards.ShardReader`, runs stages 2→5, and
writes the sample twice — once as JSONL for scoring, once as a Markdown review sheet a person can
read and mark up in place. ``score`` reads the marked-up sheet back and reports where the filter
and the human disagree.

**The sample is stratified, and it has to be.** A uniform random 200 would be the honest sample if
the question were "how good is the corpus", but the question is "are these rules right", and
stage 5 rejects 0.26% of FineWeb2 — so a uniform 200 would contain zero or one rejected document
and could not validate a single rejection. The sample is therefore drawn in two strata that are
scored separately and never pooled:

* **uniform** (100 documents, 50 per source) — an unbiased sample of what the filter *keeps*.
  False accepts are estimated here and the estimate means what it says.
* **rejected** (100 documents, spread across rule families) — an oversample of what the filter
  *drops*, so each rule's precision can be measured with enough documents to be worth reporting.
  These are deliberately not representative and no corpus-level rate may be computed from them.

Both strata are drawn by :func:`~ravaan.data.shards.stable_unit` on the document id, so the same
seed selects the same documents on any machine, in any read order, before or after a resume.

    python scripts/quality_sample.py draw --out reports/quality_sample
    # ... a fluent Urdu speaker fills in the **verdict:** lines in the .md ...
    python scripts/quality_sample.py score reports/quality_sample.md

Requires the `[data]` extra.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from ravaan.data.encoding import EncodingConfig, validate_text  # noqa: E402
from ravaan.data.langid import LangIDConfig, classify  # noqa: E402
from ravaan.data.normalization import NormalizationConfig, normalize  # noqa: E402
from ravaan.data.quality import QualityConfig, QualityMetrics, check  # noqa: E402
from ravaan.data.quality import score as quality_score  # noqa: E402
from ravaan.data.shards import LAYOUTS, ShardReader  # noqa: E402

SOURCES = ("fineweb2-urd_Arab", "urdu-wikipedia")

# Characters of each document shown in the review sheet. Long enough that a judgement about
# repetition, boilerplate and script mixture is available from the excerpt; short enough that 200
# of them are readable in one sitting. The full length is always printed alongside.
EXCERPT_CHARS = 1500

VERDICTS = ("keep", "drop", "?")

_BLOCK_RE = re.compile(
    r"^### (?P<index>\d+) · (?P<doc_id>.+?)$(?P<body>.*?)(?=^### |\Z)",
    re.MULTILINE | re.DOTALL,
)
_VERDICT_RE = re.compile(r"^\*\*verdict:\*\*\s*(?P<verdict>\S*)", re.MULTILINE)
_NOTE_RE = re.compile(r"^\*\*note:\*\*\s*(?P<note>.*)$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Draw
# ---------------------------------------------------------------------------


def _pipeline(doc, encoding_config, langid_config, normalization_config, quality_config):
    """Stages 2→5 for one document. ``None`` when stage 2 rejects it."""
    checked = validate_text(doc.text, encoding_config)
    if not checked.accepted:
        return None
    lid = classify(checked.text or "", langid_config)
    normalized = normalize(checked.text or "", normalization_config)
    config = quality_config
    if LAYOUTS.get(doc.source) and LAYOUTS[doc.source].unit == "sentence":
        config = quality_config.for_sentences()
    quality = check(
        normalized.normalized,
        config,
        label=lid.label,
        scripts=lid.scripts,
        letters=lid.letters,
    )
    layout = LAYOUTS.get(doc.source)
    return {
        "doc_id": doc.doc_id,
        "source": doc.source,
        "unit": layout.unit if layout else "document",
        "url": (doc.meta or {}).get("url") or (doc.meta or {}).get("title") or "",
        "label": lid.label,
        "by_prior": lid.by_prior,
        "accepted": quality.accepted,
        "reasons": list(quality.reasons),
        "families": list(quality.families),
        "metrics": quality.metrics.to_dict(),
        "normalization_changed": normalized.changed,
        "normalization_counts": {k: v for k, v in sorted(normalized.counts.items()) if v},
        "chars_original": len(normalized.original),
        "chars_normalized": len(normalized.normalized),
        "text": normalized.normalized,
        "config_fingerprint": quality.config_fingerprint,
    }


def draw(args: argparse.Namespace) -> list[dict]:
    encoding_config = EncodingConfig()
    langid_config = LangIDConfig()
    normalization_config = NormalizationConfig()
    quality_config = (
        QualityConfig.from_json_file(args.quality_config)
        if args.quality_config
        else QualityConfig()
    )

    per_source_uniform = args.uniform // len(SOURCES)
    per_source_rejected = args.rejected // len(SOURCES)
    sample: list[dict] = []
    # Whatever a source could not supply, kept so the deficit can be filled from the other one.
    # FineWeb2 rejects 0.26% of documents, so its quota is not always reachable in one scan, and a
    # sample of 196 is not the sample PRD §6.3.5 asks for.
    leftovers: list[dict] = []

    for source in SOURCES:
        reader = ShardReader.from_manifest(
            source,
            manifest_path=args.manifest,
            split="train" if source == "fineweb2-urd_Arab" else None,
            limit=args.scan,
            sample_rate=args.sample_rate,
            seed=args.seed,
        )
        print(
            f"scanning {source}: plan {reader.plan_fingerprint()}, up to {args.scan} documents",
            file=sys.stderr,
        )
        uniform: list[dict] = []
        uniform_ids: set[str] = set()
        rejected: dict[str, list[dict]] = defaultdict(list)

        for doc in reader:
            record = _pipeline(
                doc, encoding_config, langid_config, normalization_config, quality_config
            )
            if record is None:
                continue
            # The uniform stratum takes the first N in the reader's (already seeded-shuffled,
            # spread-across-row-groups) order, which is a random sample of the source and not a
            # prefix of the file — Finding E.
            if len(uniform) < per_source_uniform:
                record["stratum"] = "uniform"
                uniform.append(record)
                uniform_ids.add(record["doc_id"])
                continue
            for family in record["families"]:
                rejected[family].append(record)

        # Spread the rejection stratum across families, smallest first, rather than taking the
        # commonest. Rules that fire rarely are exactly the ones whose thresholds rest on the
        # least evidence, so a proportional draw would leave them uninspected — and `html_residue`
        # firing 41 times in 20,000 documents is precisely a threshold worth a human's eye.
        picked: list[dict] = []
        picked_ids: set[str] = set(uniform_ids)
        families = sorted(rejected, key=lambda f: len(rejected[f]))
        remaining = per_source_rejected
        for position, family in enumerate(families):
            if remaining <= 0:
                break
            share = max(remaining // (len(families) - position), 1)
            for record in rejected[family]:
                if len(picked) >= per_source_rejected or share <= 0:
                    break
                if record["doc_id"] in picked_ids:
                    continue
                record["stratum"] = "rejected"
                picked.append(record)
                picked_ids.add(record["doc_id"])
                share -= 1
                remaining -= 1

        sample.extend(uniform)
        sample.extend(picked)
        leftovers.extend(
            record
            for family_records in rejected.values()
            for record in family_records
            if record["doc_id"] not in picked_ids
        )
        print(
            f"  {source}: {len(uniform)} uniform, {len(picked)} rejected "
            f"(available: {_family_summary(rejected)})",
            file=sys.stderr,
        )

    # Top up to the requested total from whichever source had a surplus, rarest family first for
    # the same reason as above. The stratum label still says "rejected", so nothing downstream
    # treats these as a random sample; only the per-source balance changes.
    deficit = args.rejected - sum(1 for r in sample if r.get("stratum") == "rejected")
    if deficit > 0:
        chosen_ids = {r["doc_id"] for r in sample}
        pool = [r for r in leftovers if r["doc_id"] not in chosen_ids]
        pool.sort(key=lambda r: (len(r["families"]), r["doc_id"]))
        seen: set[str] = set()
        for record in pool:
            if deficit <= 0:
                break
            if record["doc_id"] in seen:
                continue
            seen.add(record["doc_id"])
            record["stratum"] = "rejected"
            sample.append(record)
            deficit -= 1
        print(f"  topped up the rejection stratum by {len(seen)} document(s)", file=sys.stderr)

    # A stable order that does not leak the stratum to the reader: sorting by the same hash the
    # sampler used interleaves kept and rejected documents, so a person marking the sheet cannot
    # infer the filter's answer from position. They can still read it — the filter's verdict is
    # printed — but the ordering does not do the priming for them.
    from ravaan.data.shards import stable_unit

    sample.sort(key=lambda r: stable_unit(r["doc_id"], "review-order"))
    return sample


def _family_summary(rejected: dict[str, list[dict]]) -> str:
    return ", ".join(f"{k}={len(v)}" for k, v in sorted(rejected.items())) or "none"


def write_jsonl(sample: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in sample:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_sheet(sample: list[dict], path: Path, config: QualityConfig) -> None:
    lines: list[str] = [
        "# Stage 5 quality filter — 200-sample manual validation",
        "",
        "PRD §6.3.5 requires the quality rules to be validated against 200 manually inspected "
        "random samples. This is that sample.",
        "",
        f"- Filter: `quality` v1, config fingerprint `{config.fingerprint()}`",
        f"- Documents: {len(sample)} "
        f"({sum(1 for r in sample if r['stratum'] == 'uniform')} uniform, "
        f"{sum(1 for r in sample if r['stratum'] == 'rejected')} rejection-stratified)",
        "",
        "## How to mark this up",
        "",
        "For each document, fill in `**verdict:**` with one of:",
        "",
        "- `keep` — this is text worth training a language model on.",
        "- `drop` — this is boilerplate, junk, the wrong language, or otherwise not worth it.",
        "- `?` — genuinely cannot tell. Abstaining is a real answer; guessing is not.",
        "",
        "Judge the **document**, not the filter. The filter's own verdict is shown so that "
        "disagreements can be found afterwards, but it is not a hint — the whole point is to "
        "catch the cases where it is wrong. `**note:**` is free text and is preserved.",
        "",
        "The two strata are scored separately and must never be pooled: the `uniform` documents "
        "are a random sample of the source, the `rejected` ones are an oversample of what the "
        "filter drops so that each rule has enough documents to measure.",
        "",
        "Then run `python scripts/quality_sample.py score <this file>`.",
        "",
        "---",
        "",
    ]

    for index, record in enumerate(sample, start=1):
        metrics = record["metrics"]
        verdict = "ACCEPT" if record["accepted"] else "REJECT"
        reasons = ", ".join(record["reasons"]) or "—"
        norm = record["normalization_counts"]
        norm_summary = ", ".join(f"{k}={v}" for k, v in list(norm.items())[:8]) or "no change"
        excerpt = record["text"][:EXCERPT_CHARS]
        truncated = len(record["text"]) > EXCERPT_CHARS

        lines += [
            f"### {index} · {record['doc_id']}",
            "",
            f"- **filter:** {verdict} — {reasons}",
            f"- **stratum:** {record['stratum']} · **source:** {record['source']} · "
            f"**stage-3 label:** {record['label']}"
            + (" *(by prior)*" if record["by_prior"] else ""),
            f"- **size:** {metrics['chars']} chars, {metrics['words']} words, "
            f"{metrics['lines']} lines"
            + (f" *(excerpt shows first {EXCERPT_CHARS})*" if truncated else ""),
            f"- **script:** ratio {metrics['script_ratio']:.3f} "
            f"(arabic {metrics['arabic_ratio']:.3f}, latin {metrics['latin_ratio']:.3f})",
            f"- **repetition:** dup_line {metrics['dup_line_ratio']:.3f}, "
            f"top-ngram {max(metrics['top_ngram_ratio'].values(), default=0):.3f}, "
            f"dup-ngram {max(metrics['dup_ngram_ratio'].values(), default=0):.3f}",
            f"- **url** {metrics['url_ratio']:.3f} · **html** {metrics['html_ratio']:.3f} · "
            f"**U+FFFD** {metrics['replacement_rate']:.5f}",
            f"- **stage 4:** {norm_summary}",
        ]
        if record["url"]:
            lines.append(f"- **url:** {record['url']}")
        lines += [
            "",
            "```text",
            excerpt.replace("```", "` ` `"),
            "```",
            "",
            "**verdict:** ",
            "**note:** ",
            "",
            "---",
            "",
        ]

    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------


def parse_sheet(path: Path) -> dict[str, dict[str, str]]:
    """``doc_id -> {"verdict": ..., "note": ...}`` for every block that has been marked."""
    raw = path.read_text(encoding="utf-8")
    out: dict[str, dict[str, str]] = {}
    for match in _BLOCK_RE.finditer(raw):
        body = match.group("body")
        verdict_match = _VERDICT_RE.search(body)
        verdict = (verdict_match.group("verdict") if verdict_match else "").strip().lower()
        note_match = _NOTE_RE.search(body)
        out[match.group("doc_id").strip()] = {
            "verdict": verdict,
            "note": (note_match.group("note") if note_match else "").strip(),
        }
    return out


def rescore(records: list[dict], config: QualityConfig) -> None:
    """Re-apply thresholds to the stored metrics, in place.

    The reason :func:`~ravaan.data.quality.measure` and :func:`~ravaan.data.quality.score` are
    separate functions. Human adjudication is the expensive half of this exercise and it is a
    judgement about *documents*, so it stays valid when a threshold moves; re-reading 40,000
    documents to answer "what would 0.10 have done" would not. This is what lets the sheet be
    marked once and scored against every candidate config.
    """
    for record in records:
        stored = record["metrics"]
        metrics = QualityMetrics(
            chars=stored["chars"],
            words=stored["words"],
            lines=stored["lines"],
            letters=stored["letters"],
            script_ratio=stored["script_ratio"],
            arabic_ratio=stored["arabic_ratio"],
            latin_ratio=stored["latin_ratio"],
            replacement_rate=stored["replacement_rate"],
            url_ratio=stored["url_ratio"],
            html_ratio=stored["html_ratio"],
            dup_line_ratio=stored["dup_line_ratio"],
            top_ngram_ratio=tuple((int(n), v) for n, v in stored["top_ngram_ratio"].items()),
            dup_ngram_ratio=tuple((int(n), v) for n, v in stored["dup_ngram_ratio"].items()),
            repetition_truncated=stored["repetition_truncated"],
        )
        active = config.for_sentences() if record.get("unit") == "sentence" else config
        reasons = quality_score(metrics, active, record["label"])
        record["accepted"] = not reasons
        record["reasons"] = list(reasons)
        record["families"] = list(dict.fromkeys(r.split(":", 1)[0] for r in reasons))
        record["config_fingerprint"] = active.fingerprint()


def score_sheet(sheet: Path, jsonl: Path, config: QualityConfig | None = None) -> dict:
    marks = parse_sheet(sheet)
    records = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line]
    if config is not None:
        rescore(records, config)
    by_id = {r["doc_id"]: r for r in records}

    unknown = sorted(set(marks) - set(by_id))
    for bad in unknown:
        print(f"warning: sheet has a document not in the JSONL: {bad}", file=sys.stderr)

    graded: list[tuple[dict, str]] = []
    invalid: list[str] = []
    for doc_id, mark in marks.items():
        record = by_id.get(doc_id)
        if record is None:
            continue
        verdict = mark["verdict"]
        if not verdict:
            continue
        if verdict not in VERDICTS:
            invalid.append(f"{doc_id}: {verdict!r}")
            continue
        graded.append((record, verdict))

    report: dict = {
        "sheet": str(sheet),
        "config_fingerprint": (config.fingerprint() if config else None),
        "documents_in_sample": len(records),
        "documents_marked": len(graded),
        "documents_unmarked": len(records) - len(graded),
        "invalid_verdicts": invalid,
    }

    for stratum in ("uniform", "rejected"):
        subset = [(r, v) for r, v in graded if r["stratum"] == stratum]
        decided = [(r, v) for r, v in subset if v != "?"]
        matrix = Counter(
            ("accept" if r["accepted"] else "reject", v) for r, v in decided
        )
        agree = matrix[("accept", "keep")] + matrix[("reject", "drop")]
        report[stratum] = {
            "marked": len(subset),
            "abstained": len(subset) - len(decided),
            "agreement": round(agree / len(decided), 4) if decided else None,
            "filter_accept_human_keep": matrix[("accept", "keep")],
            "filter_accept_human_drop": matrix[("accept", "drop")],  # false accept
            "filter_reject_human_keep": matrix[("reject", "keep")],  # false reject
            "filter_reject_human_drop": matrix[("reject", "drop")],
        }

    # Per-family precision: of the documents this rule rejected, how many did the human agree
    # should go. Computed over both strata because a rule's precision is a property of the rule.
    families: dict[str, Counter[str]] = defaultdict(Counter)
    for record, verdict in graded:
        if verdict == "?":
            continue
        for family in record["families"]:
            families[family][verdict] += 1
    report["family_precision"] = {
        family: {
            "rejected": counts["keep"] + counts["drop"],
            "human_agreed_drop": counts["drop"],
            "precision": round(counts["drop"] / (counts["keep"] + counts["drop"]), 4)
            if (counts["keep"] + counts["drop"])
            else None,
        }
        for family, counts in sorted(families.items())
    }

    report["disagreements"] = [
        {
            "doc_id": record["doc_id"],
            "filter": "accept" if record["accepted"] else "reject",
            "human": verdict,
            "reasons": record["reasons"],
            "note": marks[record["doc_id"]]["note"],
            "excerpt": record["text"][:200],
        }
        for record, verdict in graded
        if verdict != "?" and record["accepted"] != (verdict == "keep")
    ]
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)

    drawer = sub.add_parser("draw", help="draw the sample and write the review sheet")
    drawer.add_argument("--out", default="reports/quality_sample", help="output path stem")
    drawer.add_argument("-m", "--manifest", default="data/manifest.json")
    drawer.add_argument("--uniform", type=int, default=100, help="uniform-stratum documents")
    drawer.add_argument("--rejected", type=int, default=100, help="rejection-stratum documents")
    drawer.add_argument(
        "--scan", type=int, default=20_000, help="documents to read per source to draw from"
    )
    drawer.add_argument("--sample-rate", type=float, default=0.02)
    drawer.add_argument("--seed", type=int, default=20260804)
    drawer.add_argument("--quality-config")

    scorer = sub.add_parser("score", help="score a marked-up review sheet")
    scorer.add_argument("sheet", help="the marked-up .md")
    scorer.add_argument("--jsonl", help="the .jsonl beside it (default: same stem)")
    scorer.add_argument(
        "--quality-config",
        help="re-score the stored metrics under this config instead of using the verdicts the "
        "sample was drawn with — how a threshold change is tested against the same adjudication",
    )
    scorer.add_argument("--json", help="write the scoring report here")

    args = parser.parse_args(argv)

    if args.command == "draw":
        sample = draw(args)
        stem = Path(args.out)
        stem.parent.mkdir(parents=True, exist_ok=True)
        config = (
            QualityConfig.from_json_file(args.quality_config)
            if args.quality_config
            else QualityConfig()
        )
        write_jsonl(sample, stem.with_suffix(".jsonl"))
        write_sheet(sample, stem.with_suffix(".md"), config)
        kept = sum(1 for r in sample if r["accepted"])
        print(
            f"\nwrote {len(sample)} documents ({kept} accepted, {len(sample) - kept} rejected) to "
            f"{stem.with_suffix('.jsonl')} and {stem.with_suffix('.md')}",
            file=sys.stderr,
        )
        return 0

    sheet = Path(args.sheet)
    jsonl = Path(args.jsonl) if args.jsonl else sheet.with_suffix(".jsonl")
    config = (
        QualityConfig.from_json_file(args.quality_config) if args.quality_config else None
    )
    report = score_sheet(sheet, jsonl, config)
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    if args.json:
        Path(args.json).write_text(payload + "\n", encoding="utf-8", newline="\n")
    else:
        print(payload)
    print(
        f"\nmarked {report['documents_marked']}/{report['documents_in_sample']}; "
        f"uniform agreement {report['uniform']['agreement']}, "
        f"rejected-stratum agreement {report['rejected']['agreement']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
