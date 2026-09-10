#!/usr/bin/env python
"""Does Roman-Urdu-Parl's Roman column say what its Urdu column says?

PRD §6.2 already warns that this source "is substantially machine-produced" and that a
transliteration claim evaluated on it means "matches that transliterator". That is a statement
about *style*. This driver measures something stronger and different: the transliterator emits a
**fixed unrelated word** for some common Urdu words, at most of their occurrences, and the
crowdsourcing step that PRD §6.2 credits with spelling variation propagated the error into every
variant instead of correcting it. See `reports/eval/transliteration_reference_set.md` §5.

Three modes, because the evidence has three different strengths and they must not be quoted as
one number:

* ``screen`` — a **candidate generator with low precision, reported as one.** Flags an Urdu word
  type when some Roman token with no plausible sound-correspondence to it appears in >=30% of its
  rows and occurs >=85% of the time beside it. It cannot tell a substitution from an English
  loanword its crude skeleton fails to match (`فروری`->`feb`), so its output is a list to hand a
  native speaker, not a result.
* ``confirmed`` — the per-word table for a hand-read list, over the complete corpus. Specificity
  P(urdu | substitute) is the column that carries the argument: at 0.87-0.99 the substitute does
  not occur in this corpus except as the rendering of a word it does not mean.
* ``survivors`` — the same list against the freeze's own stage 6+7 removals, which answers whether
  this is a duplication artifact that dedup already handles. It is not.

    python scripts/substitutions.py screen --step 16
    python scripts/substitutions.py confirmed
    python scripts/substitutions.py survivors --removals reports/freeze/removals_67_roman.txt

`--split test` points any mode at the evaluation split instead of the training split.
"""

from __future__ import annotations

import argparse
import collections
import csv
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ravaan.console import pin_utf8_streams  # noqa: E402
from ravaan.data.shards import load_manifest_files  # noqa: E402

pin_utf8_streams()

# CSV fields can be whole documents; the default limit truncates silently.
csv.field_size_limit(1 << 27)

URDU_COLUMN = "Urdu text"
ROMAN_COLUMN = "Roman-Urdu text"
ROMAN_TOKEN = re.compile(r"[A-Za-z']+")

# `scripts/dedup.py` blocks this source's CSV at 10,000 rows, and a removal-list id is
# `source:file:block:row`. Keep the two in step.
CSV_BLOCK_ROWS = 10_000

# Hand-read from `screen`, kept only where the substitute is a common word with an unambiguous
# meaning and its specificity is >= 0.87. Adjudicated by machine, not by a fluent speaker — the
# same posture `quality_validation.md` takes for stage 5 and `neardedup_threshold.md` for stage 7,
# and the report must use those words. `correct` is what a correct rendering would contain; it is
# there to show the correct form is a minority, not to be exhaustive about spellings.
CONFIRMED: dict[str, tuple[str, set[str]]] = {
    "بس": ("dehli", {"bas", "bus"}),
    "کرتے": ("baghaawat", {"kartay", "karte", "karty"}),
    "گھر": ("mamu", {"ghar"}),
    "مت": ("sukh", {"mat"}),
    "چکر": ("post", {"chakkar", "chakar"}),
    "کھلاڑی": ("rgbi", {"khilari", "khilarri", "khilaari"}),
    "لائبریری": ("tromin", {"library", "laibreri"}),
    "انقلاب": ("khatima", {"inqilab", "inqlab"}),
}

# Same shape, same rate, but `ki` is *also* the correct rendering of کی and کہ, so its specificity
# is 0.29 where the rest sit above 0.87. Held apart rather than dropped: excluding it gives the
# conservative reach and including it gives the one the rate actually implies.
AMBIGUOUS: dict[str, tuple[str, set[str]]] = {"یہ": ("ki", {"yeh", "ye", "yih"})}

