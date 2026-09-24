"""Is the word the model wrote a word? The instrument §8.3 never had (PRD §8.3).

Every generation metric in :mod:`ravaan.evaluation.generation` is a property of a *string*:
script consistency asks what alphabet the letters are in, distinct-n and the repetition rate ask
how the words are distributed, and `commit_order` asks what order the decoder wrote them in. None
of them asks the question a fluent reader asks first, which is whether the thing on the page is a
word at all. `بْباغ`, `ٹیُباغے`, `طبیعتکبھی`, `علاجٹیکل` — every one of those is script-consistent,
none of them repeats, and all of them were on the hosted demo.

So this module holds a lexicon of every Arabic-script word in the project's own Urdu sample and
reports the share of a generation's words that are not in it. The comparison that makes the
number mean something is the **control**: real held-out Urdu, tokenized and checked the same way,
scores ~0.4% — the rate at which a real writer uses a word 712.6M characters of Wikipedia and
FineWeb2 did not. A decoder above that is fabricating.

⚠️ **Three things about this instrument, in the order they bit.**

1. **The tokenizer decides what the instrument can see.** The first version split on combining
   marks, because Python's ``\\w`` excludes them — category ``Mn``, and ``str.isalnum()`` is False
   for every one. `بْباغ` therefore arrived as two real words, `ب` and `باغ`, and scored clean:
   the tokenizer split *inside* the broken join it was built to detect. Marks are part of a word
   here, and :func:`words` is the whole of the difference.

2. **The key is the mark-stripped skeleton.** Urdu writes most diacritics optionally, so a corpus
   holds `دعوت` far more often than `دعوتِ` and an exact-form check would call a correct izafat a
   fabrication. Stripping marks on both sides fixes that without weakening the metric — `بْباغ`
   skeletonizes to `بباغ`, which is not a word either.

3. **It is a rate over a denominator, and the denominator is gameable.** A decoder that writes
   only short common words scores zero and has not improved; Finding BZ is the record of exactly
   that happening to `commit_order`. :class:`Fabrication` therefore carries `words` and
   `characters` beside the rate, and any table built from it prints them.

**This is still not a speaker.** A sentence of real words can be ungrammatical, and this metric
will call it clean. It rules out one failure mode cheaply — the one §8.3 could not see and a
reader saw immediately — and leaves the rest to G5's annotators.

⚠️ **And there is a second failure it cannot see alone: a real word split into real words.**
`خوب رو با ل یٰاب` survived the first regenerated page because `با`, `ل` and `یٰاب` are all in
the corpus. :class:`Fabrication` counts that separately as ``fragments``; the two together are
what a reader means by "that is not a word", and neither is sufficient.
"""

from __future__ import annotations

import gzip
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

#: Combining marks that continue a word rather than ending it: the generic diacritic block, the
#: Arabic signs and tashkil, the superscript alef that `طولٰی` needs, and the Arabic Extended-A
#: marks. Everything else — spaces, digits, punctuation — is a boundary.
_MARKS = (
    r"\u0300-\u036f"      # combining diacritical marks
    r"\u0610-\u061a"      # Arabic signs
    r"\u064b-\u065f"      # Arabic tashkil
    r"\u0670"             # superscript alef
    r"\u06d6-\u06ed"      # Quranic annotation and the Urdu-facing marks
    r"\u08e3-\u08ff"      # Arabic Extended-A marks
)
WORD = re.compile(rf"(?:[^\W\d_]|[{_MARKS}])+", re.UNICODE)

#: The same thing for text that has already had its marks removed. The alternation above costs
#: roughly five times as much as a plain class, which is nothing on a 30-word generation and
#: three quarters of an hour on a 1.2 GB corpus — so :func:`skeleton_words` strips first with a
#: `str.translate` table and tokenizes with this. The two agree by construction: stripping cannot
#: join two words, because every mark it removes sat inside one.
_WORD_STRIPPED = re.compile(r"[^\W\d_]+", re.UNICODE)

#: The Arabic-script blocks Urdu is written in. A word with no character in them is a Latin or
#: Devanagari fragment, which is Finding CA's leak metric and not this one's business.
ARABIC = re.compile(r"[\u0600-\u06ff\u0750-\u077f\ufb50-\ufdff\ufe70-\ufeff]")

#: Every codepoint `unicodedata.combining` calls a mark, mapped away. Built once; `str.translate`
#: then runs in C rather than per-character in Python.
_STRIP = {
    point: None
    for point in range(0x300, 0x2000)
    if unicodedata.combining(chr(point))
}


def strip_marks(text: str) -> str:
    """``text`` with every combining mark removed. The fast half of :func:`skeleton_words`."""
    return text.translate(_STRIP)


def words(text: str) -> list[str]:
    """Every word in ``text``, with its combining marks attached. See the module note."""
    return WORD.findall(text)


def skeleton_words(text: str) -> list[str]:
    """Every Arabic-script word in ``text``, already skeletonized. For corpus-sized inputs."""
    return [w for w in _WORD_STRIPPED.findall(strip_marks(text)) if ARABIC.search(w)]


def arabic_words(text: str) -> list[str]:
    """Only the Arabic-script words — the ones this metric is entitled to judge."""
    return [word for word in WORD.findall(text) if ARABIC.search(word)]


def skeleton(word: str) -> str:
    """``word`` without its combining marks: the letter sequence a reader actually sees."""
    return "".join(ch for ch in word if not unicodedata.combining(ch))


