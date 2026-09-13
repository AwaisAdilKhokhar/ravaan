"""§4.2's corruptions — the text side of the five training tasks (PRD §4.1, §4.2).

§4.2 is explicit that these are made *at training time*: "corruptions are generated dynamically at
training time from clean text, with the generator version and seed recorded." So this module takes
clean corpus text and returns damaged text, deterministically given a seed, and records the version
that produced it. It knows nothing about tokens, batches or either arm — that is
`ravaan.training.tasks`, which frames what this returns into the two arms' input formats.

**The restoration corruption is stage 4 run backwards, and that is a correctness property rather
than an aesthetic one.** §4.2's OCR-and-spacing row needs a (damaged, clean) pair whose clean side
is genuinely the right answer. The cheapest way to be sure of that is to draw the damage from the
exact character families `ravaan.data.normalization` already knows how to undo — the Arabic Yeh and
Kaf spellings, presentation forms, tatweel, zero-width characters, digit variants — and then assert
in a test that ``normalize_text(corrupted) == clean`` for that family. Nothing here has to be
believed: :data:`REVERSIBLE_FAMILIES` is checkable, and `tests/test_corruption.py` checks it.

**And the half that is deliberately not reversible.** A corruption the normalizer can undo is a
corruption a regex can undo, which makes it a poor test of a language model. Real Tesseract output
over Nastaliq loses *dots* — the rasm is shared, so the letters of one tooth family are one shape
plus dot placement — and that is genuine information loss recoverable only from context.
:data:`DOT_CONFUSIONS` is that family and it is the half of the task carrying the signal. The two
are mixed at a configured ratio, so the report can state what fraction of the restoration task was
mechanically invertible instead of leaving a reader to assume it was none.

**Harakat are not injected, on purpose.** `NormalizationConfig.remove_harakat` is False for the
Ravaan corpus — the comment there calls them information — so teaching a restoration model to
delete them would be teaching it to destroy what stage 4 deliberately kept.

**The transliterator is rule-based, and the report must say so.** §6.2 already carries this warning
for Roman-Urdu-Parl: a transliteration claim evaluated against an automatic transliterator means
"matches that transliterator". Training on one means the same thing one step earlier, and §8.2's
human-written set is the only instrument that can measure the gap. Two things make the rule-based
map the right choice here anyway, and both are on the record rather than assumed:

* §4.2 requires dynamic generation from clean text, which stored parallel pairs are not; and
* session 18's Finding AE measured Roman-Urdu-Parl's Roman column rendering eight common Urdu words
  as fixed *unrelated* words at 52–93% of their occurrences, surviving the freeze at 2.77% of rows.
  Its pairs are known-corrupt supervision.

Urdu is an abjad: short vowels are usually unwritten, so a grapheme-level map cannot recover them
and the output is the consonant-heavy Roman that Urdu speakers actually type. That is the register
the task is for. It is not a pronunciation model and does not claim to be.

Standard library only, like the rest of ``ravaan/data`` — this runs inside the training loop on
every host, including the ones with no wheels beyond torch.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import unicodedata
from dataclasses import asdict, dataclass
from functools import lru_cache

from ravaan.data.normalization import (
    ALEF_VARIANTS,
    ARABIC_DECIMAL_SEPARATOR,
    ARABIC_INDIC_DIGITS,
    ARABIC_THOUSANDS_SEPARATOR,
    ASCII_DIGITS,
    BIDI_MARKS,
    EXTENDED_ARABIC_INDIC_DIGITS,
    HEH_VARIANTS,
    KAF_VARIANTS,
    PRESENTATION_FORMS_RE,
    TATWEEL,
    TEH_MARBUTA_VARIANTS,
    YEH_VARIANTS,
    ZERO_WIDTH,
    ZWNJ,
)

# Bump on any change to the *output* of a corruption. `TrainingConfig.task_generator_version`
# records it next to the checkpoints, so a rerun can be shown to have seen the same tasks.
CORRUPTION_VERSION = "1.0.0"

__all__ = [
    "CORRUPTION_VERSION",
    "DOT_CONFUSIONS",
    "INSERTABLE_INVISIBLES",
    "REVERSIBLE_FAMILIES",
    "ROMANIZATION",
    "CorruptionConfig",
    "code_switch",
    "corrupt_ocr",
    "corrupt_restore",
    "corrupt_spacing",
    "romanize",
]


# ---------------------------------------------------------------------------
# Transliteration — native Urdu script to Roman
# ---------------------------------------------------------------------------

# Grapheme to Roman. Where a letter has one uncontroversial rendering it is here; where it depends
# on position in the word, the positional tables below win. The emphatic/Arabic-only distinctions
# Urdu does not pronounce collapse together, because Roman Urdu collapses them — a map that wrote
# `s-with-a-dot` would be a scholarly transliteration of a register nobody types.
ROMANIZATION: dict[str, str] = {
    "ب": "b",   # be
    "پ": "p",   # pe
    "ت": "t",   # te
    "ٹ": "t",   # tte (retroflex)
    "ث": "s",   # se
    "ج": "j",   # jim
    "چ": "ch",  # che
    "ح": "h",   # bari he
    "خ": "kh",  # khe
    "د": "d",   # dal
    "ڈ": "d",   # ddal (retroflex)
    "ذ": "z",   # zal
    "ر": "r",   # re
    "ڑ": "r",   # rre (retroflex)
    "ز": "z",   # ze
    "ژ": "zh",  # zhe
    "س": "s",   # sin
    "ش": "sh",  # shin
    "ص": "s",   # suad
    "ض": "z",   # zuad
    "ط": "t",   # toe
    "ظ": "z",   # zoe
    "ع": "a",   # ain
    "غ": "gh",  # ghain
    "ف": "f",   # fe
    "ق": "q",   # qaf
    "ک": "k",   # keheh
    "گ": "g",   # gaf
    "ل": "l",   # lam
    "م": "m",   # mim
    "ن": "n",   # nun
    "ں": "n",   # nun ghunna
    # Do-chashmi he only ever aspirates the consonant before it. Mapping it to a bare "h" is what
    # produces bh / ph / th / chh / kh / gh for free, with no aspirate table to keep in step.
    "ھ": "h",   # heh doachashmee
    "ہ": "h",   # heh goal
    "ۂ": "ae",  # heh goal with hamza — the izafat carrier
    "و": "o",   # waw
    "ی": "i",   # farsi yeh
    "ے": "e",   # bari ye
    "ا": "a",   # alef
    "آ": "aa",  # alef with madda
    "ئ": "y",   # yeh with hamza
    "ۓ": "e",   # bari ye with hamza
    "ء": "",    # bare hamza carries no consonant of its own
    # Punctuation Urdu writes differently. Stage 4 preserves these, so the Roman side has to make
    # a choice, and Roman Urdu is typed on a Latin keyboard.
    "۔": ".",   # Urdu full stop
    "،": ",",   # Arabic comma
    "؟": "?",   # Arabic question mark
    "؛": ";",   # Arabic semicolon
    "٪": "%",   # Arabic percent sign
}

# Word-initial. An alef carries a vowel rather than being one; waw and yeh are consonants here.
INITIAL_ROMANIZATION: dict[str, str] = {
    "و": "w",
    "ی": "y",
    "ا": "a",
    "آ": "aa",
    "ع": "a",
}

# Word-final. Gol he is the big one: a word ending in it is `-a`, not `-ah`.
FINAL_ROMANIZATION: dict[str, str] = {
    "ہ": "a",
    "و": "o",
    "ی": "i",
    "ے": "e",
}

# Letters that *are* a written vowel. A word-final gol he after one of these is the consonant `h`
# rather than another vowel — the difference between `dargah` and `dargaa`.
VOWEL_CARRIERS = frozenset("اآوىیےۂۓءئ")

# Gol he blocks an inherent vowel before it without being one itself: it is a consonant `h` at the
# front of a word (`hamare`) and a vowel at the end of one (`banda`). So it is in the set that
# stops epenthesis and out of the set that is a vowel.
BLOCKS_EPENTHESIS = VOWEL_CARRIERS | frozenset("ہ")

# Do-chashmi he is neither: it is the aspiration mark on the consonant before it, so nothing may
# be inserted between them. It behaves as a consonant on its own right-hand side, which is what
# turns gaf + do-chashmi he + re into `ghar` rather than `gahr`.
ASPIRATION = "ھ"


def _epenthesize(word: str, position: int) -> bool:
    """Should an inherent short `a` follow the letter at ``position``?

    **Urdu is an abjad and this is the one place that costs something.** Short vowels are simply
    not written, so a bare grapheme map emits `krte` where a Roman-Urdu speaker types `karte` —
    and the cost is not only cosmetic. Measured on the pilot corpus, the unvowelled output
    tokenized to **1.80 tokens per native token**, against a real Roman-Urdu ratio near 0.93,
    because §7's tokenizer learned its Roman pieces from text that has vowels in it. That made the
    transliteration task's source half eat two thirds of the sequence budget *and* put it in a
    register the `roman_urdu` population does not contain.

    Two rules, and they are the conventional ones:

    * a word-initial consonant followed by another consonant always takes one (`hisab`, `kitab`);
    * elsewhere a consonant takes one only when the consonant after it is *not* itself followed by
      a written vowel — which is what puts the `a` in `karte` after the kaf and not after the re.

    It recovers the presence of a vowel and never its quality: `urdu` comes out `ardo` and `kitab`
    comes out `katab`, because the script does not record which vowel it was. That is the ceiling
    on any rule-based transliterator, and it is why §8.2's human-written set is the only instrument
    that can score a transliteration claim.
    """
    char = word[position]
    piece = ROMANIZATION.get(char, "")
    if char in VOWEL_CARRIERS or not piece.isalpha():
        return False
    if position + 1 >= len(word):
        return False
    following = word[position + 1]
    if following in BLOCKS_EPENTHESIS or following == ASPIRATION:
        return False
    if position == 0:
        return True
    after = word[position + 2] if position + 2 < len(word) else None
    return after is None or after not in BLOCKS_EPENTHESIS

# An Arabic-script run: the Arabic block, its supplement, Extended-A, and the Arabic Extended-B
# range Urdu never uses but OCR occasionally produces. Latin, digits and punctuation are outside
# it on purpose — `romanize` has to be a no-op on them for the mixed-script populations.
_WORD_RE = re.compile("[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+")


def romanize(text: str) -> str:
    """Native Urdu script to Roman, grapheme by grapheme. Deterministic, no RNG.

    Anything that is not an Arabic-script letter — Latin, digits, whitespace, ASCII punctuation —
    passes through untouched, which is what makes this usable on the mixed-script documents the
    `code_switched` population is made of.
    """
    if not text:
        return text
    out: list[str] = []
    last = 0
    for match in _WORD_RE.finditer(text):
        out.append(text[last : match.start()])
        out.append(_romanize_word(match.group()))
        last = match.end()
    out.append(text[last:])
    return "".join(out)


@lru_cache(maxsize=200_000)
def _romanize_word(word: str) -> str:
    """One Arabic-script run. Memoized: Urdu's type/token ratio makes this a large win.

    A bounded cache rather than an unbounded one, for the reason `scripts/substitutions.py` gives
    in the same situation — an unbounded memo over a 9.9B-token run is not a cache, it is a leak.
    """
    end = len(word) - 1
    pieces: list[str] = []
    for position, char in enumerate(word):
        if position == 0 and char in INITIAL_ROMANIZATION:
            pieces.append(INITIAL_ROMANIZATION[char])
        elif position == end and char in FINAL_ROMANIZATION:
            # A final gol he after a written vowel is the consonant, not another vowel.
            if char == "ہ" and position and word[position - 1] in VOWEL_CARRIERS:
                pieces.append("h")
            else:
                pieces.append(FINAL_ROMANIZATION[char])
        else:
            pieces.append(ROMANIZATION.get(char, ""))
        if pieces[-1] and _epenthesize(word, position):
            pieces.append("a")
    return "".join(pieces)


# ---------------------------------------------------------------------------
# The reversible damage families — stage 4's inventories, inverted
# ---------------------------------------------------------------------------


def _invert(mapping: dict[str, str]) -> dict[str, tuple[str, ...]]:
    out: dict[str, list[str]] = {}
    for variant, clean in mapping.items():
        out.setdefault(clean, []).append(variant)
    return {clean: tuple(sorted(variants)) for clean, variants in out.items()}


def _variant_substitutions() -> dict[str, tuple[str, ...]]:
    """clean character -> the spellings stage 4 folds back into it."""
    merged: dict[str, list[str]] = {}
    for family in (YEH_VARIANTS, KAF_VARIANTS, HEH_VARIANTS, TEH_MARBUTA_VARIANTS, ALEF_VARIANTS):
        for clean, variants in _invert(dict(family)).items():
            merged.setdefault(clean, []).extend(variants)
    return {clean: tuple(sorted(set(variants))) for clean, variants in merged.items()}


def _digit_substitutions() -> dict[str, tuple[str, ...]]:
    """ASCII digit -> the two Arabic-Indic families stage 4 maps back to it (`digits='ascii'`)."""
    out: dict[str, tuple[str, ...]] = {
        ascii_digit: (arabic, extended)
        for ascii_digit, arabic, extended in zip(
            ASCII_DIGITS, ARABIC_INDIC_DIGITS, EXTENDED_ARABIC_INDIC_DIGITS, strict=True
        )
    }
    out["."] = (ARABIC_DECIMAL_SEPARATOR,)
    out[","] = (ARABIC_THOUSANDS_SEPARATOR,)
    return out


@lru_cache(maxsize=1)
def _presentation_forms() -> dict[str, tuple[str, ...]]:
    """clean text -> the presentation forms whose NFKC expansion is exactly that text.

    Derived by scanning the two blocks `PRESENTATION_FORMS_RE` covers rather than by listing
    shapes: the list is Unicode's, and restating it here would be a second answer to a question
    stage 4 already answers. Ligature forms are kept — the lam-alef shapes expand to two
    characters, which is a real scanned-Nastaliq form and a two-for-one replacement.
    """
    forms: dict[str, list[str]] = {}
    for code in list(range(0xFB50, 0xFE00)) + list(range(0xFE70, 0xFF00)):
        char = chr(code)
        if not PRESENTATION_FORMS_RE.fullmatch(char):
            continue
        expanded = unicodedata.normalize("NFKC", char)
        # Forms whose expansion carries a space — the isolated tashkil shapes at U+FE70 and
        # friends — would come back through whitespace collapse as different text. Out of the
        # reversible family rather than out of Unicode: they are simply not offered here.
        if not expanded or expanded == char or any(c.isspace() for c in expanded):
            continue
        if len(expanded) <= 2:
            forms.setdefault(expanded, []).append(char)
    return {clean: tuple(sorted(set(shapes))) for clean, shapes in forms.items()}


# The invisible characters stage 4 deletes outright. Inserting one is reversible by construction:
# `normalize_text` translates it to None. ZWNJ is listed separately in the normalizer because it
# is morphemic in Persian; in Urdu it is web noise, which is exactly why OCR and copy-paste spray
# it through scanned text.
INSERTABLE_INVISIBLES: tuple[str, ...] = (TATWEEL, ZWNJ, *ZERO_WIDTH, *BIDI_MARKS)

REVERSIBLE_FAMILIES: dict[str, dict[str, tuple[str, ...]]] = {
    "variants": _variant_substitutions(),
    "digits": _digit_substitutions(),
}


# ---------------------------------------------------------------------------
# The lossy damage family — what a regex cannot undo
# ---------------------------------------------------------------------------

# Letters sharing one rasm, separated only by dots. This is what Tesseract loses on scanned
# Nastaliq, and recovering it needs the sentence rather than the character — which is the whole
# reason §4.2 has a restoration task and §8.2 insists its test set be *real* OCR output.
#
# Farsi yeh sits in the first family on purpose: its initial and medial shapes are the same tooth
# as be/pe/te/tte/se/nun, and medial positions are most of a word.
DOT_CONFUSIONS: tuple[tuple[str, ...], ...] = (
    ("ب", "پ", "ت", "ٹ", "ث", "ن", "ی"),
    ("ج", "چ", "ح", "خ"),
    ("د", "ڈ", "ذ"),
    ("ر", "ڑ", "ز", "ژ"),
    ("س", "ش"),
    ("ص", "ض"),
    ("ط", "ظ"),
    ("ع", "غ"),
    ("ف", "ق"),
    ("ک", "گ"),
    ("ہ", "ھ"),
    ("ں", "ن"),
)

# Every family member is a substitution target for every other. Built once; the Arabic-keyboard
# spellings stage 4 *does* fold are deliberately absent, so the two families never overlap and the
# reversibility test cannot be made to pass by accident.
_DOT_ALTERNATIVES: dict[str, tuple[str, ...]] = {}
for _family in DOT_CONFUSIONS:
    for _char in _family:
        _DOT_ALTERNATIVES[_char] = _DOT_ALTERNATIVES.get(_char, ()) + tuple(
            c for c in _family if c != _char
        )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CorruptionConfig:
    """Rates, and the mix between damage a regex can undo and damage it cannot.

    Every rate is drawn *per document* from its range rather than fixed, so the model sees
    clean-ish and badly damaged text in the same run and the restoration task does not collapse
    onto one noise level. §8.2 warns about the same failure from the other end — "training on
    synthetic OCR noise and testing on synthetic OCR noise measures only whether the model learned
    your own noise generator" — and a single fixed rate is the sharpest version of that generator.
    """

    # Per-character probability of an OCR edit, drawn uniformly from this range per document.
    ocr_rate: tuple[float, float] = (0.01, 0.10)
    # Of those edits, the share drawn from DOT_CONFUSIONS and the drop/duplicate family — the half
    # `normalize_text` cannot undo. Recorded so the report can state it rather than imply it.
    ocr_lossy_share: float = 0.5
    # Within the reversible half, how often the damage is an inserted invisible rather than a
    # substituted character. Tatweel and zero-width runs are most of what web Urdu actually has.
    ocr_insert_share: float = 0.35

    # Per-boundary probability of a spacing edit, drawn per document. Urdu's space is not a word
    # boundary the way English's is — compounds and the izafat run either way — so this is the
    # noisiest family in real text and the least mechanically recoverable.
    spacing_rate: tuple[float, float] = (0.02, 0.12)
    spacing_join_share: float = 0.5  # join two words vs. split one

    # Share of whole words romanized for the code-switch task, drawn per document. Below ~10% the
    # task is trivial; above ~60% the "native" target stops being what a speaker would have typed.
    codeswitch_rate: tuple[float, float] = (0.15, 0.45)

    def __post_init__(self) -> None:
        for name in ("ocr_rate", "spacing_rate", "codeswitch_rate"):
            low, high = getattr(self, name)
            if not 0.0 <= low <= high <= 1.0:
                raise ValueError(
                    f"{name} must be an ordered range inside [0, 1], got {(low, high)}"
                )
        for name in ("ocr_lossy_share", "ocr_insert_share", "spacing_join_share"):
            share = getattr(self, name)
            if not 0.0 <= share <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {share}")

    def to_dict(self) -> dict:
        return asdict(self)

    def fingerprint(self) -> str:
        """Short stable hash over version + settings, for the run's ``config.json``."""
        payload = json.dumps({"version": CORRUPTION_VERSION, **self.to_dict()}, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


_DEFAULT = CorruptionConfig()


def _rate(rng: random.Random, span: tuple[float, float]) -> float:
    low, high = span
    return low if low == high else rng.uniform(low, high)


# ---------------------------------------------------------------------------
# The corruptions
# ---------------------------------------------------------------------------


def corrupt_ocr(text: str, rng: random.Random, config: CorruptionConfig | None = None) -> str:
    """Character-level OCR damage: stage 4's families, plus the dots it cannot restore.

    Edits fire independently per character, which is a simplification — real OCR errors cluster by
    line and by scan quality — and one the per-document rate above partly buys back. The
    alternative, a line-correlated noise process, would need real scans to fit, and §8.2 already
    spends eight hours building the hand-corrected set that measures the gap this leaves.
    """
    config = config or _DEFAULT
    if not text:
        return text
    rate = _rate(rng, config.ocr_rate)
    variants = REVERSIBLE_FAMILIES["variants"]
    digits = REVERSIBLE_FAMILIES["digits"]
    forms = _presentation_forms()

    out: list[str] = []
    for char in text:
        if rng.random() >= rate:
            out.append(char)
        elif rng.random() < config.ocr_lossy_share:
            out.append(_lossy_edit(char, rng))
        else:
            out.append(_reversible_edit(char, rng, variants, digits, forms, config))
    return "".join(out)


def _lossy_edit(char: str, rng: random.Random) -> str:
    """A dot confusion where the character has one; otherwise a drop or a duplicate."""
    alternatives = _DOT_ALTERNATIVES.get(char)
    if alternatives:
        return rng.choice(alternatives)
    roll = rng.random()
    if roll < 0.4:
        return ""  # a dropped character — the second most common Tesseract failure on Nastaliq
    if roll < 0.7:
        return char + char
    return char


def _reversible_edit(
    char: str,
    rng: random.Random,
    variants: dict[str, tuple[str, ...]],
    digits: dict[str, tuple[str, ...]],
    forms: dict[str, tuple[str, ...]],
    config: CorruptionConfig,
) -> str:
    """Damage `normalize_text` undoes.

    Falls through to the character unchanged rather than reaching for the lossy family when no
    reversible edit applies: an edit that does not fire is not an error, and forcing one would make
    the reversible/lossy ratio a property of the text rather than of the config, which is exactly
    the number the report has to quote.
    """
    if rng.random() < config.ocr_insert_share:
        # An inserted invisible attaches to the character rather than replacing it, so this is the
        # one edit available regardless of what the character is.
        return char + rng.choice(INSERTABLE_INVISIBLES)
    for table in (variants, digits, forms):
        options = table.get(char)
        if options:
            return rng.choice(options)
    return char


def corrupt_spacing(text: str, rng: random.Random, config: CorruptionConfig | None = None) -> str:
    """Join adjacent words or split one. §4.2's "spacing repair", and it is genuinely lossy.

    Urdu's orthographic word is not its typographic one — compounds, the izafat and the
    postposition are all written with and without a space by fluent writers — so this family is not
    recoverable by rule even in principle. That is why it is in the task rather than in stage 4.
    """
    config = config or _DEFAULT
    words = text.split(" ")
    if len(words) < 2:
        return text
    rate = _rate(rng, config.spacing_rate)

    out: list[str] = [words[0]]
    for word in words[1:]:
        if rng.random() < rate:
            if rng.random() < config.spacing_join_share and out[-1]:
                out[-1] = out[-1] + word  # the space is simply gone
                continue
            if len(word) > 3:
                cut = rng.randrange(1, len(word))
                out.append(word[:cut])
                out.append(word[cut:])
                continue
        out.append(word)
    return " ".join(out)


def corrupt_restore(text: str, rng: random.Random, config: CorruptionConfig | None = None) -> str:
    """§4.2's "OCR and spacing restoration" row: both damage families, in that order.

    OCR first and spacing second, because that is the order a scanned page acquires them — the
    recognizer sees glyphs and only then decides where the gaps between them are.
    """
    config = config or _DEFAULT
    return corrupt_spacing(corrupt_ocr(text, rng, config), rng, config)


def code_switch(text: str, rng: random.Random, config: CorruptionConfig | None = None) -> str:
    """Romanize a random subset of whole words, leaving the rest in native script.

    §4.2's row is code-switch *normalization*: the model is given mixed text and asked for the
    single-script version, so this generates the input and the untouched corpus text is the target.
    Whole words rather than characters — nobody writes half a word in Roman, and a character-level
    mix would be a different phenomenon wearing the same name.
    """
    config = config or _DEFAULT
    rate = _rate(rng, config.codeswitch_rate)

    out: list[str] = []
    last = 0
    for match in _WORD_RE.finditer(text):
        out.append(text[last : match.start()])
        word = match.group()
        out.append(_romanize_word(word) if rng.random() < rate else word)
        last = match.end()
    out.append(text[last:])
    return "".join(out)