# Crude Urdu -> Latin consonant skeleton. It exists only to tell a real transliteration from an
# unrelated word and is never used to produce output. `h`, `w` and `y` are kept rather than
# stripped as vowels: without them ہے, ہو and و reduce to nothing and every correct rendering of
# them screens as a substitution. That was this screen's first false-positive family.
SKELETON_MAP = {
    "ا": "a", "آ": "a", "أ": "a", "ب": "b", "پ": "p", "ت": "t", "ٹ": "t", "ث": "s",
    "ج": "j", "چ": "c", "ح": "h", "خ": "k", "د": "d", "ڈ": "d", "ذ": "z", "ر": "r",
    "ڑ": "r", "ز": "z", "ژ": "z", "س": "s", "ش": "s", "ص": "s", "ض": "z", "ط": "t",
    "ظ": "z", "ع": "a", "غ": "g", "ف": "f", "ق": "q", "ک": "k", "ك": "k", "گ": "g",
    "ل": "l", "م": "m", "ن": "n", "ں": "n", "و": "w", "ہ": "h", "ھ": "h", "ة": "h",
    "ی": "y", "ي": "y", "ے": "y", "ء": "",
}
VOWELS = set("aeiou")

_skeletons: dict[tuple[str, bool], str] = {}
_similarities: dict[tuple[str, str], float] = {}

# The screen compares every Urdu token in a row against every Roman one, so the number of distinct
# pairs it sees over 400k rows runs into the tens of millions — an unbounded memo is not a cache,
# it is a slow leak, and on this machine (~0.5 GB free) the first attempt at this pass reached
# 1.2 GB RSS and started thrashing before pass 1 finished. Two things fix it and both matter:
# the key is the *skeleton* pair, not the word pair, which collapses every spelling variant of a
# word onto one entry; and the table is dropped whole when it gets large, which costs a re-derive
# and never costs correctness. Same class of problem as Finding X, one layer up.
# 250k rather than a round million: a dict of 250k short-tuple keys is ~50 MB, and the pass has to
# survive on a machine that reported 0.2 GB free while writing this. The 2M first cut was killed
# without reaching a flush, which is what a memory ceiling looks like from inside.
_CACHE_LIMIT = 250_000


def skeleton(word: str, urdu: bool) -> str:
    key = (word, urdu)
    cached = _skeletons.get(key)
    if cached is None:
        mapped = "".join(SKELETON_MAP.get(c, "") for c in word) if urdu else word.lower()
        mapped = "".join(c for c in mapped if c.isalpha())
        cached = "".join(c for c in mapped if c not in VOWELS) or mapped
        if len(_skeletons) >= _CACHE_LIMIT:
            _skeletons.clear()
        _skeletons[key] = cached
    return cached


def similarity(urdu_word: str, roman_word: str) -> float:
    """0 for an unrelated word, ~1 for a plausible romanization.

    Memoized on the skeleton pair: `کرتے`/`کرتا` and `kartay`/`karte`/`karty` all collapse, which
    is most of what a crowdsourced-spelling corpus contains.
    """
    key = (skeleton(urdu_word, True), skeleton(roman_word, False))
    cached = _similarities.get(key)
    if cached is None:
        cached = difflib.SequenceMatcher(None, key[0], key[1]).ratio()
        if len(_similarities) >= _CACHE_LIMIT:
            _similarities.clear()
        _similarities[key] = cached
    return cached


def resolve(manifest: str, split: str) -> Path:
    files = [f for f in load_manifest_files(manifest, source="roman-urdu-parl", split=split)]
    if len(files) != 1:
        raise SystemExit(f"expected one roman-urdu-parl file for split {split!r}, got {len(files)}")
    return files[0].local_path


