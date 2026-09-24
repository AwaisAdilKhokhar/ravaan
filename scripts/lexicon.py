#!/usr/bin/env python
"""Build the Urdu word lexicon the generation metrics check against (PRD §8.3).

`ravaan.evaluation.lexicon` answers "is this a word?" by looking the word up, and this is what
it looks it up in: every Arabic-script word skeleton occurring at least twice in the project's
own 712.6M-character native-Urdu sample — the same sources, the same normalizer, and the same
exclusion list the corpus freeze used, so a word the lexicon rejects is one the *training
distribution* does not contain rather than one an external dictionary omits.

**Pruned at build time, and the pruning is the point.** A skeleton seen once in 146M words is as
likely to be OCR residue as a word, and a lexicon that admitted hapaxes would forgive a decoder
for inventing something that happened to collide with one. The count column survives so the
threshold can be raised at load time; it cannot be lowered, and the manifest says so.

**The control is not optional.** A fabrication rate means nothing without the rate real Urdu
scores on the same instrument — a real writer uses words a 712.6M-character sample missed, and that
floor is what a decoder has to be read against. `--control` measures it on held-out documents the
lexicon was not built from and writes it into the manifest.

    python scripts/lexicon.py               # -> reports/eval/urdu_lexicon.tsv.gz + .json
    python scripts/lexicon.py --control     # the same, plus the held-out floor
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ravaan.console import pin_utf8_streams  # noqa: E402

pin_utf8_streams()

from ravaan.data.normalization import NORMALIZER_VERSION, normalize_text  # noqa: E402
from ravaan.evaluation.lexicon import Lexicon, skeleton_words  # noqa: E402

#: 8 MiB at a time. Large enough that the per-chunk regex overhead is noise, small enough that a
#: 1.2 GB file never lands in memory whole.
CHUNK = 8 << 20

#: Documents held back from the build to measure the floor. They are the *first* documents of the
#: held-out split, which is a different corpus file from the build source, so there is no overlap
#: to arrange — but the count is stated because a floor measured on 40 documents is not a floor.
CONTROL_DOCS = 400


def _name(path: Path) -> str:
    """Repo-relative where it can be, absolute otherwise — a manifest must say what it read."""
    try:
        return str(path.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(path)


def chunks(path: Path):
    with path.open(encoding="utf-8", errors="replace") as handle:
        while True:
            chunk = handle.read(CHUNK)
            if not chunk:
                return
            yield normalize_text(chunk)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=REPO / "data/urdu-sample/sample_urdu.txt")
    ap.add_argument("--heldout", type=Path, default=REPO / "data/freeze/heldout_urdu.jsonl")
    ap.add_argument("--out", type=Path, default=REPO / "reports/eval/urdu_lexicon.tsv.gz")
    ap.add_argument("--min-count", type=int, default=2)
    ap.add_argument("--control", action="store_true", help="measure the held-out floor")
    args = ap.parse_args(argv)

    if not args.source.exists():
        raise SystemExit(
            f"{args.source} is not here. The corpus sample is not in the repository — "
            "`data/` is ignored — so this has to run where the freeze lives."
        )

    started = time.perf_counter()
    counts: dict[str, int] = {}
    read = 0
    for chunk in chunks(args.source):
        read += len(chunk)
        for key in skeleton_words(chunk):
            counts[key] = counts.get(key, 0) + 1
        if read % (200 << 20) < CHUNK:
            print(f"  {read / 1e6:.0f}M chars, {len(counts):,} types, "
                  f"{time.perf_counter() - started:.0f}s", file=sys.stderr, flush=True)

    kept = {word: count for word, count in counts.items() if count >= args.min_count}
    manifest = {
        "source": _name(args.source),
        "characters": read,
        "normalizer_version": NORMALIZER_VERSION,
        "word_tokens": sum(counts.values()),
        "types_seen": len(counts),
        "types_kept": len(kept),
        "min_count": args.min_count,
        "seconds": round(time.perf_counter() - started, 1),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.out, "wt", encoding="utf-8") as handle:
        for word, count in sorted(kept.items(), key=lambda kv: (-kv[1], kv[0])):
            handle.write(f"{word}\t{count}\n")
    print(f"wrote {args.out} — {len(kept):,} of {len(counts):,} types "
          f"over {manifest['word_tokens'] / 1e6:.1f}M words", file=sys.stderr)

    if args.control:
        lexicon = Lexicon(set(kept), min_count=args.min_count,
                          types=len(counts), tokens=manifest["word_tokens"])
        total = bad = docs = 0
        with args.heldout.open(encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if index >= CONTROL_DOCS:
                    break
                docs += 1
                result = lexicon.measure(normalize_text(json.loads(line).get("text", "")))
                total += result.words
                bad += result.fabricated
        manifest["control"] = {
            "source": _name(args.heldout),
            "documents": docs,
            "words": total,
            "unknown": bad,
            "rate": round(bad / total, 5) if total else 0.0,
        }
        print(f"control: {bad:,} of {total:,} held-out words unknown "
              f"({bad / total:.4f}) — this is the floor a decoder is read against",
              file=sys.stderr)

    args.out.with_suffix("").with_suffix(".json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
