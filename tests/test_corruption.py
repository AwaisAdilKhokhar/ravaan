"""§4.2's corruptions (PRD §4.2, §6.3.4).

The load-bearing test here is :func:`test_reversible_family_is_undone_by_stage_4`. §4.2's
restoration task needs a (damaged, clean) pair whose clean side is genuinely the right answer, and
the module's claim is that half its damage is drawn from the exact families stage 4 folds back.
That is a checkable claim rather than a comment, and this is where it gets checked — at a 50% edit
rate over hundreds of seeds, so a family that leaked into the reversible half would show.

The other half of the file pins the transliterator against Roman Urdu as speakers actually write
it. Those assertions are deliberately *shapes* rather than exact strings where the vowel is
unrecoverable: the script does not record whether the vowel in `kitab` was an `i`, so a test that
demanded one would be asserting something the instrument cannot know.
"""

from __future__ import annotations

import random

import pytest

from ravaan.data.corruption import (
    DOT_CONFUSIONS,
    INSERTABLE_INVISIBLES,
    REVERSIBLE_FAMILIES,
    CorruptionConfig,
    code_switch,
    corrupt_ocr,
    corrupt_restore,
    corrupt_spacing,
    romanize,
)
from ravaan.data.normalization import normalize_text

# Already through stage 4 — the reversibility claim is about text the corpus actually holds, and
# `normalize_text(CLEAN) == CLEAN` is asserted below rather than assumed.
CLEAN = (
    "یہ ایک اردو جملہ ہے۔ کتاب پڑھنا اچھا ہے، بھائی۔ "
    "پاکستان میں 2024 کے دوران 3.5 فیصد اضافہ ہوا۔ "
    "درگاہ بندہ نواز کے صفحہ پر ہمارے مقررہ وقت کا حساب لکھا ہے۔"
)

REVERSIBLE_ONLY = CorruptionConfig(ocr_rate=(0.5, 0.5), ocr_lossy_share=0.0)
LOSSY_ONLY = CorruptionConfig(ocr_rate=(0.5, 0.5), ocr_lossy_share=1.0)


def test_fixture_is_already_normalized():
    """Everything below rests on this: the corpus is stage 4's output, so the clean side is."""
    assert normalize_text(CLEAN) == CLEAN


@pytest.mark.parametrize("seed", range(40))
def test_reversible_family_is_undone_by_stage_4(seed):
    """§4.2's restoration gold is stage 4's own output, and this is the proof rather than a note.

    Half the OCR damage is drawn from the variant, digit, presentation-form and invisible families
    `ravaan.data.normalization` exists to fold away. At a 50% per-character edit rate, an entry
    that did not belong in that half would surface within a handful of seeds.
    """
    damaged = corrupt_ocr(CLEAN, random.Random(seed), REVERSIBLE_ONLY)
    assert damaged != CLEAN
    assert normalize_text(damaged) == CLEAN


@pytest.mark.parametrize("seed", range(10))
def test_lossy_family_is_not_undone_by_stage_4(seed):
    """And the other half must *not* be, or the task is a regex with extra steps."""
    damaged = corrupt_ocr(CLEAN, random.Random(seed), LOSSY_ONLY)
    assert normalize_text(damaged) != CLEAN


def test_the_two_families_never_overlap():
    """A dot confusion that stage 4 also folds would make the reversibility test pass by accident.

    The Arabic-keyboard heh (which stage 4 maps to gol he) is the near miss this guards: it sits
    in the reversible family, so it is deliberately absent from the heh dot-confusion pair.
    """
    reversible = {
        variant
        for table in REVERSIBLE_FAMILIES.values()
        for variants in table.values()
        for variant in variants
    }
    confusable = {char for family in DOT_CONFUSIONS for char in family}
    assert not reversible & confusable


def test_harakat_are_never_injected():
    """`NormalizationConfig.remove_harakat` is False — they are information stage 4 kept, so a
    restoration model must not be taught to delete them."""
    harakat = {chr(code) for code in range(0x064B, 0x0660)} | {chr(0x0670)}
    for seed in range(40):
        damaged = corrupt_ocr(CLEAN, random.Random(seed), CorruptionConfig(ocr_rate=(0.4, 0.4)))
        assert not harakat & set(damaged)