def rows_of(path: Path, step: int = 1):
    """Stream ``(index, urdu_tokens, roman_tokens, roman_text)``. Never materializes the corpus."""
    with path.open(encoding="utf-8", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            if step > 1 and index % step:
                continue
            roman = row[ROMAN_COLUMN]
            urdu_tokens = set(row[URDU_COLUMN].split())
            roman_tokens = set(ROMAN_TOKEN.findall(roman.lower()))
            yield index, urdu_tokens, roman_tokens, roman


# ---------------------------------------------------------------------------
# screen
# ---------------------------------------------------------------------------


def run_screen(path: Path, step: int, min_rows: int, max_coverage: float) -> dict:
    """Two passes, because a co-occurrence table over every type would not fit in memory.

    Pass 1 asks only "is this Urdu word ever represented in its own transliteration", which needs
    two counters. Pass 2 builds the association table for the few types that failed, which is
    small. On this machine (~0.5 GB free) the one-pass version is not an option.
    """
    occurrences: collections.Counter = collections.Counter()
    covered: collections.Counter = collections.Counter()
    sampled = 0
    for _, urdu, roman, _ in rows_of(path, step):
        sampled += 1
        for word in urdu:
            occurrences[word] += 1
            if any(similarity(word, r) >= 0.60 for r in roman):
                covered[word] += 1
    suspect = {
        w for w, n in occurrences.items() if n >= min_rows and covered[w] / n <= max_coverage
    }
    print(
        f"pass 1: {sampled:,} rows (1/{step}), {len(occurrences):,} Urdu types, "
        f"{len(suspect):,} suspect",
        flush=True,
    )

    association: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    roman_counts: collections.Counter = collections.Counter()
    for _, urdu, roman, _ in rows_of(path, step):
        hits = suspect & urdu
        for r in roman:
            roman_counts[r] += 1
        for word in hits:
            for r in roman:
                association[word][r] += 1

    candidates = []
    for word in suspect:
        n = occurrences[word]
        for roman_word, count in association[word].most_common(80):
            if similarity(word, roman_word) >= 0.60:
                continue
            p_sub = count / n
            spec = count / roman_counts[roman_word]
            if p_sub >= 0.30 and spec >= 0.85:
                candidates.append(
                    {
                        "urdu": word,
                        "rows": n,
                        "coverage": round(covered[word] / n, 3),
                        "substitute": roman_word,
                        "p_sub_given_urdu": round(p_sub, 3),
                        "p_urdu_given_sub": round(spec, 3),
                    }
                )
                break
    candidates.sort(key=lambda d: -d["rows"])
    print(f"pass 2: {len(candidates)} candidates", flush=True)
    for d in candidates[:40]:
        print(
            f"{d['rows']:>7} {d['coverage']:>5.2f}  {d['urdu']:<14}-> {d['substitute']:<18}"
            f" {d['p_sub_given_urdu']:>5.2f} {d['p_urdu_given_sub']:>5.2f}"
        )
    return {
        "sample_step": step,
        "rows_sampled": sampled,
        "urdu_types": len(occurrences),
        "suspect_types": len(suspect),
        "candidates": candidates,
    }


# ---------------------------------------------------------------------------
# confirmed
# ---------------------------------------------------------------------------


def run_confirmed(path: Path) -> dict:
    every = {**CONFIRMED, **AMBIGUOUS}
    stats = {w: dict(urdu_rows=0, substituted=0, correct=0, substitute_elsewhere=0) for w in every}
    rows = strict_rows = all_rows = 0
    chars = strict_chars = 0
    for _, urdu, roman, text in rows_of(path):
        rows += 1
        chars += len(text)
        for word, (bad, good) in every.items():
            s = stats[word]
            if word in urdu:
                s["urdu_rows"] += 1
                if bad in roman:
                    s["substituted"] += 1
                if good & roman:
                    s["correct"] += 1
            elif bad in roman:
                s["substitute_elsewhere"] += 1
        strict = any(w in urdu and b in roman for w, (b, _) in CONFIRMED.items())
        if strict:
            strict_rows += 1
            strict_chars += len(text)
        if strict or any(w in urdu and b in roman for w, (b, _) in AMBIGUOUS.items()):
            all_rows += 1

    by_word = {}
    print(
        f"\n{'urdu':<12} {'rows':>9} {'sub':>9} {'P(sub|u)':>9} {'correct':>9}"
        f" {'sub elsewhere':>14} {'specificity':>12}"
    )
    for word, (bad, _) in every.items():
        s = stats[word]
        n = max(s["urdu_rows"], 1)
        spec = s["substituted"] / max(s["substituted"] + s["substitute_elsewhere"], 1)
        by_word[word] = {
            "substitute": bad,
            **s,
            "p_sub_given_urdu": s["substituted"] / n,
            "specificity": spec,
            "ambiguous": word in AMBIGUOUS,
        }
        print(
            f"{word:<12} {s['urdu_rows']:>9,} {s['substituted']:>9,}"
            f" {s['substituted'] / n:>9.3f} {s['correct']:>9,}"
            f" {s['substitute_elsewhere']:>14,} {spec:>12.3f}"
        )
    print(
        f"\n{len(CONFIRMED)} high-specificity words: {strict_rows:,} rows"
        f" ({strict_rows / rows:.2%}), {strict_chars / chars:.2%} of Roman characters"
        f"\nincluding the ambiguous one:  {all_rows:,} rows ({all_rows / rows:.2%})"
    )
    return {
        "rows": rows,
        "roman_chars": chars,
        "rows_with_confirmed_substitution": strict_rows,
        "share_of_rows": strict_rows / rows,
        "char_share": strict_chars / chars,
        "rows_including_ambiguous": all_rows,
        "share_including_ambiguous": all_rows / rows,
        "by_word": by_word,
    }


# ---------------------------------------------------------------------------
# survivors
# ---------------------------------------------------------------------------


def run_survivors(path: Path, removals: Path, total_rows: int) -> dict:
    """Are the substituted rows the ones stage 6+7 already deletes? They are not.

    A bitmap over the row index costs 800 KB where a set of 4.3M id strings costs ~400 MB, and the
    machine that has to run this has ~0.5 GB free. Rows dropped by stages 2-5 never reach a removal
    list, so the survivor count here is an upper bound on the frozen set by ~300k rows — which is
    the gap between this count and `reports/freeze/neardedup_roman.json`'s `documents_kept`.
    """
    keep = bytearray(b"\x01") * total_rows
    marked = 0
    with removals.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#!"):
                continue
            parts = line.rstrip("\n").split(":")
            if len(parts) != 4 or not parts[3].isdigit():
                continue
            index = int(parts[2]) * CSV_BLOCK_ROWS + int(parts[3])
            if index < total_rows and keep[index]:
                keep[index] = 0
                marked += 1
    print(f"removal list: {marked:,} rows marked removed of {total_rows:,}", flush=True)

    survivors = hits = 0
    survivor_chars = hit_chars = 0
    for index, urdu, roman, text in rows_of(path):
        if index >= total_rows or not keep[index]:
            continue
        survivors += 1
        survivor_chars += len(text)
        if any(w in urdu and b in roman for w, (b, _) in CONFIRMED.items()):
            hits += 1
            hit_chars += len(text)
    result = {
        "removals_marked": marked,
        "survivors": survivors,
        "survivors_with_substitution": hits,
        "share_of_survivors": hits / max(survivors, 1),
        "survivor_roman_chars": survivor_chars,
        "substituted_chars": hit_chars,
        "char_share_of_survivors": hit_chars / max(survivor_chars, 1),
    }
    print(
        f"survivors {survivors:,}; carrying a confirmed substitution {hits:,}"
        f" ({hits / max(survivors, 1):.2%} of rows, "
        f"{hit_chars / max(survivor_chars, 1):.2%} of characters)"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("mode", choices=("screen", "confirmed", "survivors"))
    parser.add_argument("-m", "--manifest", default="data/manifest.json")
    parser.add_argument("--split", default="train", help="manifest split to read (default: train)")
    parser.add_argument(
        "--step",
        type=int,
        default=16,
        help="screen only: read every Nth row. Discovery tolerates a sample; the confirmed table "
        "does not and never takes one",
    )
    parser.add_argument("--min-rows", type=int, default=60, help="screen only: occurrence floor")
    parser.add_argument(
        "--max-coverage",
        type=float,
        default=0.50,
        help="screen only: flag a word represented in its own transliteration in at most this "
        "share of its rows",
    )
    parser.add_argument("--removals", help="survivors only: a stage 6+7 removal list")
    parser.add_argument(
        "--total-rows",
        type=int,
        default=6_333_218,
        help="survivors only: rows in the split, for the bitmap",
    )
    parser.add_argument("--json", help="write the full result here")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = resolve(args.manifest, args.split)
    print(f"{args.mode}: {path}", flush=True)
    if args.mode == "screen":
        result = run_screen(path, args.step, args.min_rows, args.max_coverage)
    elif args.mode == "confirmed":
        result = run_confirmed(path)
    else:
        if not args.removals:
            raise SystemExit("survivors needs --removals")
        result = run_survivors(path, Path(args.removals), args.total_rows)
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
        )
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
