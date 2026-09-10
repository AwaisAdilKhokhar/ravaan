"""Engineering invariants for the substitution measurement (Finding AE).

`scripts/substitutions.py` is a *driver*, and Finding W's lesson is that this repo's bugs live at
the stage boundaries drivers compose rather than inside the stages. The properties worth pinning
here are the three that would make the report's numbers wrong while the pass still produced a
plausible-looking table:

* **specificity must be the conditional it claims to be.** The whole §5 argument is
  P(urdu | substitute) — if it were computed the other way round, or against the wrong denominator,
  یہ→`ki` would read as strong evidence instead of the weakest row in the table.
* **the ambiguous word must stay out of the conservative count.** یہ→`ki` is 671,685 rows on its
  own. Folding it into `rows_with_confirmed_substitution` would turn a 3.95% floor into 13.99% with
  no change of evidence.
* **the survivor bitmap must actually read the removal list's id format.** A parse that silently
  matches nothing reports every row as a survivor, which looks like "dedup removes none of it" —
  the finding §5.2 makes — arrived at by a bug rather than by the corpus.

The screen is deliberately not tested for precision. It has none to speak of and the report says so;
what is tested is that its own first false-positive family stays fixed, because the crude skeleton
scored `ہے`→`hai` as a substitution until `h`/`w`/`y` stopped being treated as vowels.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.substitutions import (
    AMBIGUOUS,
    CONFIRMED,
    CSV_BLOCK_ROWS,
    ROMAN_COLUMN,
    URDU_COLUMN,
    run_confirmed,
    run_screen,
    run_survivors,
    similarity,
)


def write_split(path: Path, rows: list[tuple[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[URDU_COLUMN, ROMAN_COLUMN])
        writer.writeheader()
        writer.writerows({URDU_COLUMN: u, ROMAN_COLUMN: r} for u, r in rows)
    return path


# ---------------------------------------------------------------------------
# the skeleton, which is what separates a substitution from a spelling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "urdu, roman",
    [("صرف", "sirf"), ("سچ", "sach"), ("علم", "ilm"), ("کام", "kaam"), ("رات", "raat")],
)
def test_a_correct_transliteration_scores_high(urdu: str, roman: str) -> None:
    assert similarity(urdu, roman) >= 0.60


@pytest.mark.parametrize("urdu, roman", [("ہے", "hai"), ("ہو", "ho"), ("ہیں", "hain")])
def test_h_w_y_words_are_not_flagged_as_substitutions(urdu: str, roman: str) -> None:
    """The screen's first false-positive family. Stripping h/w/y left `ہے` with an empty skeleton,
    so every correct rendering of the most common word in Urdu screened as an unrelated word."""
    assert similarity(urdu, roman) >= 0.60


@pytest.mark.parametrize(
    "urdu, roman", [("ہوئے", "hue"), ("ہوئی", "hui"), ("فروری", "feb"), ("و", "o")]
)
def test_the_screen_still_has_false_positives_and_they_are_pinned(urdu: str, roman: str) -> None:
    """These are *correct* renderings that the crude skeleton still scores below the cut, so they
    appear in `substitutions_screen.json` as candidates. Pinned rather than fixed: the screen is a
    candidate generator for a native speaker and the report says so in those words. If a later
    change makes the skeleton good enough to clear them, this test is the place that says the
    report's precision paragraph is now out of date."""
    assert similarity(urdu, roman) < 0.60


@pytest.mark.parametrize("urdu, roman", [("بس", "dehli"), ("گھر", "mamu"), ("یہ", "ki")])
def test_a_confirmed_substitution_scores_low(urdu: str, roman: str) -> None:
    assert similarity(urdu, roman) < 0.60


# ---------------------------------------------------------------------------
# confirmed
# ---------------------------------------------------------------------------


def test_specificity_is_p_urdu_given_substitute(tmp_path: Path) -> None:
    """Four rows contain `dehli`; three of them contain بس. Specificity is 3/4, not 3/3."""
    path = write_split(
        tmp_path / "s.csv",
        [("بس ایک", "dehli aik"), ("بس دو", "dehli do"), ("بس تین", "dehli teen")]
        + [("اور", "dehli aur")]
        + [("کچھ", "kuch")] * 6,
    )
    result = run_confirmed(path)
    word = result["by_word"]["بس"]
    assert word["substituted"] == 3
    assert word["substitute_elsewhere"] == 1
    assert word["specificity"] == pytest.approx(0.75)
    assert word["p_sub_given_urdu"] == pytest.approx(1.0)


def test_the_ambiguous_word_is_excluded_from_the_conservative_count(tmp_path: Path) -> None:
    """یہ→`ki` alone is 671,685 rows on the real corpus. Folding it in would inflate the floor
    the report quotes by 3.5x without adding a single piece of evidence."""
    path = write_split(
        tmp_path / "s.csv",
        [("بس ایک", "dehli aik")] + [("یہ دو", "ki do")] * 5 + [("کچھ", "kuch")] * 4,
    )
    result = run_confirmed(path)
    assert result["rows_with_confirmed_substitution"] == 1
    assert result["rows_including_ambiguous"] == 6
    assert result["by_word"]["یہ"]["ambiguous"] is True
    assert result["by_word"]["بس"]["ambiguous"] is False


