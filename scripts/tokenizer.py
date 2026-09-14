#!/usr/bin/env python
"""Train and benchmark §7's tokenizer — SentencePiece Unigram, 16,384, byte fallback.

The seam stage 10 was built against. `ravaan.data.packing.SentencePieceTokenizer` has existed
since session 12 and needs only a `.model` file; this driver is what produces one. Three
subcommands, because the expensive part is not the training:

* **`sample`** — the only pass that touches the 7.8 GB corpus. Reads through the *same* stages
  2→5 pipeline `scripts/pack.py` uses, applies the stage 6+7 removal lists, and writes a
  mixture-balanced plain-text sample to disk. Minutes-to-hours, once.
* **`train`** — SentencePiece over that sample. Minutes, and repeatable without re-reading the
  corpus, which is what makes vocabulary size or coverage a decision you can revisit.
* **`bench`** — §7's required numbers: tokens-per-word by script, byte-fallback rate,
  compression ratio, and the 95th-percentile sequence length.

**The sample follows §6.1's mixture, not the corpus's own proportions.** The corpus holds `urdu`
at 46.66× its arm A budget and `roman_urdu` at ~1.53×; sampling it as it lies would train the
vocabulary almost entirely on Arabic script and then ask it to encode a Roman-Urdu stream that is
23.53% of what the model actually sees. The budget split here is 120 : 40 : 10 — §6.1's mixture,
the same one stage 9 carves the arms at.

**FineWeb2 is sampled, never prefixed.** `configs/data/sources.json` records that the shard is
not shuffled — row group 0 skews to 2021/2022 dumps and row group 206 to 2024 — so a prefix is a
time-biased slice. `--sample-rate` is a stable per-document hash across the whole shard, which is
the same reason stage 9 uses one. A budget that stops early on an *unsampled* read would
reintroduce exactly the bias Finding E is about.

**Nothing here decides anything about the corpus.** The tokenizer is measured against the corpus
and frozen; it does not filter, drop, or rewrite a document. That is why this driver can run
before stage 8 without owing the freeze anything — see §7's timebox.

Requires the `[data]` extra for parquet sources and `[tokenizer]` for SentencePiece.

    python scripts/tokenizer.py sample --source fineweb2-urd_Arab=0.05 \\
        --source urdu-wikipedia --source roman-urdu-parl=0.10 --limit 0 \\
        --exclude reports/freeze/removals_67_wikipedia.txt \\
        --exclude reports/freeze/removals_67_roman.txt
    python scripts/tokenizer.py train
    python scripts/tokenizer.py bench
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

from ravaan.data.shards import ShardReader  # noqa: E402

# §6.1's mixture: pool targets 120 : 40 : 10, which is what the arms are drawn at. The tokenizer
# sees the stream the model will see, in the proportions the model will see it.
MIXTURE: dict[str, float] = {
    "urdu": 120 / 170,
    "roman_urdu": 40 / 170,
    "code_switched": 10 / 170,
}

DEFAULT_SAMPLE_DIR = Path("data/tokenizer")
DEFAULT_MODEL_PREFIX = "ravaan-16k"

# §5's vocabulary. Duplicated from PackingConfig on purpose — a tokenizer that silently disagreed
# with the packer's dtype ceiling would corrupt the corpus in a way no later stage could see, so
# `train` asserts the two match rather than importing one from the other.
VOCAB_SIZE = 16_384

# §4.1 and §4.2's framing tokens, fixed in the vocabulary rather than bolted on at training time.
#
# `<mask>` is the one that has to be here. MDLM's absorbing state is a token the model embeds and
# attends to, so it either lives inside the 16,384 or the two arms have different vocabularies and
# §4.1's "same parameter count" is broken by the thing the experiment is measuring. Every other
# symbol is here for the same reason in weaker form: §4.2 mixes five objectives whose framings need
# separators, and a separator that the tokenizer splits into three pieces is a separator whose cost
# differs between the arms.
#
# **The AR model never emits most of these and that is fine.** An unused embedding row costs both
# arms the same 640 parameters. A vocabulary that differed between them would not.
SPECIAL_TOKENS: tuple[str, ...] = (
    "<mask>",  # §4.1 — MDLM's absorbing state
    "<sep>",  # §4.1 — `<src> <sep> <tgt>` for the conditional tasks
    "<fim_prefix>",  # §4.1's FIM row, the fix for v1's central flaw
    "<fim_suffix>",
    "<fim_middle>",
    "<lm>",  # §4.2's five objectives, so a sequence carries which one made it
    "<infill>",
    "<translit>",
    "<restore>",
    "<codeswitch>",
    "<ur>",  # transliteration direction, both ways
    "<rom>",
)


# ---------------------------------------------------------------------------
# sample — the pass over the corpus
# ---------------------------------------------------------------------------


class CompactExclusions:
    """`ExclusionSet`'s membership test at 8 bytes an id, and nothing else it does.

    Stage 6+7's Roman-Urdu-Parl list holds 4,307,848 ids. `ExclusionSet` keeps them as a
    ``frozenset`` of strings — right for the deciding stages, which also need the header check
    that catches a list computed over a different read — and that costs roughly 650 MB resident
    with a similar transient on top. **This machine has ~2.7 GB free**, so the deciding stages'
    representation is not affordable here and the sampler would die on the source that matters
    most for the vocabulary.

    So: 64-bit BLAKE2b digests in a sorted array, membership by binary search. The collision
    probability over 4.3M ids is ~5e-7, and a collision drops one extra sentence from a *sample*
    — this driver decides nothing about the corpus, which is what makes the trade legitimate here
    and not in stage 10. Anything that writes a corpus keeps using `ExclusionSet`.
    """

    def __init__(self, paths: list[str]) -> None:
        from array import array as _array  # noqa: PLC0415

        import numpy as np  # noqa: PLC0415

        digests = _array("Q")
        self.declared = 0
        for path in paths:
            with Path(path).open(encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("#"):
                        if line.startswith("#!ravaan-exclusions"):
                            self.declared += json.loads(line.split(" ", 1)[1]).get("count", 0)
                        continue
                    digests.append(self._hash(line))
        self._ids = np.frombuffer(digests, dtype=np.uint64).copy()
        self._ids.sort()
        self._np = np
        self.hits = 0

    @staticmethod
    def _hash(doc_id: str) -> int:
        import hashlib  # noqa: PLC0415

        return int.from_bytes(hashlib.blake2b(doc_id.encode(), digest_size=8).digest(), "big")

    def excludes(self, doc_id: str) -> bool:
        digest = self._hash(doc_id)
        index = int(self._np.searchsorted(self._ids, digest))
        if index < self._ids.size and int(self._ids[index]) == digest:
            self.hits += 1
            return True
        return False

    def __len__(self) -> int:
        return int(self._ids.size)

    def __bool__(self) -> bool:
        return bool(self._ids.size)


def _parse_source(spec: str, default_limit: int | None) -> tuple[str, float | None, int | None]:
    """``NAME[=RATE][@LIMIT]``.

    The per-source limit is not decoration. Populations do not come from every source —
    `roman_urdu` comes only from Roman-Urdu-Parl — and the sampler's stop condition is that *all*
    of them are at budget, so without one the reader keeps running stages 2→5 over another four
    million rows whose population filled an hour ago.
    """
    limit = default_limit
    if "@" in spec:
        spec, _, raw_limit = spec.partition("@")
        limit = int(raw_limit) or None
    name, _, raw = spec.partition("=")
    if not raw:
        return name, None, limit
    rate = float(raw)
    if not 0.0 < rate <= 1.0:
        raise SystemExit(f"--source {spec}: rate must be in (0, 1], got {rate}")
    return name, (None if rate == 1.0 else rate), limit


def cmd_sample(args: argparse.Namespace) -> int:
    # Imported here rather than at module scope: `scripts/pack.py` pulls in the whole stage-2→5
    # stack, and `train`/`bench` have no business paying for it.
    from pack import Pipeline  # noqa: PLC0415

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    budgets = {pop: int(args.chars * share) for pop, share in MIXTURE.items()}
    for override in args.population_chars or ():
        pop, _, value = override.partition("=")
        if pop not in budgets or not value.isdigit():
            raise SystemExit(
                f"--population-chars {override}: expected <population>=<chars> with population "
                f"one of {sorted(budgets)}"
            )
        budgets[pop] = int(value)
    handles = {pop: (out_dir / f"sample_{pop}.txt").open("w", encoding="utf-8") for pop in MIXTURE}
    written = dict.fromkeys(MIXTURE, 0)
    documents = Counter()

    sources = [_parse_source(spec, args.limit or None) for spec in args.source]
    readers = [
        ShardReader.from_manifest(
            name,
            manifest_path=args.manifest,
            split=args.split,
            limit=limit,
            sample_rate=rate,
            seed=args.seed,
        )
        for name, rate, limit in sources
    ]

    exclusions = CompactExclusions(args.exclude)
    if exclusions.declared and exclusions.declared != len(exclusions):
        raise SystemExit(
            f"removal lists declare {exclusions.declared:,} ids and hold {len(exclusions):,} — "
            "a truncated list produces a sample rather than an error"
        )
    print(
        f"sample: {len(readers)} sources, {len(exclusions):,} excluded ids, "
        f"budget {args.chars:,} chars "
        + " ".join(f"{p}={b:,}" for p, b in sorted(budgets.items())),
        file=sys.stderr,
        flush=True,
    )

    started = time.time()
    seen = 0
    try:
        for _doc_id, text, label, _source in Pipeline(readers, exclusions=exclusions):
            seen += 1
            if seen % 200_000 == 0:
                filled = " ".join(
                    f"{p}={written[p] / budgets[p]:.0%}" for p in sorted(budgets) if budgets[p]
                )
                print(
                    f"  {seen:,} docs, {time.time() - started:.0f}s, {filled}",
                    file=sys.stderr,
                    flush=True,
                )
            if args.max_seconds and seen % 2_000 == 0 and time.time() - started >= args.max_seconds:
                print(
                    f"  --max-seconds {args.max_seconds:,} reached — stopping short",
                    file=sys.stderr,
                    flush=True,
                )
                break
            if label not in budgets or written[label] >= budgets[label]:
                continue
            # One line per document. SentencePiece treats a line as a sentence for the purposes
            # of `input_sentence_size`, and the corpus's own line structure is what stage 10 will
            # hand it — collapsing newlines here would train the model on a stream it never sees.
            line = text.replace("\n", " ").strip()
            if not line:
                continue
            handles[label].write(line + "\n")
            written[label] += len(line)
            documents[label] += 1
            if all(written[p] >= budgets[p] for p in budgets):
                print("  every population at budget — stopping", file=sys.stderr, flush=True)
                break
            if args.max_seconds and time.time() - started >= args.max_seconds:
                print(
                    f"  --max-seconds {args.max_seconds:,} reached — stopping short",
                    file=sys.stderr,
                    flush=True,
                )
                break
    finally:
        for handle in handles.values():
            handle.close()

    report = {
        "chars_budget": args.chars,
        "mixture": MIXTURE,
        "population_chars_override": list(args.population_chars or ()),
        "max_seconds": args.max_seconds,
        "stopped_early": bool(
            args.max_seconds and time.time() - started >= args.max_seconds
        ),
        "sources": [{"name": n, "sample_rate": r, "limit": lim} for n, r, lim in sources],
        "exclusions": {
            "lists": [str(p) for p in args.exclude],
            "ids": len(exclusions),
            "hits": exclusions.hits,
        },
        "documents_read": seen,
        "seconds": round(time.time() - started, 1),
        "populations": {
            pop: {
                "chars": written[pop],
                "budget": budgets[pop],
                "documents": documents[pop],
                "filled": round(written[pop] / budgets[pop], 4) if budgets[pop] else None,
            }
            for pop in sorted(budgets)
        },
    }
    (out_dir / "sample.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

    print(f"\nread {seen:,} documents in {report['seconds']:.0f}s", file=sys.stderr)
    for pop in sorted(budgets):
        entry = report["populations"][pop]
        # `filled` is None for a population `--population-chars` set to zero, which is a
        # population deliberately not sampled rather than one that came up short.
        if entry["filled"] is None:
            print(f"  {pop:<14} {'not sampled (budget 0)':>32}", file=sys.stderr)
            continue
        short = "" if entry["filled"] >= 0.999 else "  ← SHORT"
        print(
            f"  {pop:<14} {entry['chars']:>12,} chars  {entry['documents']:>9,} docs  "
            f"{entry['filled']:.1%}{short}",
            file=sys.stderr,
        )
    print(f"wrote {out_dir}/sample_*.txt and sample.json", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# train
# ---------------------------------------------------------------------------


def cmd_train(args: argparse.Namespace) -> int:
    import sentencepiece as spm  # noqa: PLC0415

    sample_dir = Path(args.sample)
    inputs = sorted(sample_dir.glob("sample_*.txt"))
    if not inputs:
        raise SystemExit(f"no sample_*.txt in {sample_dir} — run `tokenizer.py sample` first")
    total = sum(p.stat().st_size for p in inputs)
    print(
        f"train: {len(inputs)} files, {total / 1e6:.0f} MB, vocab {args.vocab_size:,}",
        file=sys.stderr,
        flush=True,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / args.model_prefix

    started = time.time()
    spm.SentencePieceTrainer.train(
        input=[str(p) for p in inputs],
        model_prefix=str(prefix),
        model_type="unigram",
        vocab_size=args.vocab_size,
        # §7: byte fallback, so the vocabulary has no UNK-shaped hole. Urdu diacritics, stray
        # Devanagari and OCR residue all encode; they encode *expensively*, which `bench`
        # reports as the byte-fallback rate rather than hiding as a single unknown token.
        byte_fallback=True,
        character_coverage=args.character_coverage,
        # §7: "minimal destructive normalization". Stage 4 already normalized the corpus and its
        # rules were validated over 200 documents; letting SentencePiece apply NFKC on top would
        # mean the tokenizer's idea of the text and stage 4's disagree, and the offsets stage 10
        # writes would be into a string nobody kept.
        normalization_rule_name="identity",
        remove_extra_whitespaces=False,
        # Control ids fixed here rather than left to defaults, because `eos_id` is the document
        # separator stage 10 writes and a corpus cannot be re-read with a different one.
        pad_id=0,
        unk_id=1,
        bos_id=2,
        eos_id=3,
        user_defined_symbols=list(SPECIAL_TOKENS),
        input_sentence_size=args.input_sentence_size,
        shuffle_input_sentence=True,
        num_threads=args.threads,
        train_extremely_large_corpus=args.large,
    )
    elapsed = time.time() - started

    import hashlib  # noqa: PLC0415

    model = prefix.with_suffix(".model")
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    # Read the ids back off the trained model rather than predicting them. `user_defined_symbols`
    # are placed after the control ids, but "after" is SentencePiece's business and the corpus
    # will be written against whatever it actually chose.
    trained = spm.SentencePieceProcessor(model_file=str(model))
    meta = {
        "model": model.name,
        "sha256": digest,
        "fingerprint": digest[:16],
        "vocab_size": args.vocab_size,
        "model_type": "unigram",
        "byte_fallback": True,
        "character_coverage": args.character_coverage,
        "normalization_rule_name": "identity",
        "control_ids": {"pad": 0, "unk": 1, "bos": 2, "eos": 3},
        "special_tokens": {piece: trained.piece_to_id(piece) for piece in SPECIAL_TOKENS},
        "input_bytes": total,
        "input_files": [p.name for p in inputs],
        "seconds": round(elapsed, 1),
    }
    (out_dir / f"{args.model_prefix}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(
        f"\nwrote {model} in {elapsed:.0f}s\n  fingerprint {digest[:16]}\n"
        f"  stage 10:  python scripts/pack.py --tokenizer {model} …",
        file=sys.stderr,
    )
    return 0


# ---------------------------------------------------------------------------
# bench — §7's reported numbers
# ---------------------------------------------------------------------------


def _script_of(text: str) -> str:
    """Which alphabet a line is in, by letter majority. Coarse on purpose.

    §7 asks for tokens-per-word *by script*, and the sample files are already carved by stage 3's
    label — but a benchmark that trusted the label would be reporting stage 3's opinion rather
    than measuring the text. This counts codepoints.
    """
    arabic = latin = 0
    for char in text:
        if not char.isalpha():
            continue
        name = unicodedata.name(char, "")
        if name.startswith("ARABIC"):
            arabic += 1
        elif name.startswith("LATIN"):
            latin += 1
    if arabic and latin:
        ratio = arabic / (arabic + latin)
        if 0.15 < ratio < 0.85:
            return "mixed"
    return "arabic" if arabic >= latin else "latin"


def cmd_bench(args: argparse.Namespace) -> int:
    import sentencepiece as spm  # noqa: PLC0415

    model_path = Path(args.model)
    sp = spm.SentencePieceProcessor(model_file=str(model_path))
    # Byte-fallback pieces are the 256 `<0xNN>` entries SentencePiece appends after the control
    # ids. Detected by name rather than by id arithmetic so a re-trained model with different
    # control ids still measures the right thing.
    byte_ids = {i for i in range(sp.get_piece_size()) if sp.id_to_piece(i).startswith("<0x")}

    per_script: dict[str, dict[str, float]] = {}
    lengths: list[int] = []

    for path in sorted(Path(args.sample).glob("sample_*.txt")):
        population = path.stem.removeprefix("sample_")
        with path.open(encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if index >= args.lines:
                    break
                line = line.strip()
                if not line:
                    continue
                ids = sp.encode(line, out_type=int)
                script = _script_of(line)
                for key in (population, f"script:{script}"):
                    entry = per_script.setdefault(
                        key, {"tokens": 0, "words": 0, "chars": 0, "bytes": 0, "fallback": 0}
                    )
                    entry["tokens"] += len(ids)
                    entry["words"] += len(line.split())
                    entry["chars"] += len(line)
                    entry["bytes"] += len(line.encode("utf-8"))
                    entry["fallback"] += sum(1 for i in ids if i in byte_ids)
                lengths.append(len(ids))

    report = {
        "model": model_path.name,
        "vocab_size": sp.get_piece_size(),
        "lines_per_file": args.lines,
        "populations": {},
        "sequence_length_p95": int(statistics.quantiles(lengths, n=20)[-1]) if lengths else 0,
        "sequence_length_median": int(statistics.median(lengths)) if lengths else 0,
    }
    for key, entry in sorted(per_script.items()):
        if not entry["tokens"]:
            continue
        report["populations"][key] = {
            "tokens_per_word": (
                round(entry["tokens"] / entry["words"], 4) if entry["words"] else None
            ),
            "chars_per_token": round(entry["chars"] / entry["tokens"], 4),
            "bytes_per_token": round(entry["bytes"] / entry["tokens"], 4),
            "byte_fallback_rate": round(entry["fallback"] / entry["tokens"], 6),
            "tokens": entry["tokens"],
        }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")

    print(f"{model_path.name} — vocab {report['vocab_size']:,}\n", file=sys.stderr)
    print(
        f"{'population':<20}{'tok/word':>10}{'chars/tok':>11}{'byte-fb':>10}{'tokens':>12}",
        file=sys.stderr,
    )
    for key, entry in report["populations"].items():
        tpw = f"{entry['tokens_per_word']:.3f}" if entry["tokens_per_word"] else "—"
        print(
            f"{key:<20}{tpw:>10}{entry['chars_per_token']:>11.3f}"
            f"{entry['byte_fallback_rate']:>10.4%}{entry['tokens']:>12,}",
            file=sys.stderr,
        )
    print(
        f"\nsequence length: median {report['sequence_length_median']}, "
        f"p95 {report['sequence_length_p95']}\nwrote {out}",
        file=sys.stderr,
    )
    # The number stage 9 needs back, in the form `ravaan-splits` takes it.
    cpt = {
        pop: entry["chars_per_token"]
        for pop, entry in report["populations"].items()
        if not pop.startswith("script:")
    }
    if cpt:
        print(
            "\n  ravaan-splits <plan.json> "
            + " ".join(f"--chars-per-token {p}={r:.4f}" for p, r in sorted(cpt.items())),
            file=sys.stderr,
        )
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("sample", help="read the corpus once and write a mixture-balanced sample")
    s.add_argument("--source", action="append", required=True, metavar="NAME[=RATE]")
    s.add_argument("-m", "--manifest", default="data/manifest.json")
    s.add_argument("--split", help="restrict the sources to one acquisition split")
    s.add_argument("--limit", type=int, default=0, help="documents per source; 0 for no limit")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--exclude", action="append", default=[], help="a stage 6/7/8 removal list")
    s.add_argument(
        "--chars",
        type=int,
        default=300_000_000,
        help="total characters to sample, split at §6.1's mixture (default 300M)",
    )
    s.add_argument(
        "--population-chars",
        action="append",
        metavar="POP=CHARS",
        help=(
            "override one population's share of --chars. §6.1's mixture is the default and is "
            "what a tokenizer sample wants; a *corpus* sample may not be able to afford it, "
            "because the populations do not cost the same per character — measured on this "
            "machine, FineWeb2 runs at 321k chars/s through stages 2-5 and Roman-Urdu-Parl at "
            "1.1k, a factor of 280 that falls entirely on document count. Whatever this is set "
            "to lands in sample.json, so the realized mixture is never inferred"
        ),
    )
    s.add_argument(
        "--max-seconds",
        type=float,
        help=(
            "stop and write what has been collected. Without it the loop runs until every "
            "population is at budget or every reader is exhausted, and one slow population can "
            "hold the other two hostage for hours after they finished"
        ),
    )
    s.add_argument("--out", default=str(DEFAULT_SAMPLE_DIR))
    s.set_defaults(func=cmd_sample)

    t = sub.add_parser("train", help="train SentencePiece over the sample")
    t.add_argument("--sample", default=str(DEFAULT_SAMPLE_DIR))
    t.add_argument("--out", default=str(DEFAULT_SAMPLE_DIR))
    t.add_argument("--model-prefix", default=DEFAULT_MODEL_PREFIX)
    t.add_argument("--vocab-size", type=int, default=VOCAB_SIZE)
    t.add_argument("--character-coverage", type=float, default=0.9995)
    t.add_argument("--input-sentence-size", type=int, default=8_000_000)
    t.add_argument("--threads", type=int, default=8)
    t.add_argument("--large", action="store_true", help="train_extremely_large_corpus")
    t.set_defaults(func=cmd_train)

    b = sub.add_parser("bench", help="§7's fertility and byte-fallback numbers")
    b.add_argument("--model", default=str(DEFAULT_SAMPLE_DIR / f"{DEFAULT_MODEL_PREFIX}.model"))
    b.add_argument("--sample", default=str(DEFAULT_SAMPLE_DIR))
    b.add_argument("--lines", type=int, default=50_000, help="lines per population file")
    b.add_argument("--out", default="reports/eval/tokenizer_bench.json")
    b.set_defaults(func=cmd_bench)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
