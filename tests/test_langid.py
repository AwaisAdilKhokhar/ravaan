"""Engineering invariants for language and script ID (PRD §8.1 — CI, never a results table).

Stage 3 splits the corpus into the three populations PRD §6.1 budgets separately, so the tests
that matter are the ones that catch a *population* being silently misrouted: Urdu read as Persian
because it was typed on an Arabic keyboard, Roman Urdu read as English, or an Urdu page quoting a
foreign name filed as bilingual.

The measured behaviour on real text lives in `reports/probe_stage3_*.json`; these are the rules.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ravaan.data.langid import (
    AMBIGUOUS_LATIN_WORDS,
    ENGLISH_WORDS,
    LANGID_VERSION,
    ROMAN_URDU_WORDS,
    LangIDConfig,
    LangIDLog,
    classify,
    script_ratios,
)

DEFAULT = LangIDConfig()

URDU = (
    "یہ ایک صاف اردو جملہ ہے۔ پاکستان میں اردو بولی جاتی ہے اور یہ قومی زبان ہے۔ "
    "اس کے بعد وہ لوگ آئے جو یہاں رہتے تھے اور انہوں نے بہت کام کیا۔"
)
ROMAN_URDU = (
    "yeh aik saaf urdu jumla hai. Pakistan mein urdu boli jati hai aur yeh qaumi zaban hai. "
    "us ke baad wo log aaye jo yahan rehte thay aur unhon ne bohat kaam kiya."
)
ENGLISH = (
    "This is a clean English sentence about the corpus. The pipeline reads documents from a "
    "shard and decides which of them are written in the target language."
)
ARABIC = (
    "هذا نص عربي واضح. اللغة العربية من أكثر اللغات انتشارا في العالم وهي لغة القرآن الكريم "
    "التي يتحدث بها الملايين في كل مكان."
)
PERSIAN = (
    "این یک متن فارسی است که برای آزمایش نوشته شده است. زبان فارسی در ایران و افغانستان "
    "صحبت می شود و برای ما بسیار زیبا است."
)
CODE_SWITCHED = (
    "meeting kal schedule ہے، لیکن deadline کے بارے میں team نے کوئی final decision نہیں کیا۔ "
    "کل کی presentation کے liye slides ابھی ready نہیں ہیں۔"
)


# --- The three populations come out separately ------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (URDU, "urdu"),
        (ROMAN_URDU, "roman_urdu"),
        (ENGLISH, "english"),
        (ARABIC, "arabic"),
        (PERSIAN, "persian"),
        (CODE_SWITCHED, "code_switched"),
        ("यह एक हिंदी वाक्य है। हिंदी भारत में बोली जाती है और देवनागरी लिपि में लिखी जाती है।", "hindi"),
    ],
)
def test_each_population_gets_its_own_label(text: str, expected: str) -> None:
    assert classify(text).label == expected


def test_only_the_three_budgeted_populations_are_kept() -> None:
    assert classify(URDU).kept
    assert classify(ROMAN_URDU).kept
    assert classify(CODE_SWITCHED).kept
    assert not classify(ENGLISH).kept
    assert not classify(ARABIC).kept
    assert not classify(PERSIAN).kept


# --- Urdu vs Persian vs Arabic ---------------------------------------------
# Stage 3 runs *before* normalization, so Urdu typed on an Arabic keyboard still carries ي, ك
# and ه. Those are exactly the characters that make it look Persian or Arabic, and the reason
# the classifier leans on Urdu's own letters rather than on shared function words.


def test_arabic_keyboard_urdu_is_still_urdu() -> None:
    dirty = URDU.replace("ی", "ي").replace("ک", "ك").replace("ہ", "ه")
    assert classify(dirty).label == "urdu"


def test_urdu_quoting_arabic_scripture_stays_urdu() -> None:
    # Religious and legal Urdu quotes Arabic constantly. A classifier tuned to reject
    # Arabic-looking text would strip a register of the language, not a language.
    text = (
        "قرآن مجید میں اللہ تعالیٰ کا ارشاد ہے۔ إن الله مع الصابرين والذين هم في صلاتهم خاشعون. "
        "اس آیت کا مطلب یہ ہے کہ صبر کرنے والوں کے ساتھ اللہ ہوتا ہے اور وہ لوگ کامیاب ہیں۔"
    )
    assert classify(text).label == "urdu"


def test_arabic_script_with_no_evidence_falls_back_to_urdu_and_says_so() -> None:
    result = classify("محمد احمد محمود عثمان صالح سلیمان ابراہیم اسماعیل یوسف یعقوب")
    assert result.label == "urdu"
    assert result.by_prior, "a label given by the prior must be marked as such"


def test_a_decided_label_is_not_marked_as_prior() -> None:
    assert not classify(URDU).by_prior
    assert not classify(ARABIC).by_prior


# --- Roman Urdu vs English --------------------------------------------------


def test_ambiguous_words_are_dropped_from_both_lists() -> None:
    # The failure this prevents: `the`, `to`, `or`, `he`, `us`, `do`, `main`, `so`, `say` are
    # frequent in both languages, and leaving them in hands whichever list is longer a free vote.
    assert {"the", "to", "or", "he", "us", "do", "main", "so", "say"} <= AMBIGUOUS_LATIN_WORDS
    assert not (ROMAN_URDU_WORDS & ENGLISH_WORDS)
    assert not (ROMAN_URDU_WORDS & AMBIGUOUS_LATIN_WORDS)
    assert not (ENGLISH_WORDS & AMBIGUOUS_LATIN_WORDS)


def test_roman_urdu_spelling_variants_all_land_in_the_same_place() -> None:
    # Roman Urdu has no orthography. A word list that only knows one spelling is a word list
    # that only classifies one writer.
    for variant in ("hai", "hy", "hain", "hein"):
        text = f"yeh kitab bohat achi {variant} aur mujhe pasand {variant}"
        assert classify(text).label == "roman_urdu", variant


def test_english_does_not_leak_into_the_roman_urdu_population() -> None:
    # The expensive direction: English scored as Roman Urdu pollutes a population the report
    # makes claims about. Measured at 0% over the repo's own English prose.
    assert classify(ENGLISH).label == "english"
    assert classify("The quick brown fox jumps over the lazy dog near a river bank.").label != (
        "roman_urdu"
    )


def test_latin_text_neither_list_explains_is_other_not_a_guess() -> None:
    assert classify("Nikon Canon Sony Fujifilm Olympus Panasonic Leica Sigma Tamron").label == (
        "other"
    )


# --- Code-switching ---------------------------------------------------------


def test_intra_sentential_switching_is_caught() -> None:
    # The common form of Urdu/English switching, and the one a sentence-level-only classifier
    # would file as plain Urdu.
    result = classify(CODE_SWITCHED)
    assert result.label == "code_switched"
    assert result.segments, "a mixed document must carry per-sentence labels"


def test_urdu_quoting_a_foreign_name_is_not_code_switching() -> None:
    # Urdu Wikipedia's geographic stubs. 30% of the source came out code-switched before the
    # Latin side had to be lowercase running text rather than capitalised names.
    text = (
        "سینٹ-موریس، ہوتے-مرنے ( فرانسیسی: Saint-Maurice, Haute-Marne) فرانس کا ایک فرانسیسی "
        "کمیون ہے جو ہوتے-مرنے میں واقع ہے اور یہاں بہت کم لوگ رہتے ہیں۔"
    )
    assert classify(text).label == "urdu"


def test_urdu_with_a_navigation_bar_is_not_code_switching() -> None:
    # Latin-script furniture — menus, category lists, product tables — carries almost no function
    # words, so it scores below `min_evidence` and lands in `other`, which is not an alternation
    # partner. The page stays in the native population where its Urdu belongs.
    navigation = "Home About Contact Login Register Search Menu Categories Archive Sitemap. "
    assert classify(navigation + URDU * 3).label == "urdu"


def test_alternation_needs_a_real_second_language_in_quantity() -> None:
    # Below `alternation_min_share` a document is Urdu with an English footer; above it, the two
    # languages are comparable and it is bilingual.
    assert classify(URDU * 6 + " " + ENGLISH).label == "urdu"
    assert classify(URDU * 2 + " " + ENGLISH * 3).label == "code_switched"


def test_sentence_labels_only_appear_for_mixed_documents() -> None:
    # PRD §6.3.3: document level; sentence level only for mixed docs.
    assert classify(URDU).segments == ()
    assert classify(ENGLISH).segments == ()
    assert classify(CODE_SWITCHED).segments != ()


def test_segment_letters_add_up_to_the_labelled_parts() -> None:
    result = classify(CODE_SWITCHED)
    by_label = result.segment_letters()
    assert sum(by_label.values()) == sum(s.letters for s in result.segments)


# --- Script measurement -----------------------------------------------------


def test_script_ratios_count_letters_not_punctuation_or_digits() -> None:
    ratios, letters = script_ratios("اردو 123 ... !!! ??? ۔۔۔")
    assert letters == 4
    assert ratios == {"arabic": 1.0}


def test_presentation_forms_are_arabic_script() -> None:
    # Stage 4 folds them away, but stage 3 runs first and must not read a page written in
    # presentation forms as scriptless.
    ratios, letters = script_ratios("ﻻ ﺍ ﺏ ﺕ")
    assert letters >= 4
    assert ratios["arabic"] == 1.0


def test_empty_and_tiny_documents_are_labelled_empty_not_guessed() -> None:
    assert classify("").label == "empty"
    assert classify("۔۔۔ 123 !!!").label == "empty"
    assert classify("اردو").label == "empty"  # 4 letters, below min_letters


# --- Config -----------------------------------------------------------------


def test_shipped_config_matches_the_code_defaults() -> None:
    path = Path("configs/data/langid.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload.pop("langid_version") == LANGID_VERSION
    assert LangIDConfig.from_dict(payload) == LangIDConfig()


def test_config_round_trips_through_json(tmp_path: Path) -> None:
    config = LangIDConfig(min_letters=50, code_switch_min_share=0.25)
    path = tmp_path / "langid.json"
    config.to_json_file(path)
    assert LangIDConfig.from_json_file(path) == config
    assert "\r" not in path.read_bytes().decode("utf-8")


def test_unknown_config_keys_are_rejected() -> None:
    with pytest.raises(ValueError, match="unknown langid config keys"):
        LangIDConfig.from_dict({"min_letters": 10, "urdu_threshold": 0.5})


def test_impossible_thresholds_are_rejected() -> None:
    with pytest.raises(ValueError, match="mixed_min_ratio must be <= 0.5"):
        # Above 0.5 nothing can ever be mixed, so the code-switched population would be silently
        # empty rather than absent.
        LangIDConfig(mixed_min_ratio=0.6)
    with pytest.raises(ValueError):
        LangIDConfig(min_letters=0)
    with pytest.raises(ValueError):
        LangIDConfig(min_evidence=1.5)


def test_fingerprint_changes_with_settings_and_is_stable_otherwise() -> None:
    base = LangIDConfig()
    assert base.fingerprint() == LangIDConfig().fingerprint()
    assert base.fingerprint() != LangIDConfig(min_evidence=0.2).fingerprint()


def test_result_carries_the_evidence_that_produced_it() -> None:
    # A label a reader cannot argue with is a label nobody can audit.
    payload = classify(URDU).to_dict()
    assert payload["label"] == "urdu"
    assert payload["scripts"]["arabic"] == 1.0
    assert payload["arabic_scores"]["urdu"] > payload["arabic_scores"]["arabic"]
    assert payload["config_fingerprint"] == LangIDConfig().fingerprint()


# --- Log --------------------------------------------------------------------


def test_log_separates_the_populations_and_the_priors() -> None:
    log = LangIDLog()
    for text in (URDU, ROMAN_URDU, CODE_SWITCHED, ENGLISH, ARABIC):
        log.add(classify(text))
    payload = log.to_dict()
    assert payload["documents"] == 5
    assert payload["documents_kept"] == 3
    assert payload["labels"]["urdu"] == 1
    assert payload["labels"]["code_switched"] == 1
    assert set(payload["letters_by_label"]) == set(payload["labels"])
    assert payload["mixed_documents"] == 1
    assert payload["langid_version"] == LANGID_VERSION
