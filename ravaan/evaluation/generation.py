"""§8.3's open-generation metrics: script consistency, distinct-n, repetition rate.

Three numbers, and they exist because "is this coherent Urdu?" is a native speaker's question and
G3 asks it of a 25M-parameter model trained for 50 epochs on 7.4M tokens. A reader can tell
fluent text from noise; what a reader *cannot* do reliably across a hundred samples is notice that
one arm quietly stopped writing Urdu, or that a sample which reads well is four phrases on a loop.
These measure the two failure modes that are cheap to miss and expensive to report, so the read
arrives with them attached rather than as an impression.

**None of these says the text is good.** §8.4's human evaluation is what says that, and §8.2's
test sets are what the results table reads. A sample can score 1.00 on all three and be
grammatical nonsense. They are a floor: a sample that fails them has failed before a speaker is
asked to spend time on it.

Script consistency reuses stage 3's letter inventories rather than a second opinion about what
Arabic script is — `ravaan.data.langid` decided that for the corpus, and a generation metric that
disagreed with the corpus filter would be measuring the disagreement.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ravaan.data.langid import script_ratios

#: §8.3 reports distinct-n; these are the orders. 1 and 2 move with vocabulary, 3 and 4 with
#: phrasing, and a degenerate loop shows up in 4 long before it shows up in 1.
ORDERS = (1, 2, 3, 4)


def _ngrams(units: list[str], n: int) -> Counter:
    return Counter(tuple(units[i : i + n]) for i in range(len(units) - n + 1))


def longest_repeated_run(units: list[str]) -> int:
    """Length of the longest contiguous run that occurs at least twice.

    The metric that catches the failure the others blur: a sample that writes forty good tokens
    and then repeats one clause to the end of the canvas has a respectable distinct-2 and is not
    worth a speaker's time. Quadratic in the worst case and linear in practice — the inputs here
    are a few hundred tokens.
    """
    best = 0
    for n in range(1, len(units) + 1):
        counts = _ngrams(units, n)
        if not counts or max(counts.values()) < 2:
            break
        best = n
    return best


@dataclass(frozen=True, slots=True)
class GenerationStats:
    """What §8.3 asks of an open generation. Built from text, not from tokens.

    Text rather than tokens on purpose: the arms share a tokenizer but not a decoder, and a
    repetition rate measured over token ids would count §7's byte-fallback pieces as content. A
    reader sees characters.
    """

    characters: int
    words: int
    letters: int
    scripts: dict[str, float]
    script_consistency: float
    distinct: dict[int, float]
    repetition: float
    longest_repeat: int

    @classmethod
    def of(cls, text: str, *, script: str = "arabic") -> GenerationStats:
        """``script`` is the one the sample was *asked* for — `arabic` for native Urdu, `latin`
        for a Roman-Urdu target. Consistency is that script's share of the sample's letters."""
        ratios, letters = script_ratios(text)
        words = text.split()
        distinct = {}
        for n in ORDERS:
            counts = _ngrams(words, n)
            total = sum(counts.values())
            distinct[n] = len(counts) / total if total else 0.0
        return cls(
            characters=len(text),
            words=len(words),
            letters=letters,
            scripts=dict(sorted(ratios.items(), key=lambda kv: -kv[1])),
            script_consistency=ratios.get(script, 0.0),
            distinct=distinct,
            # §8.3 names repetition rate separately from distinct-n, and at order 4 the two are
            # complements. Reported as its own field because it is the one a reader looks at.
            repetition=1.0 - distinct[4],
            longest_repeat=longest_repeated_run(words),
        )

    def to_dict(self) -> dict:
        return {
            "characters": self.characters,
            "words": self.words,
            "letters": self.letters,
            "scripts": self.scripts,
            "script_consistency": self.script_consistency,
            "distinct": {str(n): v for n, v in self.distinct.items()},
            "repetition": self.repetition,
            "longest_repeat": self.longest_repeat,
        }


__all__ = ["ORDERS", "GenerationStats", "longest_repeated_run"]
