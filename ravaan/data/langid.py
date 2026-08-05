"""Language and script identification — stage 3 of the corpus pipeline (PRD §6.3.3).

Stage 3 decides what "Urdu" means for this project, and it is the last stage where a wrong
default silently changes the corpus rather than the code. PRD §6.1 budgets three populations
separately — native Urdu (~120M tokens), Roman Urdu (~40M), code-switched (~10M) — so this stage
has to *separate* them, not merely accept or reject.

Four decisions, in the order they matter.

**1. Script is measured, language is inferred.** Script comes from Unicode ranges and is exact:
Arabic script is Arabic script. Language is a judgement over evidence, and the two are not the
same question — Urdu, Persian and Arabic share one script, and Roman Urdu and English share
another. Every result therefore carries its script ratios *and* the language scores that produced
the label, so a decision can be argued with rather than taken on faith.

**2. The hard case is Roman Urdu vs English, and it is answered with word lists, not a model.**
The choice is recorded here because it is the one PRD §6.3.3 leaves open. Reasons, in order:
GlotLID and fastText's lid.176 are the obvious off-the-shelf answers, and lid.176 has no Roman
Urdu label at all — it knows `ur` only in Arabic script, so it would label this population as
English, Indonesian or Malay and the corpus would silently lose it. Roman Urdu is also
orthographically unstandardised (*hai / hy / he*, *kya / kia*, *nahi / nahin / nahen*), so what
actually discriminates it is a set of very frequent function words in all their spellings — which
is exactly what a word list is, and what a subword model trained on standardised text is not.
And the alternative costs a 1–3 GB model dependency in a pipeline whose other stages are
standard-library-only, for a decision we can validate directly against Roman-Urdu-Parl.

The failure mode of word lists is collisions, so they are handled explicitly rather than hoped
away: *the*, *is*, *in*, *me*, *us*, *hum*, *par* are ordinary words in both languages.
:data:`AMBIGUOUS_LATIN_WORDS` is computed as the intersection of the two lists and removed from
**both** before scoring, so a collision contributes nothing to either side instead of quietly
voting for whichever list happens to be longer.

**3. Urdu vs Persian vs Arabic is decided on Urdu's own letters first, function words second.**
Function words are treacherous here because stage 3 runs *before* normalization (stage 4): Urdu
typed on an Arabic keyboard writes که for کہ, which is also the Persian word. Folding the variants
first would merge the two languages' evidence rather than separate it. The Urdu-specific letters
— ٹ ڈ ڑ ں ے ھ ہ ۓ ۂ — do not have that problem: they are absent from Arabic and Persian, and they
survive an Arabic keyboard because there is no Arabic key that produces them.

**4. Sentence-level work happens only for mixed documents**, as §6.3.3 specifies. A document whose
minority script clears :attr:`LangIDConfig.mixed_min_ratio` is segmented and each sentence is
labelled, which is what makes the code-switched population extractable instead of merely
detectable. Everything else gets one document-level verdict and no per-sentence cost.

Entry point: :func:`classify`. :class:`LangIDLog` aggregates for the manifest.
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

from ravaan.console import pin_utf8_streams

__all__ = [
    "LANGID_VERSION",
    "Label",
    "Script",
    "LangIDConfig",
    "LangIDResult",
    "LangIDLog",
    "Segment",
    "classify",
    "script_ratios",
    "AMBIGUOUS_LATIN_WORDS",
]

# Bump on any change to which label a document gets. The manifest records it, so a frozen corpus
# can be traced to the exact classifier that split it into populations.
LANGID_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Script measurement
#
# One `str.translate` pass marks every letter with a one-character script code; everything that
# is not a letter is deleted. Counting the marks is then a C-level operation. The table is built
# once at import over the BMP — non-BMP letters (no Urdu concern) fall through untranslated and
# are counted as "other".
# ---------------------------------------------------------------------------

Script = Literal["arabic", "latin", "devanagari", "other"]

_SCRIPT_MARKS: dict[str, str] = {"a": "arabic", "l": "latin", "d": "devanagari", "o": "other"}

# Arabic script proper, plus the two presentation-form blocks. Stage 4 folds the presentation
# forms away, but stage 3 runs first and must not read a page written in them as scriptless.
_ARABIC_RANGES = (
    (0x0600, 0x06FF),  # Arabic
    (0x0750, 0x077F),  # Arabic Supplement
    (0x0870, 0x089F),  # Arabic Extended-B
    (0x08A0, 0x08FF),  # Arabic Extended-A
    (0xFB50, 0xFDFF),  # Presentation Forms-A
    (0xFE70, 0xFEFF),  # Presentation Forms-B
)
_LATIN_RANGES = (
    (0x0041, 0x005A),
    (0x0061, 0x007A),
    (0x00C0, 0x024F),  # Latin-1 Supplement letters through Latin Extended-B
    (0x1E00, 0x1EFF),  # Latin Extended Additional
)
_DEVANAGARI_RANGES = ((0x0900, 0x097F),)  # Hindi — the same language in another script


def _build_script_table() -> dict[int, str | None]:
    """Codepoint → script mark, or ``None`` for "not a letter, ignore".

    Ratios are taken over *letters* only. Digits, punctuation and whitespace are shared between
    scripts and would otherwise let a page of numbers and URLs outvote its own prose.
    """
    table: dict[int, str | None] = {}
    ranged: list[tuple[tuple[tuple[int, int], ...], str]] = [
        (_ARABIC_RANGES, "a"),
        (_LATIN_RANGES, "l"),
        (_DEVANAGARI_RANGES, "d"),
    ]
    for ranges, mark in ranged:
        for start, end in ranges:
            for code in range(start, end + 1):
                if unicodedata.category(chr(code)).startswith("L"):
                    table[code] = mark
    for code in range(0x10000):
        if code in table:
            continue
        table[code] = "o" if unicodedata.category(chr(code)).startswith("L") else None
    return table


_SCRIPT_TABLE = _build_script_table()


def script_ratios(text: str) -> tuple[dict[str, float], int]:
    """``({script: share of letters}, letter count)``. Shares sum to 1 when there are letters."""
    marks = text.translate(_SCRIPT_TABLE)
    if not marks:
        return {}, 0
    counts = Counter(marks)
    total = len(marks)
    ratios: dict[str, float] = {}
    for mark, count in counts.items():
        name = _SCRIPT_MARKS.get(mark, "other")
        ratios[name] = ratios.get(name, 0.0) + count / total
    return ratios, total


# ---------------------------------------------------------------------------
# Arabic-script language evidence
# ---------------------------------------------------------------------------

# Letters Urdu writes that Arabic and Persian do not. This is the primary signal: unlike function
# words, an Arabic keyboard cannot produce them by accident, and Urdu prose cannot avoid them —
# ہے, ہیں, کے, نے and ں are unavoidable in any two sentences of Urdu.
URDU_LETTERS = "ٹڈڑںےۓہۂھ"

# Letters that mark Arabic and are rare-to-absent in correct Urdu. ي and ك *do* appear in
# Arabic-keyboard Urdu, which is precisely the confusion stage 4 exists to fix, so they are
# weighted through the word lists rather than counted as decisive on their own.
ARABIC_LETTERS = "ةًٌٍأإؤئى"

# Persian has no exclusive letters against Urdu (Urdu is a superset), so Persian is carried
# entirely by function words.

_ARABIC_SCRIPT_WORD_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿ]+")

URDU_WORDS = frozenset(
    """
    ہے ہیں ہو ہوا ہوئی ہوئے ہونے تھا تھی تھے کے کی کا کو نے سے میں پر اور یہ وہ کہ بھی نہیں
    گیا گئی گئے کیا کرنے کرنا کرتے کرتی کرتا لیے لئے ساتھ اس ان ایک ہر جو جس تک بعد دیا رہے
    رہا رہی ہمیں انہوں انہیں والے والی والا کچھ سب پھر اگر لیکن مگر آپ ہم تم میرے اپنے اپنی
    بہت زیادہ کیوں کیسے کہاں جب تب صرف طرح بارے دوران خلاف بجائے علاوہ
    """.split()  # noqa: SIM905 - a word list reads as words
)

PERSIAN_WORDS = frozenset(
    """
    است این آن را که های برای می هم ما شما بود شد کرد خود دیگر بسیار هستند نیست چه کجا آیا
    توسط بین درباره باشد کنید کند شود شده کرده بودند آنها یک هر ولی اگر اما چون تا روی نیز
    """.split()  # noqa: SIM905 - a word list reads as words
)

ARABIC_WORDS = frozenset(
    """
    في من على عن إلى هذا هذه التي الذي أن إن كان قد لا ما بين بعد كل هو هي كما حيث لكن عند
    أو ثم كانت يكون تكون التي الذين ذلك تلك أي بها به له لها منذ حتى وقد وقال أيضا نحن أنا
    """.split()  # noqa: SIM905 - a word list reads as words
)


@dataclass(frozen=True, slots=True)
class ArabicScriptScores:
    """Evidence for each Arabic-script language, on a common per-unit scale."""

    urdu: float = 0.0
    persian: float = 0.0
    arabic: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: round(v, 5) for k, v in asdict(self).items()}


def _score_arabic_script(text: str, letters: int, config: LangIDConfig) -> ArabicScriptScores:
    words = _ARABIC_SCRIPT_WORD_RE.findall(text)
    if not words:
        return ArabicScriptScores()
    total = len(words)

    urdu_words = sum(1 for w in words if w in URDU_WORDS)
    persian_words = sum(1 for w in words if w in PERSIAN_WORDS)
    arabic_words = sum(1 for w in words if w in ARABIC_WORDS)

    # Letter evidence is a *rate over letters*, word evidence a rate over words; both land in
    # [0, 1]. The Urdu letter rate is multiplied up because even dense Urdu prose is only ~8-12%
    # Urdu-specific letters, so an unscaled rate would always lose to a word rate.
    urdu_letters = sum(text.count(ch) for ch in URDU_LETTERS) / letters if letters else 0.0
    arabic_letters = sum(text.count(ch) for ch in ARABIC_LETTERS) / letters if letters else 0.0

    return ArabicScriptScores(
        urdu=urdu_words / total + config.urdu_letter_weight * urdu_letters,
        persian=persian_words / total,
        arabic=arabic_words / total + config.arabic_letter_weight * arabic_letters,
    )


# ---------------------------------------------------------------------------
# Latin-script language evidence — Roman Urdu vs English
# ---------------------------------------------------------------------------

_LATIN_WORD_RE = re.compile(r"[A-Za-z][A-Za-z']*")

# Function words and their common spellings. Roman Urdu has no orthography, so the variants are
# the point: a list holding only `hai` and `nahin` matches a fraction of real usage.
_ROMAN_URDU_RAW = frozenset(
    """
    hai hain hy hain hein han haan ha nahi nahin nahen nai nahe ka ke ki ko se me mein main
    aur ya ye yeh wo woh kya kia kyun kyu kis kisi kuch kuchh sab bhi bhe bohat bahut boht
    bht zyada ziada tha thi thay thee thy hua hui huay hue hona ho gaya gaye gai gayi raha
    rahi rahe rha kar karna karne karta karti kartay kiya kre kro liye liay lye sath saath
    phir agar magar lekin par per jo jis us is un in un ap aap tum tumhe hum ham humein
    hamein mera meri mere tera teri apna apni apne uska uski unka unki humara hamara kaise
    kesa kaisa kab kahan kaha kitna kitni acha achha achi theek thik bilkul zaroor shayad
    matlab baat baten kaam waqt din raat ghar dost pyar dil zindagi khuda allah insan log
    logo logon bhai behen ammi abbu beta beti sahab sahib janab shukriya khush dukh mushkil
    asan chahiye chahye chaiye milta milti karo kero dekha dekhi dekho suno bola boli kehna
    kehta kehte pata malum sirf abhi kabhi hamesha jaldi thora thoda bara bari chota choti
    naya nayi purana purani accha
    aik ek ne nay na nah hi hee hun hoon hon tak jab tab ab koi koe kai kayi har hr wala wali
    walay walon jaise jese waise mujhe mujhy tujhe unhon inhon sakta sakte sakti laga lagi lage
    diya di dena lena liya rakha rakhi bana bani banaya huwa huway saal mahina hafta subah
    shaam raat behtar bara sath andar bahar upar neeche pehle baad darmiyan taraf tarah
    the to or he us do main so say
    """.split()  # noqa: SIM905 - a word list reads as words
)
# The last line is not a mistake. Those nine are frequent Roman Urdu words — *the* (they were),
# *to* (then), *or* (and), *he* (is), *us* (that), *do* (two), *main* (I / in), *so* (sleep),
# *say* (from) — and they are also frequent English words. They are listed so the intersection
# below *removes* them from both sides. Leaving them out would silently hand the strongest
# English signals to English, which is the same bug in a quieter form.
#
# The rest of the list is not guesswork either. It was extended by mining the sentences that the
# first version failed to label in Roman-Urdu-Parl's validation split and taking the words those
# sentences were made of: *aik*, *ne*, *na*, *hi*, *hon*, *tak*, *koi* are among the most frequent
# words in the language and were simply missing. That loop — measure on the labelled source,
# read the misses, extend — is the only thing that makes a word list defensible.

_ENGLISH_RAW = frozenset(
    """
    the of and to in is it that for was on with as are be this have from at by not but or an
    they we you he she his her all would there their what so up out if about who which when
    will can has had more one been my me no do does did said than then them these into over
    only also its may such other some time could our your any first new like now people than
    after most made where how because been being were said very much many should must under
    between while during before same both each own too still every another however
    us do main so per say
    """.split()  # noqa: SIM905 - a word list reads as words
)

# Words that are ordinary in *both* languages: `the` (English article / Roman Urdu "they were"),
# `is` (English copula / Roman Urdu "this"), `me` ("in"), `us` ("that"), `par` ("on"), `in`
# ("these"), `hum`. A collision is not evidence, so it is removed from both sides rather than
# left to vote for whichever list is longer. Kept public because it is the classifier's main
# known weakness and belongs in the report.
AMBIGUOUS_LATIN_WORDS: frozenset[str] = _ROMAN_URDU_RAW & _ENGLISH_RAW

ROMAN_URDU_WORDS: frozenset[str] = _ROMAN_URDU_RAW - AMBIGUOUS_LATIN_WORDS
ENGLISH_WORDS: frozenset[str] = _ENGLISH_RAW - AMBIGUOUS_LATIN_WORDS


@dataclass(frozen=True, slots=True)
class LatinScriptScores:
    """Evidence for each Latin-script language, as a share of Latin words matched.

    ``lowercase`` is not a language score — it is how the Latin side tells *running text* from
    *names*. See :func:`_score_latin_script`.
    """

    roman_urdu: float = 0.0
    english: float = 0.0
    lowercase: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {k: round(v, 5) for k, v in asdict(self).items()}


def _score_latin_script(text: str) -> LatinScriptScores:
    """Score the Latin words, and measure how many of them are lowercase.

    The lowercase rate is what separates a code-switched sentence from an Urdu sentence
    containing a foreign name, and it was added because the classifier got that wrong on real
    text: Urdu Wikipedia's geographic stubs — "سینٹ-موریس، ہوتے-مرنے (فرانسیسی: Saint-Maurice,
    Haute-Marne) فرانس کا ایک فرانسیسی کمیون" — are a quarter Latin letters by volume, so 30% of
    Urdu Wikipedia came out labelled code-switched on the first run. They are not bilingual
    documents; they are Urdu sentences with a French place name in them.

    Names are capitalised and embedded content words are not: those stubs score 0.0 here, while
    real switching ("meeting kal schedule ہے، deadline کے بارے میں team نے final decision نہیں
    کیا") scores 1.0. Function-word lists cannot make this distinction, because embedded English
    in Urdu is almost entirely *content* words.
    """
    words = _LATIN_WORD_RE.findall(text)
    if not words:
        return LatinScriptScores()
    total = len(words)
    lowered = [w.lower() for w in words]
    return LatinScriptScores(
        roman_urdu=sum(1 for w in lowered if w in ROMAN_URDU_WORDS) / total,
        english=sum(1 for w in lowered if w in ENGLISH_WORDS) / total,
        lowercase=sum(1 for w in words if w.islower() and len(w) > 1) / total,
    )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

Label = Literal[
    "urdu",  # native Urdu, Arabic script — PRD §6.1's ~120M-token population
    "roman_urdu",  # Urdu in Latin script — ~40M
    "code_switched",  # both, meaningfully — ~10M
    "english",
    "arabic",
    "persian",
    "hindi",  # Devanagari: the same language, the wrong script for this corpus
    "other",  # another script, or Latin/Arabic text no list explains
    "empty",  # too little text to decide
]

KEPT_LABELS: frozenset[str] = frozenset({"urdu", "roman_urdu", "code_switched"})


@dataclass(frozen=True, slots=True)
class LangIDConfig:
    """Thresholds for stage 3. Defaults are the Ravaan corpus v1 settings.

    The defaults are deliberately *asymmetric*: a document is kept as Urdu unless there is
    positive evidence for another language, but it is only labelled Persian or Arabic when that
    evidence beats Urdu's by ``min_margin``. Urdu is not scarce here — ~5B tokens are collectable
    against a ~120M-token target (PRD §6.1) — so a false accept costs a little corpus quality and
    a false reject costs corpus *composition*: religious and legal Urdu quotes Arabic heavily, and
    a classifier tuned to reject Arabic-looking text would strip a register rather than a
    language.
    """

    min_letters: int = 20
    # One knob, not two. An earlier draft also carried a `dominant_script_ratio`, which is the
    # same boundary written from the other end — and two names for one threshold is how a band
    # of documents ends up matching neither rule and falling through to `other` with nothing
    # having decided it. A span is mixed when its minority scripts reach this share, and
    # single-script otherwise. There is no third case.
    mixed_min_ratio: float = 0.10
    min_margin: float = 0.02
    # How much function-word evidence a label needs before it beats "nothing decided this".
    # 0.08 = roughly one function word in twelve. English and Roman Urdu prose run 0.30–0.50, so
    # the bar is nowhere near them; what it excludes is Latin-script *furniture* — navigation
    # bars, category lists, product tables — which scores about 0.06 and would otherwise make
    # every Urdu page with a menu look like a bilingual document and land it in the
    # code-switched population instead of the native one.
    min_evidence: float = 0.08
    urdu_letter_weight: float = 4.0
    arabic_letter_weight: float = 2.0
    sentence_min_letters: int = 8
    # Share of Latin tokens that must be lowercase before a mixed span counts as switching
    # rather than Urdu quoting a name. Real switching runs ~0.9; Urdu Wikipedia's French place
    # names run 0.0. Anywhere in between is a judgement call and 0.5 is the middle of it.
    latin_running_text_rate: float = 0.50
    # Share of letters in *internally mixed* sentences that makes a document code-switched.
    # Intra-sentential switching is unambiguous evidence, so the bar is low.
    code_switch_min_share: float = 0.10
    # Share of letters in monolingual sentences of the *other* language that makes an
    # alternating document code-switched. Much higher, and measured rather than chosen: across
    # 1,920 mixed Urdu Wikipedia articles the English share has a sharp mode at 0.10–0.20
    # (1,064 documents) that is not bilingual writing at all — it is the English reference list
    # and category footer every Wikipedia article carries. The distribution then collapses
    # (298 documents at 0.20–0.30, 39 at 0.30–0.40), so 0.30 sits in the valley after the
    # artifact and keeps genuinely bilingual documents on the far side of it.
    alternation_min_share: float = 0.30
    max_segments: int = 400

    def __post_init__(self) -> None:
        for name in ("mixed_min_ratio", "code_switch_min_share", "alternation_min_share"):
            value = getattr(self, name)
            if not 0.0 < value <= 1.0:
                raise ValueError(f"{name} must be in (0, 1], got {value!r}")
        for name in ("min_margin", "min_evidence"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value!r}")
        if self.min_letters < 1:
            raise ValueError("min_letters must be >= 1")
        if self.mixed_min_ratio > 0.5:
            # Above 0.5 no document can be mixed: the minority share of a two-script document is
            # at most 0.5 by definition, so the sentence-level pass would never run and the
            # code-switched population would be silently empty rather than absent.
            raise ValueError(f"mixed_min_ratio must be <= 0.5, got {self.mixed_min_ratio}")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> LangIDConfig:
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known - {"langid_version", "_comment"}
        if unknown:
            raise ValueError(f"unknown langid config keys: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json_file(cls, path: str | Path) -> LangIDConfig:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json_file(self, path: str | Path) -> None:
        payload = {"langid_version": LANGID_VERSION, **self.to_dict()}
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"version": LANGID_VERSION, **self.to_dict()}, sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Segment:
    """One sentence of a mixed document, with its own label."""

    label: Label
    text: str
    letters: int

    def to_dict(self) -> dict:
        return {"label": self.label, "letters": self.letters, "text": self.text}


@dataclass(frozen=True, slots=True)
class LangIDResult:
    """One document's label, with the evidence that produced it."""

    label: Label
    scripts: dict[str, float] = field(default_factory=dict)
    letters: int = 0
    margin: float = 0.0
    arabic_scores: ArabicScriptScores = field(default_factory=ArabicScriptScores)
    latin_scores: LatinScriptScores = field(default_factory=LatinScriptScores)
    segments: tuple[Segment, ...] = ()
    # True when the label came from the prior rather than from evidence — Arabic-script text with
    # no function words in it is called Urdu because that is what an Urdu-filtered corpus mostly
    # is, and the corpus statistics should say how much of it was decided that way.
    by_prior: bool = False
    langid_version: str = LANGID_VERSION
    config_fingerprint: str = ""

    @property
    def kept(self) -> bool:
        """Whether the document belongs to one of PRD §6.1's three budgeted populations."""
        return self.label in KEPT_LABELS

    @property
    def dominant_script(self) -> str:
        return max(self.scripts, key=self.scripts.__getitem__) if self.scripts else "none"

    def segment_letters(self) -> dict[str, int]:
        """Letters per label across segments — how a code-switched document splits."""
        out: Counter[str] = Counter()
        for segment in self.segments:
            out[segment.label] += segment.letters
        return dict(out)

    def to_dict(self, include_segments: bool = False) -> dict:
        payload = {
            "label": self.label,
            "kept": self.kept,
            "by_prior": self.by_prior,
            "letters": self.letters,
            "margin": round(self.margin, 5),
            "scripts": {k: round(v, 5) for k, v in self.scripts.items()},
            "arabic_scores": self.arabic_scores.to_dict(),
            "latin_scores": self.latin_scores.to_dict(),
            "langid_version": self.langid_version,
            "config_fingerprint": self.config_fingerprint,
        }
        if self.segments:
            payload["segment_letters"] = self.segment_letters()
            if include_segments:
                payload["segments"] = [s.to_dict() for s in self.segments]
        return payload


@dataclass
class LangIDLog:
    """Corpus-level aggregate — the stage-3 line of the manifest and the statistics table."""

    config: LangIDConfig = field(default_factory=LangIDConfig)
    documents: int = 0
    documents_kept: int = 0
    documents_by_prior: int = 0
    letters: int = 0
    labels: Counter[str] = field(default_factory=Counter)
    letters_by_label: Counter[str] = field(default_factory=Counter)
    segment_letters: Counter[str] = field(default_factory=Counter)
    mixed_documents: int = 0

    def add(self, result: LangIDResult) -> None:
        self.documents += 1
        self.labels[result.label] += 1
        self.letters += result.letters
        self.letters_by_label[result.label] += result.letters
        if result.kept:
            self.documents_kept += 1
        if result.by_prior:
            self.documents_by_prior += 1
        if result.segments:
            self.mixed_documents += 1
            for label, letters in result.segment_letters().items():
                self.segment_letters[label] += letters

    @property
    def keep_rate(self) -> float:
        return self.documents_kept / self.documents if self.documents else 0.0

    def to_dict(self) -> dict:
        return {
            "langid_version": LANGID_VERSION,
            "config_fingerprint": self.config.fingerprint(),
            "config": self.config.to_dict(),
            "documents": self.documents,
            "documents_kept": self.documents_kept,
            "keep_rate": round(self.keep_rate, 6),
            "documents_by_prior": self.documents_by_prior,
            "prior_rate": round(
                self.documents_by_prior / self.documents if self.documents else 0.0, 6
            ),
            "mixed_documents": self.mixed_documents,
            "letters": self.letters,
            "labels": dict(sorted(self.labels.items())),
            "letters_by_label": dict(sorted(self.letters_by_label.items())),
            "segment_letters": dict(sorted(self.segment_letters.items())),
        }


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = LangIDConfig()

# Urdu ends sentences with ۔ (U+06D4), asks with ؟ (U+061F). The Latin full stop is included for
# Roman Urdu and for mixed text; the Urdu comma ٫ and ، are *not* sentence ends.
_SENTENCE_SPLIT_RE = re.compile(r"[۔؟?!.]+[\s‏‎]*|\n+")


@lru_cache(maxsize=16)
def _fingerprint(config: LangIDConfig) -> str:
    return config.fingerprint()


def _argmax(scores: dict[str, float]) -> tuple[str, float, float]:
    """``(best label, best score, margin over the runner-up)``."""
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    best, top = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    return best, top, top - second


def _label_arabic_script(
    scores: ArabicScriptScores, config: LangIDConfig
) -> tuple[Label, float, bool]:
    """``(label, margin, decided_by_prior)``.

    The third element is the honest part. Arabic-script text with no function words in it —
    headings, name lists, poetry fragments, tables — gets labelled Urdu because that is the
    prior for an Urdu-filtered corpus, not because anything was measured. The flag is aggregated
    into :class:`LangIDLog` so the manifest can state what share of the corpus was classified on
    evidence and what share was waved through, instead of reporting one number for both.
    """
    best, top, margin = _argmax(
        {"urdu": scores.urdu, "persian": scores.persian, "arabic": scores.arabic}
    )
    if top < config.min_evidence:
        return "urdu", 0.0, True
    if margin < config.min_margin:
        return "urdu", margin, True
    return best, margin, False  # type: ignore[return-value]


def _label_latin_script(
    scores: LatinScriptScores, config: LangIDConfig
) -> tuple[Label, float, bool]:
    best, top, margin = _argmax({"roman_urdu": scores.roman_urdu, "english": scores.english})
    if top < config.min_evidence or margin < config.min_margin:
        # Latin script that neither list explains: product listings, transliterated names,
        # another Latin-script language entirely. Not Roman Urdu on the evidence available —
        # and `other` says exactly that, rather than guessing.
        return "other", margin, True
    return best, margin, False  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class _Span:
    """A labelled piece of text — a whole document or one sentence of a mixed one."""

    label: Label
    margin: float
    arabic: ArabicScriptScores
    latin: LatinScriptScores
    scripts: dict[str, float]
    letters: int
    by_prior: bool = False


def _label_span(text: str, config: LangIDConfig) -> _Span:
    """Label a span of any script mixture.

    Both scorers run over their own token populations — the Arabic-script word regex cannot match
    a Latin word and vice versa — so a mixed span gets an independent verdict per side and the
    two are combined here. This is where intra-sentential code-switching is caught, and it is the
    case that matters: Urdu–English switching is overwhelmingly *within* the sentence ("meeting
    kal schedule ہے"), so a classifier that only compared whole sentences would label the common
    case as plain Urdu and the ~10M-token population of PRD §6.1 would never be separable.
    """
    ratios, letters = script_ratios(text)
    if not letters:
        return _Span("empty", 0.0, ArabicScriptScores(), LatinScriptScores(), ratios, 0, True)

    top_script = max(ratios, key=ratios.__getitem__)
    minor = 1.0 - ratios[top_script]

    if minor < config.mixed_min_ratio:
        if top_script == "arabic":
            scores = _score_arabic_script(text, letters, config)
            label, margin, by_prior = _label_arabic_script(scores, config)
            return _Span(label, margin, scores, LatinScriptScores(), ratios, letters, by_prior)
        if top_script == "latin":
            scores = _score_latin_script(text)
            label, margin, by_prior = _label_latin_script(scores, config)
            return _Span(label, margin, ArabicScriptScores(), scores, ratios, letters, by_prior)
        if top_script == "devanagari":
            return _Span("hindi", 1.0, ArabicScriptScores(), LatinScriptScores(), ratios, letters)
        return _Span("other", 0.0, ArabicScriptScores(), LatinScriptScores(), ratios, letters, True)

    arabic_scores = _score_arabic_script(text, letters, config)
    latin_scores = _score_latin_script(text)
    arabic_label, arabic_margin, arabic_prior = _label_arabic_script(arabic_scores, config)
    latin_label, latin_margin, latin_prior = _label_latin_script(latin_scores, config)

    arabic_share = ratios.get("arabic", 0.0)
    latin_share = ratios.get("latin", 0.0)
    both_present = (
        arabic_share >= config.mixed_min_ratio and latin_share >= config.mixed_min_ratio
    )
    # An Urdu side plus a substantial Latin side of *running text* is code-switching. Two things
    # are deliberately not required, and one is.
    #
    # Not required: that the Latin side score as English or Roman Urdu. Embedded English in Urdu
    # is overwhelmingly *content* words — "meeting kal schedule ہے، deadline کے بارے میں team نے
    # final decision نہیں کیا" — so a genuinely code-switched sentence carries no English function
    # words at all. An earlier version required one and rejected exactly the case the label
    # exists for.
    #
    # Required: that the Latin side be lowercase running text rather than names. Without it, Urdu
    # Wikipedia's geographic stubs — Urdu prose quoting a French place name — came out 30%
    # code-switched, which would have moved a large slice of the cleanest native Urdu available
    # into PRD §6.1's ~10M-token code-switched budget and out of the ~120M native one.
    if (
        both_present
        and arabic_label == "urdu"
        and latin_scores.lowercase >= config.latin_running_text_rate
    ):
        return _Span(
            "code_switched",
            min(arabic_share, latin_share),
            arabic_scores,
            latin_scores,
            ratios,
            letters,
        )

    if arabic_share >= latin_share:
        return _Span(
            arabic_label, arabic_margin, arabic_scores, latin_scores, ratios, letters, arabic_prior
        )
    return _Span(
        latin_label, latin_margin, arabic_scores, latin_scores, ratios, letters, latin_prior
    )


def _sentences(text: str, config: LangIDConfig) -> list[str]:
    """Sentences long enough to carry evidence. Short fragments are dropped, not guessed at."""
    out: list[str] = []
    for piece in _SENTENCE_SPLIT_RE.split(text):
        if not piece:
            continue
        piece = piece.strip()
        if not piece:
            continue
        _, letters = script_ratios(piece)
        if letters < config.sentence_min_letters:
            continue
        out.append(piece)
        if len(out) >= config.max_segments:
            break
    return out


def classify(text: str, config: LangIDConfig | None = None) -> LangIDResult:
    """Label one document. Sentence-level work happens only when the document is mixed.

    PRD §6.3.3 specifies exactly that: document level, sentence level only for mixed documents.
    The document verdict comes first and stands on its own; segmentation refines a mixed document
    into the pieces stage 9 will need to budget the code-switched population separately.
    """
    config = config or _DEFAULT_CONFIG
    fingerprint = _fingerprint(config)
    span = _label_span(text, config)

    if span.letters < config.min_letters:
        return LangIDResult(
            label="empty",
            scripts=span.scripts,
            letters=span.letters,
            config_fingerprint=fingerprint,
        )

    result = LangIDResult(
        label=span.label,
        scripts=span.scripts,
        letters=span.letters,
        margin=span.margin,
        arabic_scores=span.arabic,
        latin_scores=span.latin,
        by_prior=span.by_prior,
        config_fingerprint=fingerprint,
    )

    mixed = 1.0 - max(span.scripts.values()) >= config.mixed_min_ratio
    if not mixed:
        return result

    # --- mixed document: label every sentence too ---------------------------
    segments: list[Segment] = []
    per_label: Counter[str] = Counter()
    for sentence in _sentences(text, config):
        piece = _label_span(sentence, config)
        segments.append(Segment(label=piece.label, text=sentence, letters=piece.letters))
        per_label[piece.label] += piece.letters

    if not per_label:  # nothing cleared sentence_min_letters; the document verdict stands
        return result

    counted = sum(per_label.values())
    shares = {label: count / counted for label, count in per_label.items()}
    switched = shares.get("code_switched", 0.0)
    # The alternation partner has to be a *recognised* language. `other` — Latin script no word
    # list explains — is a navigation bar, a product table or a list of names, and a page of Urdu
    # wrapped in one is an Urdu page with furniture, not a bilingual document. Arabic and Persian
    # are excluded as partners on purpose too: religious and legal Urdu quotes Arabic constantly,
    # and that is a register of Urdu, not the Urdu/English population PRD §6.1 budgets.
    partner = shares.get("english", 0.0) + shares.get("roman_urdu", 0.0)

    # A document is code-switched either because its sentences switch internally, or because it
    # alternates between Urdu sentences and sentences of a language it switches with. Same
    # population for PRD §6.1's purposes; only the granularity differs.
    if switched >= config.code_switch_min_share or (
        shares.get("urdu", 0.0) >= config.alternation_min_share
        and partner >= config.alternation_min_share
    ):
        label: Label = "code_switched"
        margin = max(switched, min(shares.get("urdu", 0.0), partner))
    else:
        best, _, margin = _argmax(shares)
        label = best  # type: ignore[assignment]

    return LangIDResult(
        label=label,
        scripts=span.scripts,
        letters=span.letters,
        margin=margin,
        arabic_scores=span.arabic,
        latin_scores=span.latin,
        segments=tuple(segments),
        by_prior=span.by_prior and label == span.label,
        config_fingerprint=fingerprint,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    pin_utf8_streams()  # Urdu on a cp1252 console raises rather than mangles.
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("input", nargs="?", help="input file (default: stdin)")
    parser.add_argument("-c", "--config", help="langid config JSON")
    parser.add_argument("--jsonl", action="store_true", help="one JSON document per line")
    parser.add_argument("--field", default="text", help="JSONL text field (default: text)")
    parser.add_argument("--log", help="write the stage-3 log here as JSON")
    parser.add_argument("--segments", action="store_true", help="include per-sentence labels")
    args = parser.parse_args(argv)

    config = LangIDConfig.from_json_file(args.config) if args.config else LangIDConfig()
    raw = (
        Path(args.input).read_text(encoding="utf-8")
        if args.input
        else sys.stdin.read()
    )

    log = LangIDLog(config=config)
    if args.jsonl:
        documents = [json.loads(line)[args.field] for line in raw.splitlines() if line.strip()]
    else:
        documents = [raw]

    for text in documents:
        result = classify(text, config)
        log.add(result)
        print(json.dumps(result.to_dict(args.segments), ensure_ascii=False))

    report = json.dumps(log.to_dict(), indent=2, ensure_ascii=False)
    if args.log:
        Path(args.log).write_text(report + "\n", encoding="utf-8", newline="\n")
    else:
        print(report, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
