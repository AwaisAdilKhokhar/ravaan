"""The wordhood metric, and in particular the tokenizer bug that made its first version blind.

Dependency-free like `test_generation_metrics.py`, and for the same reason: this is string and
dictionary arithmetic, so it belongs in the CI job that proves the library imports without a
deep-learning stack.

The case that has to be locked down is the one that got past the first version. `بْباغ` — a word
the hosted demo actually printed — is `ب` + sukun + `باغ`, and Python's `\\w` excludes combining
marks, so a naive `[^\\W\\d_]+` splits it into two *real* words and reports it clean. A metric
built to catch broken joins must not tokenize inside one.
"""

from __future__ import annotations

import gzip

import pytest

from ravaan.evaluation.lexicon import (
    Lexicon,
    arabic_words,
    skeleton,
    skeleton_words,
    strip_marks,
    summarize,
    words,
)

#: `ب` + U+0652 sukun + `باغ`. The demo printed it; a reader pointed at it.
BROKEN = "بْباغ"
#: `دعوت` with an izafat kasra — a correct Urdu word the corpus mostly writes bare.
IZAFAT = "دعوتِ"


def test_a_combining_mark_does_not_end_a_word() -> None:
    assert words(BROKEN) == [BROKEN]
    assert words(f"صبح {IZAFAT} شام") == ["صبح", IZAFAT, "شام"]


def test_the_naive_tokenizer_would_have_split_it() -> None:
    """Guards the actual bug: two real words out of one fabricated one."""
    import re

    assert re.findall(r"[^\W\d_]+", BROKEN) == ["ب", "باغ"]
    assert words(BROKEN) != ["ب", "باغ"]


def test_skeleton_strips_marks_and_keeps_letters() -> None:
    assert skeleton(BROKEN) == "بباغ"
    assert skeleton(IZAFAT) == "دعوت"


def test_arabic_words_drops_latin_fragments() -> None:
    """A Latin leak is Finding CA's metric. This one only judges Arabic-script words."""
    assert arabic_words("لاہور shukriya شہر") == ["لاہور", "شہر"]


def test_a_marked_word_is_known_by_its_skeleton() -> None:
    lexicon = Lexicon({"دعوت"}, min_count=2, types=1, tokens=2)
    assert IZAFAT in lexicon
    assert BROKEN not in lexicon


def test_measure_reports_the_denominators_beside_the_rate() -> None:
    """Finding BZ: a rate whose denominator is not printed is how a decoder games a metric."""
    lexicon = Lexicon({"لاہور", "شہر"}, min_count=2, types=2, tokens=4)
    result = lexicon.measure(f"لاہور {BROKEN} شہر hello")
    assert (result.words, result.fabricated) == (3, 1)
    assert result.unknown == (BROKEN,)
    assert result.non_arabic == 1
    assert result.rate == pytest.approx(1 / 3)
    # لاہور is five letters, بْباغ skeletonizes to four, شہر is three.
    assert result.characters == pytest.approx((5 + 4 + 3) / 3)


def test_measure_of_empty_text_is_zero_and_not_an_error() -> None:
    lexicon = Lexicon(set(), min_count=2, types=0, tokens=0)
    result = lexicon.measure("")
    assert result.words == 0 and result.rate == 0.0


def test_build_prunes_below_min_count() -> None:
    lexicon, counts = Lexicon.build(["لاہور شہر لاہور"], min_count=2)
    assert counts == {"لاہور": 2, "شہر": 1}
    assert "لاہور" in lexicon and "شہر" not in lexicon
    assert (lexicon.types, lexicon.tokens) == (2, 3)


def test_load_round_trips_a_gzipped_table(tmp_path) -> None:
    path = tmp_path / "lex.tsv.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("لاہور\t9\nشہر\t1\n")
    lexicon = Lexicon.load(path, min_count=2)
    assert "لاہور" in lexicon and "شہر" not in lexicon
    assert (lexicon.types, lexicon.tokens) == (2, 10)


def test_summarize_reports_affected_draws_and_not_only_the_mean() -> None:
    """Finding CA: a mean over a share is blind to a per-draw failure, and a reader reads draws."""
    lexicon = Lexicon({"لاہور", "شہر"}, min_count=2, types=2, tokens=4)
    clean = lexicon.measure("لاہور شہر لاہور شہر")
    dirty = lexicon.measure(f"لاہور شہر لاہور {BROKEN}")
    pooled = summarize([clean, clean, clean, dirty])
    assert pooled["rate"] == pytest.approx(1 / 16)
    assert pooled["draws_affected"] == 1
    assert pooled["draws_affected_rate"] == pytest.approx(0.25)


def test_the_fast_path_agrees_with_the_slow_one() -> None:
    """`skeleton_words` strips then tokenizes; `arabic_words` tokenizes then strips."""
    text = f"لاہور {BROKEN} شہر {IZAFAT} hello"
    assert skeleton_words(text) == [skeleton(w) for w in arabic_words(text)]


def test_strip_marks_leaves_letters_alone() -> None:
    assert strip_marks(f"{BROKEN} {IZAFAT}") == "بباغ دعوت"


def test_fragments_counts_one_letter_words_urdu_does_not_write() -> None:
    """`خوب رو با ل یٰاب` — every piece in the corpus, one word across four."""
    lexicon = Lexicon({"خوب", "رو", "با", "ل", "یاب"}, min_count=2, types=5, tokens=10)
    result = lexicon.measure("خوب رو با ل یٰاب")
    assert result.fabricated == 0
    assert result.fragments == 1


def test_fragments_exempts_the_one_letter_words_urdu_does_write() -> None:
    lexicon = Lexicon({"و", "ء", "آ", "لاہور"}, min_count=2, types=4, tokens=8)
    assert lexicon.measure("لاہور و ء آ").fragments == 0


def test_summarize_pools_fragments_too() -> None:
    lexicon = Lexicon({"خوب", "ل"}, min_count=2, types=2, tokens=4)
    pooled = summarize([lexicon.measure("خوب ل"), lexicon.measure("خوب خوب")])
    assert pooled["fragments"] == 1
