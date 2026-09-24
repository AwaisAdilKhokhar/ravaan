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
from collections.abc import Sequence
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


# --- Two quantities §8.3 does not have, added 2026-09-24 --------------------------------------
#
# §8.3's three metrics are properties of a *string*, and both failure modes a fluent reader
# reported on the published demo are properties of the string's *relationship to something else*
# — to the order the decoder wrote it in, and to the prefix it was given. Neither can be computed
# by `GenerationStats.of(text)` and neither should be bolted onto it: a caller with only text is
# entitled to the three numbers, and these two would have to be `None` there, which is how an
# optional field ends up silently unreported. They are functions, they take what they need, and a
# caller that has the inputs calls them.
#
# The evidence they exist for: on the ten demo prompts the diffusion arm assembled **47%**
# (`gumbel 2`) and **66%** (`random`) of its multi-piece words out of order, against **0%** for
# the AR arm, and echoed a prefix bigram on 5/10 and 4/10 continuations against AR's 1/10 — while
# distinct-1, the metric that was being read, *preferred* the worse of the two schedules 0.676 to
# 0.410. A metric that ranks the arms opposite to the only fluent reader who has looked is not a
# floor, it is a trapdoor.


def prefix_echo(prefix: str, continuation: str, *, n: int = 2) -> dict:
    """How much of ``continuation`` is the ``prefix`` said back. Word n-grams, order ``n``.

    The phrase-level symptom of the same independence that breaks words: a canvas whose positions
    are committed from marginals has no mechanism preventing half of it agreeing to restate the
    prompt, because each half is individually a plausible continuation. `longest_repeat` cannot
    see it — the repeat is not *within* the continuation, it is between the continuation and text
    the metric was never shown.

    ``rate`` is the share of the continuation's n-grams that also occur in the prefix, and
    ``echoed`` is the yes/no a table column wants. Both are 0.0/False when either side is shorter
    than ``n`` words, which is the honest reading: nothing was repeated because nothing could be.
    """
    if n < 1:
        raise ValueError(f"n must be at least 1, got {n}")
    before, after = prefix.split(), continuation.split()
    source = set(_ngrams(before, n))
    written = _ngrams(after, n)
    total = sum(written.values())
    if not source or not total:
        return {"n": n, "echoed": False, "rate": 0.0, "shared": []}
    shared = sorted(" ".join(gram) for gram in written if gram in source)
    hits = sum(count for gram, count in written.items() if gram in source)
    return {"n": n, "echoed": bool(shared), "rate": hits / total, "shared": shared}


def commit_order(pieces: Sequence[str | None], commit_step: Sequence[int]) -> dict:
    """Share of multi-piece words whose pieces were **not** written left to right.

    This is the metric that measures what a reader actually complained about, and it is free:
    every diffusion trace already records which step committed which position. A word is a run of
    SentencePiece pieces opened by a word-boundary marker — `▁` as the tokenizer writes it, or the
    leading space `scripts/demo_trace.py` renders it as, and both are accepted because the trace
    on disk uses the second. ``None`` marks a position that is framing rather than output.

    A word is **out of order** when the step numbers of its generated pieces are not
    non-decreasing: some piece was committed on an earlier pass than a piece to its left, so the
    model chose it from a marginal that had not seen its own word's beginning. Ties are in order —
    two pieces committed on the *same* step were still sampled independently, and that is a
    separate (and unavoidable) property of the schedule, not this one.

    **For the AR arm this is 0 by construction**, which is the point: it is not a metric the AR
    arm happens to win, it is a failure mode the AR factorization cannot have. Reporting it is
    therefore a statement about the decoder, and the honest comparison is between diffusion
    decoders rather than across arms.

    Positions with ``commit_step < 0`` were given, not written, and are skipped — a word whose
    first piece came from the prompt is only scored on what the decoder added to it.
    """
    if len(pieces) != len(commit_step):
        raise ValueError(f"{len(pieces)} pieces against {len(commit_step)} commit steps")
    words: list[list[int]] = []
    for piece, step in zip(pieces, commit_step, strict=True):
        if piece is None:
            continue
        if (piece.startswith("▁") or piece.startswith(" ")) or not words:
            words.append([])
        if step >= 0:
            words[-1].append(step)
    multi = [w for w in words if len(w) > 1]
    disordered = [w for w in multi if any(b < a for a, b in zip(w, w[1:], strict=False))]
    return {
        "words": len(words),
        "multi_piece": len(multi),
        "out_of_order": len(disordered),
        "rate": len(disordered) / len(multi) if multi else 0.0,
    }


__all__ = [
    "ORDERS",
    "GenerationStats",
    "commit_order",
    "longest_repeated_run",
    "prefix_echo",
]
