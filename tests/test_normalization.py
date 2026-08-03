"""Engineering invariants for Urdu normalization (PRD §8.1 — CI, never a results table)."""

from __future__ import annotations

import json

import pytest

from ravaan.data.normalization import (
    NORMALIZER_VERSION,
    PRESERVED_LETTERS,
    NormalizationConfig,
    NormalizationLog,
    normalize,
    normalize_text,
)

DEFAULT = NormalizationConfig()

# A paragraph carrying one of each defect the pipeline is supposed to fix.
DIRTY = (
    "﻿یہ كتاب يہاں ہے‏۔\n\n\n\n"
    "قیمت ٦٧٨ روــپے ہے؟\r\n"
    "ﻺ أب آج ے ۓ ھ ه‌و\n"
)


# --- Preservation ----------------------------------------------------------
# If any of these fold, the normalizer has destroyed the language. Highest-priority tests.


@pytest.mark.parametrize("letter", list(PRESERVED_LETTERS))
def test_urdu_letters_survive_unchanged(letter: str) -> None:
    assert normalize_text(f"ا{letter}ا") == f"ا{letter}ا"


def test_bari_ye_is_not_folded_into_choti_ye() -> None:
    # ہے (bari ye) and ہی (choti ye) are different words.
    assert normalize_text("ہے") == "ہے"
    assert normalize_text("ہے") != normalize_text("ہی")


def test_do_chashmi_he_is_not_folded_into_gol_he() -> None:
    # کھانا (to eat) vs کہانا — the aspirate is a distinct letter.
    assert normalize_text("کھانا") == "کھانا"
    assert normalize_text("کھانا") != normalize_text("کہانا")


def test_alef_madda_survives() -> None:
    assert normalize_text("آم") == "آم"
    assert normalize_text("آم") != normalize_text("ام")


# --- Letter unification ----------------------------------------------------


def test_arabic_yeh_becomes_farsi_yeh() -> None:
    assert normalize_text("يہاں") == "یہاں"
    assert normalize_text("ى") == "ی"


def test_arabic_kaf_becomes_keheh() -> None:
    assert normalize_text("كتاب") == "کتاب"


def test_arabic_heh_becomes_heh_goal() -> None:
    assert normalize_text("هم") == "ہم"


def test_heh_with_yeh_above_becomes_izafat_form() -> None:
    assert normalize_text("ۀ") == "ۂ"


def test_teh_marbuta_folds_when_enabled_and_not_otherwise() -> None:
    assert normalize_text("ة") == "ہ"
    kept = NormalizationConfig(map_teh_marbuta=False)
    assert normalize_text("ة", kept) == "ة"


def test_hamza_bearing_alef_folds_to_plain_alef() -> None:
    assert normalize_text("أ") == "ا"
    assert normalize_text("إ") == "ا"
    assert normalize_text("ٱ") == "ا"


# --- Presentation forms ----------------------------------------------------


def test_arabic_presentation_forms_expand() -> None:
    # U+FEFA LAM WITH ALEF WITH HAMZA BELOW FINAL FORM → لإ → (alef unification) → لا
    assert normalize_text("ﻺ") == "لا"


def test_presentation_form_expansion_chains_into_letter_unification() -> None:
    # U+FEE9 HEH ISOLATED FORM → U+0647 → U+06C1
    assert normalize_text("ﻩ") == "ہ"


def test_bom_is_not_counted_as_a_presentation_form() -> None:
    """U+FEFF sits inside the Forms-B block; counting it twice would inflate the manifest."""
    counts = normalize("﻿ﻩم").counts
    assert counts["presentation_forms"] == 1
    assert counts["zero_width"] == 1


def test_presentation_forms_can_be_disabled() -> None:
    cfg = NormalizationConfig(expand_presentation_forms=False)
    assert normalize_text("ﻺ", cfg) == "ﻺ"


def test_nfkc_is_not_applied_globally() -> None:
    """The whole point of doing this by hand instead of calling unicodedata.normalize."""
    # Superscripts carry meaning in URLs, maths and citations. NFKC would flatten them.
    assert normalize_text("x²") == "x²"
    # Latin ligatures are outside the Arabic presentation blocks and are none of our business.
    assert normalize_text("ﬁle") == "ﬁle"
    # Circled digits and vulgar fractions likewise survive.
    assert normalize_text("① ½") == "① ½"


# --- Invisibles ------------------------------------------------------------


def test_tatweel_is_removed() -> None:
    assert normalize_text("روــپے") == "روپے"


def test_zero_width_and_bom_are_removed() -> None:
    assert normalize_text("﻿ا​ب‍ج") == "ابج"


def test_bidi_control_marks_are_removed() -> None:
    assert normalize_text("‏ا‫ب⁩ج؜") == "ابج"


def test_zwnj_removal_is_switchable() -> None:
    assert normalize_text("ہ‌و") == "ہو"
    kept = NormalizationConfig(remove_zwnj=False)
    assert normalize_text("ہ‌و", kept) == "ہ‌و"


# --- Digits ----------------------------------------------------------------


def test_digits_fold_to_ascii_by_default() -> None:
    assert normalize_text("٦٧٨") == "678"
    assert normalize_text("۱۲۳") == "123"
    assert normalize_text("١٫٥") == "1.5"


def test_digits_can_fold_to_urdu_shapes() -> None:
    cfg = NormalizationConfig(digits="urdu")
    assert normalize_text("123", cfg) == "۱۲۳"
    assert normalize_text("١", cfg) == "۱"


def test_digits_can_be_left_alone() -> None:
    cfg = NormalizationConfig(digits="keep")
    assert normalize_text("٦ 6 ۶", cfg) == "٦ 6 ۶"