def test_a_row_with_two_substitutions_is_counted_once(tmp_path: Path) -> None:
    """The reach number is rows carrying *at least one*, so double counting would overstate it
    exactly where the corruption is densest."""
    path = write_split(
        tmp_path / "s.csv", [("بس گھر", "dehli mamu")] + [("کچھ", "kuch")] * 9
    )
    result = run_confirmed(path)
    assert result["rows_with_confirmed_substitution"] == 1
    assert result["share_of_rows"] == pytest.approx(0.1)


def test_the_correct_form_is_counted_independently_of_the_substitute(tmp_path: Path) -> None:
    """A row can carry both — §5's کرتے row has 66.8% wrong and 30.8% right, which do not sum to
    one. Counting them as exclusive would hide that."""
    path = write_split(tmp_path / "s.csv", [("بس", "dehli bas")])
    word = run_confirmed(path)["by_word"]["بس"]
    assert word["substituted"] == 1 and word["correct"] == 1


# ---------------------------------------------------------------------------
# survivors
# ---------------------------------------------------------------------------


def test_survivors_reads_the_removal_list_id_format(tmp_path: Path) -> None:
    """`source:file:block:row` with 10,000-row blocks. A parse that matches nothing reports every
    row as a survivor, which is indistinguishable from the finding §5.2 actually makes."""
    rows = [("بس", "dehli")] * 3 + [("کچھ", "kuch")] * 3
    path = write_split(tmp_path / "s.csv", rows)
    removals = tmp_path / "r.txt"
    removals.write_text(
        '#!ravaan-exclusions {"count": 2}\n'
        "roman-urdu-parl:train_set.csv:0:0\nroman-urdu-parl:train_set.csv:0:1\n",
        encoding="utf-8",
    )
    result = run_survivors(path, removals, total_rows=len(rows))
    assert result["removals_marked"] == 2
    assert result["survivors"] == 4
    assert result["survivors_with_substitution"] == 1  # row 2 of the three `dehli` rows


def test_survivors_ignores_the_header_and_a_repeated_id(tmp_path: Path) -> None:
    rows = [("کچھ", "kuch")] * 5
    path = write_split(tmp_path / "s.csv", rows)
    removals = tmp_path / "r.txt"
    removals.write_text(
        "#!ravaan-exclusions {}\n"
        "roman-urdu-parl:train_set.csv:0:3\nroman-urdu-parl:train_set.csv:0:3\n",
        encoding="utf-8",
    )
    result = run_survivors(path, removals, total_rows=len(rows))
    assert result["removals_marked"] == 1
    assert result["survivors"] == 4


def test_a_block_offset_id_lands_on_the_right_row(tmp_path: Path) -> None:
    """`1:606` is global row 10,606, not row 606. Getting this wrong removes real rows and keeps
    the ones the freeze deleted, with no error anywhere."""
    rows = [("کچھ", f"row {i}") for i in range(CSV_BLOCK_ROWS + 3)]
    path = write_split(tmp_path / "s.csv", rows)
    removals = tmp_path / "r.txt"
    removals.write_text("roman-urdu-parl:train_set.csv:1:2\n", encoding="utf-8")
    result = run_survivors(path, removals, total_rows=len(rows))
    assert result["removals_marked"] == 1
    assert result["survivors"] == CSV_BLOCK_ROWS + 2


# ---------------------------------------------------------------------------
# screen
# ---------------------------------------------------------------------------


def test_the_screen_finds_a_planted_substitution(tmp_path: Path) -> None:
    # The other word has to *vary*: with two tokens present in all the same rows the screen cannot
    # tell which is the substitute, and would name either. On the corpus the confirmed words sit at
    # specificity 0.87-0.99 rather than a tied 1.00, which is what breaks that symmetry there.
    other = ["علم", "کام", "رات", "سچ", "دن", "کتاب",
             "پانی", "شہر", "راستہ", "درخت", "ہاتھ", "آنکھ"]
    roman = ["ilm", "kaam", "raat", "sach", "din", "kitaab",
             "paani", "shehar", "rasta", "darakht", "haath", "aankh"]
    rows = [(f"بس {other[i]}", f"dehli {roman[i]}") for i in range(12)]
    rows += [(f"صرف {other[i]}", f"sirf {roman[i]}") for i in range(12)]
    path = write_split(tmp_path / "s.csv", rows)
    result = run_screen(path, step=1, min_rows=10, max_coverage=0.50)
    found = {c["urdu"]: c["substitute"] for c in result["candidates"]}
    assert found.get("بس") == "dehli"
    assert "صرف" not in found


def test_the_screen_does_not_flag_a_correctly_transliterated_word(tmp_path: Path) -> None:
    rows = [("ہے یہاں", "hai yahan")] * 20
    path = write_split(tmp_path / "s.csv", rows)
    result = run_screen(path, step=1, min_rows=10, max_coverage=0.50)
    assert [c["urdu"] for c in result["candidates"]] == []


def test_the_screen_output_is_json_serializable_with_urdu_intact(tmp_path: Path) -> None:
    """Every artifact in reports/ is read back by a human. cp1252 is this repo's fifth Windows text
    default and `ensure_ascii` is the same failure one layer up."""
    rows = [("بس ٹھیک", "dehli theek")] * 12
    path = write_split(tmp_path / "s.csv", rows)
    result = run_screen(path, step=1, min_rows=10, max_coverage=0.50)
    out = tmp_path / "out.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    assert "بس" in out.read_text(encoding="utf-8")


def test_confirmed_and_ambiguous_do_not_overlap() -> None:
    assert not set(CONFIRMED) & set(AMBIGUOUS)
