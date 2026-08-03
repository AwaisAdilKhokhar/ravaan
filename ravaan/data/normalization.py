"""Urdu text normalization — stage 4 of the corpus pipeline (PRD §6.3).

Three properties this module is built around, in priority order:

1. **Never apply NFKC blindly.** NFKC is the usual shortcut and it is wrong here. It happily
   rewrites `x²` to `x2`, `ﬁ` to `fi`, and `½` to `1⁄2` — none of which is Urdu normalization —
   while *failing* to do the thing Urdu actually needs (unifying the Yeh, Kaf, Heh and Alef
   variants that Arabic keyboards and OCR spray through Urdu corpora). Here NFKC is applied
   character-by-character and only inside the two Arabic presentation-form blocks
   (U+FB50–U+FDFF, U+FE70–U+FEFF), where it is exactly the right tool. Everything else outside
   those blocks is left alone.

2. **Urdu-specific letters survive.** Bari ye (ے U+06D2), bari ye with hamza (ۓ U+06D3), heh
   doachashmee (ھ U+06BE), heh goal (ہ U+06C1), alef with madda (آ U+0622) and the retroflex /
   Indic letters are distinct graphemes carrying meaning. A normalizer that folds ے into ی has
   destroyed the language to make a metric look tidy. Tests lock every one of these down.

3. **Original text, normalized text, and a transformation log are all recoverable.** The PRD
   requires the corpus manifest to state what was changed and how often, so `normalize()` returns
   all three and `NormalizationLog` aggregates counts across a corpus.

Two entry points share one compiled rule set:

* :func:`normalize_text` — fast path (C-level ``str.translate`` + regex), for the 300M-token run.
* :func:`normalize` — same output, plus per-rule counts, for sampling and the manifest.

They are required to agree; ``tests/test_normalization.py`` asserts it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

__all__ = [
    "NORMALIZER_VERSION",
    "DigitStyle",
    "NormalizationConfig",
    "NormalizationResult",
    "NormalizationLog",
    "normalize",
    "normalize_text",
]

# Bump on any change to the *output* of normalization. The corpus manifest records this, so a
# frozen corpus can always be traced back to the exact transform that produced it.
NORMALIZER_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Character inventories
#
# Every mapping below is a deliberate decision, not a Unicode default. Codepoints that Urdu
# needs are listed as PRESERVE_* so the intent is visible in the source and in the tests.
# ---------------------------------------------------------------------------

# --- Yeh family ------------------------------------------------------------
FARSI_YEH = "ی"  # ی — the only "chhoti ye" Urdu writes
YEH_BARREE = "ے"  # ے — "bari ye"; a different letter, never folded
YEH_BARREE_HAMZA = "ۓ"  # ۓ
YEH_HAMZA = "ئ"  # ئ — hamza carrier, a real Urdu grapheme

YEH_VARIANTS = {
    "ي": FARSI_YEH,  # ي ARABIC LETTER YEH — the Arabic-keyboard spelling
    "ى": FARSI_YEH,  # ى ALEF MAKSURA
    "ې": FARSI_YEH,  # ې ARABIC LETTER E (Pashto spill-over)
    "ۍ": FARSI_YEH,  # ۍ YEH WITH TAIL (Pashto spill-over)
    "ؠ": FARSI_YEH,  # ؠ KASHMIRI YEH
}

# --- Kaf / Gaf family ------------------------------------------------------
KEHEH = "ک"  # ک — Urdu kaf
GAF = "گ"  # گ

KAF_VARIANTS = {
    "ك": KEHEH,  # ك ARABIC LETTER KAF
    "ڪ": KEHEH,  # ڪ SWASH KAF (Sindhi/decorative)
    "ڰ": GAF,  # ڰ GAF WITH RING
    "ڲ": GAF,  # ڲ GAF WITH TWO DOTS BELOW
}

# --- Heh family ------------------------------------------------------------
HEH_GOAL = "ہ"  # ہ — Urdu "gol he"
HEH_GOAL_HAMZA = "ۂ"  # ۂ — izafat carrier
HEH_DOACHASHMEE = "ھ"  # ھ — "do-chashmi he"; aspirates. NEVER folded.

HEH_VARIANTS = {
    "ه": HEH_GOAL,  # ه ARABIC LETTER HEH — by far the most common Urdu misspelling
    "ە": HEH_GOAL,  # ە ARABIC LETTER AE
    "ۀ": HEH_GOAL_HAMZA,  # ۀ HEH WITH YEH ABOVE → the Urdu izafat form
}

# Arabic loanword endings. Separate flag: folding these is a judgement call, not a typo fix.
TEH_MARBUTA_VARIANTS = {
    "ة": HEH_GOAL,  # ة
    "ۃ": HEH_GOAL,  # ۃ TEH MARBUTA GOAL
}

# --- Alef family -----------------------------------------------------------
ALEF = "ا"  # ا
ALEF_MADDA = "آ"  # آ — a distinct Urdu letter, never folded

ALEF_VARIANTS = {
    "أ": ALEF,  # أ HAMZA ABOVE
    "إ": ALEF,  # إ HAMZA BELOW
    "ٱ": ALEF,  # ٱ WASLA
    "ٲ": ALEF,  # ٲ WAVY HAMZA ABOVE
    "ٳ": ALEF,  # ٳ WAVY HAMZA BELOW
}

# Letters that must come out the far end byte-identical. Asserted in tests.
PRESERVED_LETTERS = (
    YEH_BARREE
    + YEH_BARREE_HAMZA
    + YEH_HAMZA
    + HEH_DOACHASHMEE
    + HEH_GOAL
    + HEH_GOAL_HAMZA
    + ALEF_MADDA
    + FARSI_YEH
    + KEHEH
    + GAF
    + "پ"  # پ
    + "چ"  # چ
    + "ٹ"  # ٹ
    + "ڈ"  # ڈ
    + "ڑ"  # ڑ
    + "ژ"  # ژ
    + "ں"  # ں
    + "ء"  # ء
    + "۔"  # ۔ Urdu full stop
    + "،"  # ، Arabic comma
    + "؟"  # ؟ Arabic question mark
)

# --- Digits ----------------------------------------------------------------
ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"  # U+0660–U+0669
EXTENDED_ARABIC_INDIC_DIGITS = "۰۱۲۳۴۵۶۷۸۹"  # U+06F0–U+06F9 (the Urdu/Persian shapes)
ASCII_DIGITS = "0123456789"
ARABIC_DECIMAL_SEPARATOR = "٫"  # ٫
ARABIC_THOUSANDS_SEPARATOR = "٬"  # ٬

# --- Invisibles ------------------------------------------------------------
TATWEEL = "ـ"  # ـ kashida; pure typography, carries no phonemic content

ZERO_WIDTH = (
    "​"  # ZERO WIDTH SPACE
    "‍"  # ZERO WIDTH JOINER
    "﻿"  # ZERO WIDTH NO-BREAK SPACE / BOM
    "­"  # SOFT HYPHEN
    "⁠"  # WORD JOINER
    "᠎"  # MONGOLIAN VOWEL SEPARATOR
    "︀︁︂︃︄︅︆︇"  # variation selectors 1–8
    "︈︉︊︋︌︍︎️"  # variation selectors 9–16
)

# ZWNJ is separate: in Persian it is morphemic, in Urdu it is overwhelmingly web noise.
ZWNJ = "‌"

BIDI_MARKS = (
    "‎‏"  # LRM RLM
    "؜"  # ARABIC LETTER MARK
    "‪‫‬‭‮"  # embeddings / overrides / PDF
    "⁦⁧⁨⁩"  # isolates
)

# --- Harakat / annotation marks -------------------------------------------
# Optional and off by default: Urdu writes these rarely and inconsistently, but they are
# information, and stripping them is a corpus decision the config should own.
HARAKAT_RANGES = (
    (0x0610, 0x061A),  # honorifics (ؐ ؑ ؒ …)
    (0x064B, 0x065F),  # tashkil
    (0x0670, 0x0670),  # superscript alef
    (0x06D6, 0x06ED),  # Quranic annotation
)

# --- Presentation forms ----------------------------------------------------
# The ONLY place NFKC is allowed to run. U+FB00–U+FB4F (Latin/Hebrew ligatures) is deliberately
# excluded — `ﬁ` is not Urdu's problem and folding it is not this module's business. Forms-B stops
# at U+FEFC rather than U+FEFF: U+FEFD/U+FEFE are unassigned and U+FEFF is the BOM, which NFKC
# leaves alone and which `zero_width` removes — including it would double-count every BOM.
PRESENTATION_FORMS_RE = re.compile(r"[ﭐ-﷿ﹰ-ﻼ]")

# --- Whitespace ------------------------------------------------------------
_LINE_BREAK_RE = re.compile("\r\n|\r|| | ")
_HORIZONTAL_SPACE_RE = re.compile("[ \t\v\f   -   　]+")
_SPACE_AROUND_NEWLINE_RE = re.compile("[ ]*\n[ ]*")


DigitStyle = Literal["ascii", "urdu", "keep"]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NormalizationConfig:
    """Every transform is individually switchable so the corpus decision is auditable.

    Defaults are the Ravaan corpus v1 settings. Changing any of them changes the corpus, so the
    fingerprint goes into the manifest.
    """

    expand_presentation_forms: bool = True
    unify_yeh: bool = True
    unify_kaf: bool = True
    unify_heh: bool = True
    map_teh_marbuta: bool = True
    unify_alef: bool = True
    remove_tatweel: bool = True
    remove_zero_width: bool = True
    remove_zwnj: bool = True
    remove_bidi_marks: bool = True
    remove_harakat: bool = False
    digits: DigitStyle = "ascii"
    normalize_whitespace: bool = True
    max_consecutive_newlines: int = 2

    def __post_init__(self) -> None:
        if self.digits not in ("ascii", "urdu", "keep"):
            raise ValueError(f"digits must be 'ascii', 'urdu' or 'keep', got {self.digits!r}")
        if self.max_consecutive_newlines < 1:
            raise ValueError("max_consecutive_newlines must be >= 1")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> NormalizationConfig:
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known - {"normalizer_version", "_comment"}
        if unknown:
            raise ValueError(f"unknown normalization config keys: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json_file(cls, path: str | Path) -> NormalizationConfig:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json_file(self, path: str | Path) -> None:
        payload = {"normalizer_version": NORMALIZER_VERSION, **self.to_dict()}
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def fingerprint(self) -> str:
        """Short stable hash over version + settings, for the corpus manifest."""
        payload = json.dumps(
            {"version": NORMALIZER_VERSION, **self.to_dict()}, sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Compiled rule set
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Rules:
    """One translation table plus the rule name each codepoint belongs to.

    All the character-level maps operate on disjoint sets, so they collapse into a single
    ``str.translate`` pass. ``rule_of`` keeps per-rule attribution available for the log.
    """

    table: dict[int, str | None]
    rule_of: dict[int, str]


def _add(
    table: dict[int, str | None],
    rule_of: dict[int, str],
    mapping: dict[str, str | None],
    rule: str,
) -> None:
    for src, dst in mapping.items():
        code = ord(src)
        if code in table:
            raise AssertionError(f"rule {rule!r} collides with {rule_of[code]!r} on U+{code:04X}")
        table[code] = dst
        rule_of[code] = rule


@lru_cache(maxsize=16)
def _compile(config: NormalizationConfig) -> _Rules:
    table: dict[int, str | None] = {}
    rule_of: dict[int, str] = {}

    if config.unify_yeh:
        _add(table, rule_of, dict(YEH_VARIANTS), "yeh")
    if config.unify_kaf:
        _add(table, rule_of, dict(KAF_VARIANTS), "kaf")
    if config.unify_heh:
        _add(table, rule_of, dict(HEH_VARIANTS), "heh")
    if config.map_teh_marbuta:
        _add(table, rule_of, dict(TEH_MARBUTA_VARIANTS), "teh_marbuta")
    if config.unify_alef:
        _add(table, rule_of, dict(ALEF_VARIANTS), "alef")

    if config.remove_tatweel:
        _add(table, rule_of, {TATWEEL: None}, "tatweel")
    if config.remove_zero_width:
        _add(table, rule_of, dict.fromkeys(ZERO_WIDTH, None), "zero_width")
    if config.remove_zwnj:
        _add(table, rule_of, {ZWNJ: None}, "zwnj")
    if config.remove_bidi_marks:
        _add(table, rule_of, dict.fromkeys(BIDI_MARKS, None), "bidi")

    if config.remove_harakat:
        harakat = {chr(c): None for lo, hi in HARAKAT_RANGES for c in range(lo, hi + 1)}
        _add(table, rule_of, harakat, "harakat")

    if config.digits == "ascii":
        digits: dict[str, str | None] = {}
        for family in (ARABIC_INDIC_DIGITS, EXTENDED_ARABIC_INDIC_DIGITS):
            digits.update(dict(zip(family, ASCII_DIGITS, strict=True)))
        digits[ARABIC_DECIMAL_SEPARATOR] = "."
        digits[ARABIC_THOUSANDS_SEPARATOR] = ","
        _add(table, rule_of, digits, "digits")
    elif config.digits == "urdu":
        digits = {}
        for family in (ASCII_DIGITS, ARABIC_INDIC_DIGITS):
            digits.update(dict(zip(family, EXTENDED_ARABIC_INDIC_DIGITS, strict=True)))
        _add(table, rule_of, digits, "digits")

    return _Rules(table=table, rule_of=rule_of)


def _expand_presentation_forms(text: str) -> str:
    """NFKC, applied only inside the Arabic presentation-form blocks. See module docstring."""
    return PRESENTATION_FORMS_RE.sub(lambda m: unicodedata.normalize("NFKC", m.group()), text)


@lru_cache(maxsize=8)
def _newline_run_re(max_newlines: int) -> re.Pattern[str]:
    """Compiled once per distinct cap — this runs over every document in the corpus."""
    return re.compile(f"\n{{{max_newlines + 1},}}")


def _collapse_whitespace(text: str, max_newlines: int) -> str:
    text = _LINE_BREAK_RE.sub("\n", text)
    text = _HORIZONTAL_SPACE_RE.sub(" ", text)
    text = _SPACE_AROUND_NEWLINE_RE.sub("\n", text)
    text = _newline_run_re(max_newlines).sub("\n" * max_newlines, text)
    return text.strip()


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """Original, normalized, and the transformation log the PRD requires us to keep."""

    original: str
    normalized: str
    counts: dict[str, int]
    normalizer_version: str = NORMALIZER_VERSION
    config_fingerprint: str = ""

    @property
    def changed(self) -> bool:
        return self.original != self.normalized

    def to_dict(self) -> dict:
        return {
            "normalized": self.normalized,
            "counts": dict(self.counts),
            "normalizer_version": self.normalizer_version,
            "config_fingerprint": self.config_fingerprint,
        }


@dataclass
class NormalizationLog:
    """Corpus-level aggregate of transformation counts, for the manifest and statistics."""

    config: NormalizationConfig = field(default_factory=NormalizationConfig)
    documents: int = 0
    documents_changed: int = 0
    chars_in: int = 0
    chars_out: int = 0
    counts: Counter[str] = field(default_factory=Counter)

    def add(self, result: NormalizationResult) -> None:
        self.documents += 1
        self.documents_changed += int(result.changed)
        self.chars_in += len(result.original)
        self.chars_out += len(result.normalized)
        self.counts.update(result.counts)

    def to_dict(self) -> dict:
        return {
            "normalizer_version": NORMALIZER_VERSION,
            "config_fingerprint": self.config.fingerprint(),
            "config": self.config.to_dict(),
            "documents": self.documents,
            "documents_changed": self.documents_changed,
            "chars_in": self.chars_in,
            "chars_out": self.chars_out,
            "chars_removed": self.chars_in - self.chars_out,
            "counts": dict(sorted(self.counts.items())),
        }


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = NormalizationConfig()


def normalize_text(text: str, config: NormalizationConfig | None = None) -> str:
    """Fast path: normalized text only. Used for the full corpus run."""
    config = config or _DEFAULT_CONFIG

    if config.expand_presentation_forms:
        text = _expand_presentation_forms(text)

    rules = _compile(config)
    if rules.table:
        text = text.translate(rules.table)

    if config.normalize_whitespace:
        text = _collapse_whitespace(text, config.max_consecutive_newlines)

    return text


def normalize(text: str, config: NormalizationConfig | None = None) -> NormalizationResult:
    """Same output as :func:`normalize_text`, plus per-rule counts.

    Counting costs one ``Counter(text)`` pass, so use this for sampling and manifest statistics
    rather than for every document in a 300M-token corpus.
    """
    config = config or _DEFAULT_CONFIG
    original = text
    counts: Counter[str] = Counter()

    if config.expand_presentation_forms:
        n = len(PRESENTATION_FORMS_RE.findall(text))
        if n:
            counts["presentation_forms"] = n
            text = _expand_presentation_forms(text)

    rules = _compile(config)
    if rules.table:
        char_freq = Counter(text)
        for code, rule in rules.rule_of.items():
            hits = char_freq.get(chr(code), 0)
            if hits:
                counts[rule] += hits
        text = text.translate(rules.table)

    if config.normalize_whitespace:
        before = len(text)
        text = _collapse_whitespace(text, config.max_consecutive_newlines)
        removed = before - len(text)
        if removed:
            counts["whitespace"] = removed

    return NormalizationResult(
        original=original,
        normalized=text,
        counts=dict(counts),
        normalizer_version=NORMALIZER_VERSION,
        config_fingerprint=config.fingerprint(),
    )


# ---------------------------------------------------------------------------
# CLI — normalize a file, print the log to stderr
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("input", nargs="?", help="input file (default: stdin)")
    parser.add_argument("-o", "--output", help="output file (default: stdout)")
    parser.add_argument("-c", "--config", help="normalization config JSON")
    parser.add_argument("--log", help="write the transformation log here as JSON")
    args = parser.parse_args(argv)

    config = (
        NormalizationConfig.from_json_file(args.config) if args.config else NormalizationConfig()
    )
    raw = (
        Path(args.input).read_text(encoding="utf-8")
        if args.input
        else sys.stdin.buffer.read().decode("utf-8")
    )

    result = normalize(raw, config)
    log = NormalizationLog(config=config)
    log.add(result)

    if args.output:
        Path(args.output).write_text(result.normalized, encoding="utf-8")
    else:
        sys.stdout.buffer.write(result.normalized.encode("utf-8"))

    payload = json.dumps(log.to_dict(), indent=2, ensure_ascii=False)
    if args.log:
        Path(args.log).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