# --- Harakat ---------------------------------------------------------------


def test_harakat_are_preserved_by_default() -> None:
    assert normalize_text("کِتاب") == "کِتاب"


def test_harakat_removal_is_opt_in() -> None:
    cfg = NormalizationConfig(remove_harakat=True)
    assert normalize_text("کِتاب", cfg) == "کتاب"
    assert normalize_text("مُحَمَّد", cfg) == "محمد"


# --- Whitespace ------------------------------------------------------------


def test_whitespace_is_collapsed_and_trimmed() -> None:
    assert normalize_text("  ا   ب \t ج  ") == "ا ب ج"
    assert normalize_text("ا ب") == "ا ب"


def test_crlf_and_unicode_line_separators_become_newlines() -> None:
    assert normalize_text("ا\r\nب ج د") == "ا\nب\nج\nد"


def test_blank_line_runs_are_capped() -> None:
    assert normalize_text("ا\n\n\n\n\n\nب") == "ا\n\nب"
    cfg = NormalizationConfig(max_consecutive_newlines=1)
    assert normalize_text("ا\n\n\nب", cfg) == "ا\nب"


def test_empty_and_whitespace_only_input() -> None:
    assert normalize_text("") == ""
    assert normalize_text("   \n\n\t ") == ""
    assert normalize("").counts == {}


# --- Cross-cutting invariants ---------------------------------------------


@pytest.mark.parametrize(
    "config",
    [
        NormalizationConfig(),
        NormalizationConfig(digits="urdu"),
        NormalizationConfig(digits="keep"),
        NormalizationConfig(remove_harakat=True),
        NormalizationConfig(remove_zwnj=False, map_teh_marbuta=False),
        NormalizationConfig(expand_presentation_forms=False, normalize_whitespace=False),
    ],
)
def test_normalization_is_idempotent(config: NormalizationConfig) -> None:
    once = normalize_text(DIRTY, config)
    assert normalize_text(once, config) == once


@pytest.mark.parametrize(
    "config",
    [
        NormalizationConfig(),
        NormalizationConfig(digits="urdu"),
        NormalizationConfig(remove_harakat=True),
    ],
)
def test_fast_path_and_logging_path_agree(config: NormalizationConfig) -> None:
    assert normalize(DIRTY, config).normalized == normalize_text(DIRTY, config)


def test_output_is_valid_utf8_and_free_of_surrogates() -> None:
    out = normalize_text(DIRTY)
    assert out.encode("utf-8").decode("utf-8") == out
    assert not any(0xD800 <= ord(ch) <= 0xDFFF for ch in out)


def test_no_rule_collides_on_a_codepoint() -> None:
    """_compile raises on overlap; exercising every flag combination that matters proves it."""
    for digits in ("ascii", "urdu", "keep"):
        for harakat in (False, True):
            normalize_text("ا", NormalizationConfig(digits=digits, remove_harakat=harakat))


# --- Transformation log ----------------------------------------------------


def test_result_carries_original_normalized_and_counts() -> None:
    result = normalize(DIRTY)
    assert result.original == DIRTY
    assert result.changed
    assert result.normalizer_version == NORMALIZER_VERSION
    assert result.config_fingerprint == DEFAULT.fingerprint()
    for rule in ("yeh", "kaf", "heh", "alef", "tatweel", "zero_width", "bidi", "digits"):
        assert result.counts.get(rule, 0) > 0, f"expected {rule} to fire on the dirty fixture"


def test_counts_are_exact() -> None:
    counts = normalize("ككيـ").counts
    assert counts["kaf"] == 2
    assert counts["yeh"] == 1
    assert counts["tatweel"] == 1


def test_unchanged_text_reports_no_transformations() -> None:
    result = normalize("یہ صاف اردو ہے۔")
    assert not result.changed
    assert result.counts == {}


def test_log_aggregates_across_documents() -> None:
    log = NormalizationLog(config=DEFAULT)
    for text in (DIRTY, "یہ صاف اردو ہے۔", "كتاب"):
        log.add(normalize(text, DEFAULT))
    payload = log.to_dict()
    assert payload["documents"] == 3
    assert payload["documents_changed"] == 2
    assert payload["chars_removed"] > 0
    assert payload["counts"]["kaf"] >= 2
    assert payload["config_fingerprint"] == DEFAULT.fingerprint()
    json.dumps(payload)  # must be manifest-serializable


# --- Config ----------------------------------------------------------------


def test_fingerprint_is_stable_and_sensitive() -> None:
    assert NormalizationConfig().fingerprint() == NormalizationConfig().fingerprint()
    assert NormalizationConfig().fingerprint() != NormalizationConfig(digits="urdu").fingerprint()


def test_config_json_roundtrip(tmp_path) -> None:
    cfg = NormalizationConfig(digits="urdu", remove_harakat=True, max_consecutive_newlines=1)
    path = tmp_path / "normalization.json"
    cfg.to_json_file(path)
    assert NormalizationConfig.from_json_file(path) == cfg


def test_shipped_default_config_matches_code_defaults() -> None:
    from pathlib import Path

    shipped = Path(__file__).resolve().parents[1] / "configs" / "data" / "normalization.json"
    assert NormalizationConfig.from_json_file(shipped) == NormalizationConfig()


def test_invalid_config_is_rejected() -> None:
    with pytest.raises(ValueError):
        NormalizationConfig(digits="hindi")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        NormalizationConfig(max_consecutive_newlines=0)
    with pytest.raises(ValueError):
        NormalizationConfig.from_dict({"unify_yeh": True, "unify_zeh": True})