#: One-letter words real Urdu actually writes, so that counting the rest means something. In 400
#: held-out documents one-letter words are **0.68%** of all words, and `و`, `ء` and `آ` are 73%
#: of those; the rest of the tail (`ن`, `ں`, `ر`, `ل` at 30–55 occurrences each) is corpus noise
#: of the same kind this metric exists to catch, so it is not exempted.
STANDALONE = frozenset("وءآ")


@dataclass(frozen=True, slots=True)
class Fabrication:
    """One generation's wordhood, with the denominators the rate is over.

    ``fragments`` is the companion failure and the one the lexicon *cannot* see on its own: a
    real word split into real words. `خوب رو با ل یٰاب` was on the demo with every piece of it in
    the corpus — `با`, `ل` and `یٰاب` all occur — so it passed the wordhood check while reading,
    to a speaker, as one word broken across four. A lexicon can only answer the question it is
    asked, and "is this a word" is not "is this one word".
    """

    words: int
    fabricated: int
    unknown: tuple[str, ...]
    non_arabic: int
    characters: float
    fragments: int

    @property
    def rate(self) -> float:
        return self.fabricated / self.words if self.words else 0.0

    def to_dict(self) -> dict:
        return {
            "words": self.words,
            "fabricated": self.fabricated,
            "rate": round(self.rate, 4),
            "unknown": list(self.unknown),
            "non_arabic": self.non_arabic,
            "characters": round(self.characters, 2),
            "fragments": self.fragments,
        }


class Lexicon:
    """Skeletons of every Arabic-script word seen at least ``min_count`` times in a corpus.

    ``min_count`` defaults to 2 because a hapax in 146M words is as likely to be OCR residue or a
    scanning artefact as it is to be a word, and a lexicon that admits them will forgive a decoder
    for inventing something that happens to collide with one.
    """

    __slots__ = ("_skeletons", "min_count", "types", "tokens")

    def __init__(self, skeletons: set[str], *, min_count: int, types: int, tokens: int) -> None:
        self._skeletons = skeletons
        self.min_count = min_count
        self.types = types
        self.tokens = tokens

    def __contains__(self, word: str) -> bool:
        return skeleton(word) in self._skeletons

    def __len__(self) -> int:
        return len(self._skeletons)

    @classmethod
    def load(cls, path: Path, *, min_count: int = 2) -> Lexicon:
        """Read a ``skeleton<TAB>count`` table, plain or gzipped."""
        opener = gzip.open if path.suffix == ".gz" else open
        keep, types, tokens = set(), 0, 0
        with opener(path, "rt", encoding="utf-8") as handle:  # type: ignore[operator]
            for line in handle:
                word, _, count = line.rstrip("\n").partition("\t")
                value = int(count)
                types += 1
                tokens += value
                if value >= min_count:
                    keep.add(word)
        return cls(keep, min_count=min_count, types=types, tokens=tokens)

    @classmethod
    def build(cls, chunks: Iterable[str], *, min_count: int = 2) -> tuple[Lexicon, dict[str, int]]:
        """Count skeletons across ``chunks`` of text. Returns the lexicon and the raw counts."""
        counts: dict[str, int] = {}
        for chunk in chunks:
            for key in skeleton_words(chunk):
                counts[key] = counts.get(key, 0) + 1
        keep = {word for word, count in counts.items() if count >= min_count}
        return (
            cls(keep, min_count=min_count, types=len(counts), tokens=sum(counts.values())),
            counts,
        )

    def measure(self, text: str) -> Fabrication:
        """The share of ``text``'s Arabic-script words this lexicon has never seen."""
        arabic = arabic_words(text)
        every = words(text)
        unknown = tuple(word for word in arabic if word not in self)
        skeletons = [skeleton(word) for word in arabic]
        letters = sum(len(s) for s in skeletons)
        return Fabrication(
            words=len(arabic),
            fabricated=len(unknown),
            unknown=unknown,
            non_arabic=len(every) - len(arabic),
            characters=letters / len(arabic) if arabic else 0.0,
            fragments=sum(1 for s in skeletons if len(s) == 1 and s not in STANDALONE),
        )


def summarize(measurements: Iterable[Fabrication]) -> dict:
    """Pool a set of draws. ``draws_affected`` is the number a reader would actually notice.

    Finding CA's lesson, applied at the point it was learned: a mean over a share hides a
    per-draw failure, and a reader reads draws. The rate says how much of the text is wrong; the
    affected share says how often *a page* is wrong, and on the hosted demo those two numbers
    told different stories.
    """
    items = list(measurements)
    total = sum(item.words for item in items)
    bad = sum(item.fabricated for item in items)
    affected = sum(1 for item in items if item.fabricated)
    return {
        "draws": len(items),
        "words": total,
        "fabricated": bad,
        "rate": round(bad / total, 4) if total else 0.0,
        "draws_affected": affected,
        "fragments": sum(item.fragments for item in items),
        "draws_affected_rate": round(affected / len(items), 4) if items else 0.0,
        "characters": round(
            sum(item.characters * item.words for item in items) / total, 2
        ) if total else 0.0,
    }


__all__ = [
    "ARABIC",
    "STANDALONE",
    "WORD",
    "Fabrication",
    "Lexicon",
    "arabic_words",
    "skeleton",
    "skeleton_words",
    "strip_marks",
    "summarize",
    "words",
]