def test_corruption_is_deterministic_given_a_seed():
    """§4.2: "with the generator version and seed recorded" — which only means anything if the
    seed determines the output."""
    for corrupt in (corrupt_ocr, corrupt_spacing, corrupt_restore, code_switch):
        assert corrupt(CLEAN, random.Random(7)) == corrupt(CLEAN, random.Random(7))
        assert corrupt(CLEAN, random.Random(7)) != corrupt(CLEAN, random.Random(8))


def test_spacing_corruption_moves_spaces_and_keeps_the_characters():
    """Joining and splitting words changes where the spaces are and nothing else."""
    damaged = corrupt_spacing(CLEAN, random.Random(3), CorruptionConfig(spacing_rate=(0.5, 0.5)))
    assert damaged != CLEAN
    assert damaged.replace(" ", "") == CLEAN.replace(" ", "")


def test_config_fingerprint_moves_with_the_settings():
    assert CorruptionConfig().fingerprint() == CorruptionConfig().fingerprint()
    assert CorruptionConfig().fingerprint() != CorruptionConfig(ocr_lossy_share=0.4).fingerprint()


def test_config_rejects_an_inverted_range():
    with pytest.raises(ValueError, match="ordered range"):
        CorruptionConfig(ocr_rate=(0.5, 0.1))


def test_invisibles_are_all_deleted_by_stage_4():
    """Every insertable invisible has to be one stage 4 removes, or inserting it is lossy."""
    for invisible in INSERTABLE_INVISIBLES:
        assert normalize_text(f"ا{invisible}ب") == "اب"


# ---------------------------------------------------------------------------
# The transliterator
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("urdu", "roman"),
    [
        ("کرتے", "karte"),  # the inherent vowel goes after the kaf, not after the re
        ("گھر", "ghar"),  # do-chashmi he aspirates and does not take a vowel before it
        ("بندہ", "banda"),  # final gol he after a consonant is the vowel
        ("درگاہ", "dargah"),  # final gol he after a written vowel is the consonant
        ("صفحہ", "safha"),
        ("ہمارے", "hamare"),  # gol he is `h` at the front of a word
        ("پڑھنا", "parhna"),
        ("اچھا", "achha"),
        ("لڑکی", "larki"),
        ("بھائی", "bhayi"),
    ],
)
def test_romanize_matches_how_speakers_write_it(urdu, roman):
    assert romanize(urdu) == roman


@pytest.mark.parametrize(
    ("urdu", "skeleton"),
    [("اردو", "rd"), ("کتاب", "ktb"), ("حساب", "hsb"), ("جملہ", "jml")],
)
def test_romanize_recovers_the_consonants_where_the_vowel_is_unknowable(urdu, skeleton):
    """`kitab` comes out `katab`: the abjad does not record which vowel it was.

    Asserted as the consonant skeleton rather than as a string, because demanding the vowel would
    be demanding information the script does not carry — and because that gap is precisely what
    §8.2's human-written test set exists to measure.
    """
    produced = romanize(urdu)
    assert "".join(c for c in produced if c not in "aeiou") == skeleton


def test_romanize_leaves_non_arabic_text_alone():
    """The `code_switched` population is mixed, so this has to be a no-op on the Latin half."""
    assert romanize("COVID-19 vaccine 2024") == "COVID-19 vaccine 2024"
    assert romanize("") == ""


def test_romanize_is_a_pure_function_of_the_text():
    assert romanize(CLEAN) == romanize(CLEAN)


def test_code_switch_only_replaces_whole_words():
    """Nobody writes half a word in Roman. Every native run that survives must be untouched."""
    mixed = code_switch(CLEAN, random.Random(1), CorruptionConfig(codeswitch_rate=(0.4, 0.4)))
    assert mixed != CLEAN
    native_words = set(CLEAN.split())
    for word in mixed.split():
        if any("؀" <= char <= "ۿ" for char in word):
            assert word in native_words


def test_code_switch_at_zero_is_the_identity():
    assert code_switch(CLEAN, random.Random(0), CorruptionConfig(codeswitch_rate=(0.0, 0.0))) == (
        CLEAN
    )
