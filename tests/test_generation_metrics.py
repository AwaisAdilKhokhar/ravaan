"""§8.3's two order-dependent metrics, added after a fluent reader outranked the existing three.

Deliberately **not** in `test_sampling.py`, which gates its whole module behind
`pytest.importorskip("torch")`. Neither metric needs torch or numpy — they are string and integer
arithmetic — so they belong where the dependency-free CI job can run them, which is the job that
exists to prove the library is importable without a deep-learning stack installed.

What is worth asserting here is not that the arithmetic is right; it is the two edge cases that
would make a *silent* wrong answer, because both metrics are read as evidence in a comparison:

* a word whose pieces were committed on the **same** step is in order, not out of it. Same-step
  pieces were still sampled independently, and if that counted as disorder the metric would
  conflate the thing a word-aware commit rule fixes with the thing it cannot;
* a word whose first piece came from the **prompt** is scored on what the decoder added. Counting
  given positions would report disorder on every word a prompt ends mid-way through.
"""

from __future__ import annotations

import pytest

from ravaan.evaluation.generation import commit_order, prefix_echo

#: A word boundary as SentencePiece writes it. `scripts/demo_trace.py` renders it as a leading
#: space before the trace reaches disk, so both spellings are exercised.
SP = "▁"


def test_commit_order_reads_left_to_right_as_ordered() -> None:
    pieces = [f"{SP}کتاب", f"{SP}اردو", "ادب"]
    assert commit_order(pieces, [0, 1, 2])["out_of_order"] == 0


def test_commit_order_catches_a_word_written_backwards() -> None:
    # The failure the demo showed: the second piece of a word committed a pass before its first.
    stats = commit_order([f"{SP}اردو", "ادب"], [3, 1])
    assert stats == {"words": 1, "multi_piece": 1, "out_of_order": 1, "rate": 1.0}


def test_commit_order_treats_the_leading_space_spelling_the_same() -> None:
    assert commit_order([" اردو", "ادب"], [3, 1])["out_of_order"] == 1


def test_commit_order_counts_a_same_step_word_as_ordered() -> None:
    """Two pieces on one step are independent draws, and that is a different metric's problem."""
    assert commit_order([f"{SP}اردو", "ادب"], [2, 2])["out_of_order"] == 0


def test_commit_order_skips_given_positions() -> None:
    """A word the prompt opened is scored on the pieces the decoder wrote, not on the prompt's."""
    # `-1` is given. What the decoder added is a single piece, so there is no order to violate.
    assert commit_order([f"{SP}اردو", "ادب"], [-1, 4])["multi_piece"] == 0


def test_commit_order_ignores_framing_positions() -> None:
    assert commit_order([None, None, f"{SP}اردو", "ادب"], [-1, -1, 1, 0])["out_of_order"] == 1


def test_commit_order_single_piece_words_are_not_counted() -> None:
    stats = commit_order([f"{SP}ایک", f"{SP}دو", f"{SP}تین"], [2, 0, 1])
    assert (stats["words"], stats["multi_piece"], stats["rate"]) == (3, 0, 0.0)


def test_commit_order_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="pieces against"):
        commit_order([f"{SP}ایک"], [0, 1])


def test_prefix_echo_finds_a_restated_opening() -> None:
    echo = prefix_echo("لاہور شہر اپنی تاریخ", "لاہور شہر کی عمارتیں")
    assert echo["echoed"] and "لاہور شہر" in echo["shared"]


def test_prefix_echo_is_silent_on_a_fresh_continuation() -> None:
    echo = prefix_echo("لاہور شہر اپنی تاریخ", "اور ثقافت کے حوالے سے")
    assert not echo["echoed"] and echo["rate"] == 0.0


def test_prefix_echo_rate_is_a_share_of_the_continuation() -> None:
    # Four bigrams written, the first of which restates the prefix.
    echo = prefix_echo("a b", "a b c d e")
    assert echo["rate"] == pytest.approx(0.25)


def test_prefix_echo_is_zero_when_nothing_could_repeat() -> None:
    """Shorter than one n-gram on either side. Nothing repeated because nothing could."""
    assert prefix_echo("a", "b c d")["rate"] == 0.0
    assert prefix_echo("a b c", "d")["rate"] == 0.0


def test_prefix_echo_order_is_settable() -> None:
    assert prefix_echo("a b c", "a b c d", n=3)["shared"] == ["a b c"]
    assert prefix_echo("a b c", "a b d e", n=3)["shared"] == []


def test_prefix_echo_rejects_a_zero_order() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        prefix_echo("a b", "c d", n=0)
