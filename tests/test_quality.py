"""Engineering invariants for quality filtering (PRD §8.1 — CI, never a results table).

Stage 5 is the first stage that deletes text on grounds of judgement, so the tests that matter
are the ones that catch it deleting the *wrong* text. Three classes of them:

* **Population safety.** A Roman Urdu document must survive the Roman Urdu label and only fail
  under the wrong one. PRD §6.1 budgets three populations and the obvious reading of §6.3.5 — one
  Urdu-script floor — silently empties two of them.
* **Genre safety.** Urdu news copy restates its headline verbatim in the lead paragraph. The
  inherited Gopher repetition thresholds reject 13.7% of FineWeb2 for doing so, and
  ``test_urdu_news_headline_restatement_survives`` is what stops that being reintroduced by
  someone tidying the constants back towards the published values.
* **Rule accounting.** Every failing rule is reported, not just the first, because
  ``sole_rejections`` is how the report can say whether a rule filters anything.

Measured behaviour on real text lives in `reports/probe_*.json`, and the adjudicated sample
that set four of these thresholds is `reports/quality_sample.md` with its scoring in
`reports/quality_validation.md`. These are the rules.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ravaan.data.langid import classify, script_ratios
from ravaan.data.normalization import normalize_text
from ravaan.data.quality import (
    EXPECTED_SCRIPTS,
    QUALITY_VERSION,
    QualityConfig,
    QualityLog,
    check,
    measure,
    score,
)

DEFAULT = QualityConfig()
CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "data" / "quality.json"

# Ordinary Urdu prose, long enough and varied enough to clear every rule. Deliberately not a
# repeated sentence — the fixtures that motivated the repetition thresholds are further down.
CLEAN_URDU = (
    "پاکستان جنوبی ایشیا کا ایک اہم ملک ہے جس کی سرحدیں بھارت، افغانستان، ایران اور چین سے ملتی "
    "ہیں۔ اس کا دارالحکومت اسلام آباد ہے جبکہ کراچی سب سے بڑا شہر اور معاشی مرکز سمجھا جاتا ہے۔ "
    "ملک کی سرکاری زبان اردو ہے، تاہم صوبائی سطح پر پنجابی، سندھی، پشتو اور بلوچی بھی بولی جاتی "
    "ہیں۔ شمالی علاقہ جات اپنے بلند و بالا پہاڑوں کی وجہ سے دنیا بھر کے سیاحوں کو اپنی طرف "
    "متوجہ کرتے ہیں، جہاں کے ٹو دنیا کی دوسری بلند ترین چوٹی واقع ہے۔ معیشت کا بڑا حصہ زراعت پر "
    "منحصر ہے اور گندم، چاول اور کپاس اہم فصلیں شمار ہوتی ہیں۔ حالیہ برسوں میں ٹیکنالوجی کے شعبے "
    "نے بھی نمایاں ترقی کی ہے اور نوجوان نسل سافٹ ویئر برآمدات میں دلچسپی لے رہی ہے۔"
)

CLEAN_ROMAN_URDU = (
    "Pakistan janoobi asia ka aik ahem mulk hai jiski sarhadain India, Afghanistan aur Iran se "
    "milti hain. Iska darulhukoomat Islamabad hai jabke Karachi sabse bara shehr samjha jata "
    "hai. Mulk ki sarkari zaban urdu hai, lekin sooba ki satah par punjabi, sindhi aur pashto "
    "bhi boli jati hain. Shumali ilaqe apne buland pahaaron ki wajah se sailaniyon ko apni taraf "
    "mutawajjah karte hain aur wahan bohat khoobsurat manazir milte hain. Maeeshat ka bara hissa "
    "zaraat par munhasir hai aur gandum, chawal aur kapas ahem faslain shumar hoti hain."
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_shipped_config_matches_code_defaults():
    """The committed config is the defaults, or the manifest describes a filter nobody ran."""
    shipped = QualityConfig.from_json_file(CONFIG_PATH)
    assert shipped == DEFAULT
    assert json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["quality_version"] == QUALITY_VERSION


def test_config_round_trips_through_json(tmp_path):
    config = QualityConfig(min_chars=123, max_url_ratio=0.42)
    path = tmp_path / "quality.json"
    config.to_json_file(path)
    assert QualityConfig.from_json_file(path) == config
    assert QualityConfig.from_json_file(path).fingerprint() == config.fingerprint()


def test_ngram_thresholds_accept_both_json_and_python_forms():
    """A config built in Python and one loaded from JSON must fingerprint identically.

    JSON has no integer keys, so the thresholds arrive as ``{"5": 0.4}`` and the dataclass holds
    ``((5, 0.4),)``. If those two did not normalize to the same value the manifest would record a
    different filter depending on how the run was launched.
    """
    from_json = QualityConfig(max_dup_ngram_ratio={"5": 0.4, "6": 0.38})
    from_python = QualityConfig(max_dup_ngram_ratio=((6, 0.38), (5, 0.4)))
    assert from_json == from_python
    assert from_json.fingerprint() == from_python.fingerprint()


def test_fingerprint_changes_with_any_threshold():
    assert QualityConfig().fingerprint() != QualityConfig(max_url_ratio=0.31).fingerprint()
    assert (
        QualityConfig().fingerprint()
        != QualityConfig(max_dup_ngram_ratio={"5": 0.41, "6": 0.38}).fingerprint()
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_urdu_script_ratio": 1.5},
        {"max_url_ratio": -0.1},
        {"min_chars": -1},
        {"max_repetition_words": 0},
        {"max_dup_ngram_ratio": {"5": 1.5}},
        {"max_dup_ngram_ratio": {"0": 0.5}},
    ],
)
def test_invalid_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        QualityConfig(**kwargs)


def test_unknown_config_key_is_an_error():
    with pytest.raises(ValueError, match="unknown quality config keys"):
        QualityConfig.from_dict({"max_url_ratio": 0.3, "max_emoji_ratio": 0.1})


# ---------------------------------------------------------------------------
# Clean text survives
# ---------------------------------------------------------------------------


def test_clean_urdu_passes_every_rule():
    result = check(CLEAN_URDU)
    assert result.accepted, result.reasons


def test_clean_roman_urdu_passes_under_its_own_label():
    result = check(CLEAN_ROMAN_URDU, label="roman_urdu")
    assert result.accepted, result.reasons


def test_roman_urdu_is_only_rejected_when_labelled_urdu():
    """The whole reason the script rule is per population, in one assertion.

    A single "Urdu-script ratio >= x" floor is the obvious reading of PRD §6.3.5 and it deletes
    the entire ~40M-token Roman Urdu population, which is Latin script by definition.
    """
    assert not check(CLEAN_ROMAN_URDU, label="urdu").accepted
    assert "script_ratio" in check(CLEAN_ROMAN_URDU, label="urdu").reasons
    assert check(CLEAN_ROMAN_URDU, label="roman_urdu").accepted


def test_every_kept_population_has_a_script_expectation():
    """A population stage 3 keeps but stage 5 has no expectation for is unfiltered by accident."""
    from ravaan.data.langid import KEPT_LABELS

    assert set(EXPECTED_SCRIPTS) >= KEPT_LABELS


def test_urdu_news_headline_restatement_survives():
    """The regression that locks the repetition calibration.

    Urdu news wire copy repeats the headline verbatim as the first sentence of the body. Under
    Rae et al.'s Gopher thresholds this is 20%+ duplicate 5-grams and the document is rejected;
    measured on FineWeb2 that pattern alone accounts for most of a 13.7% rejection rate on the
    cleanest large source in the corpus. If someone restores the published constants, this fails.
    """
    headline = "وزیر اعظم نے قومی اسمبلی میں معاشی اصلاحات کے نئے پیکج کا اعلان کر دیا"
    body = (
        f"{headline}\n"
        f"اسلام آباد (نامہ نگار) {headline}۔ ان کا کہنا تھا کہ اس پیکج سے برآمدات میں اضافہ ہوگا "
        "اور روزگار کے نئے مواقع پیدا ہوں گے۔ وزیر خزانہ نے بریفنگ دیتے ہوئے بتایا کہ اصلاحات کا "
        "پہلا مرحلہ اگلے مالی سال سے شروع کیا جائے گا، جس میں ٹیکس نظام کو آسان بنایا جائے گا۔ "
        "اجلاس میں اپوزیشن جماعتوں نے بھی اپنی تجاویز پیش کیں اور مشترکہ کمیٹی بنانے پر اتفاق "
        "کیا گیا۔ ماہرین کے مطابق ان اقدامات کے نتائج آئندہ دو برس میں سامنے آنا شروع ہوں گے۔"
    )
    result = check(body)
    assert result.accepted, result.reasons


def test_wikipedia_biography_survives_the_duplicate_ngram_rules():
    """The second regression from the 200-sample validation.

    An article about one person repeats that person's name and the formulae of the genre
    ("… پنجاب کی صوبائی اسمبلی کے رکن رہے"), which scored 0.41–0.60 on duplicate 5-grams and got
    clean biographies deleted. Real boilerplate shows up on the *top*-n-gram side instead, which
    is what `test_disambiguation_list_page_is_rejected` covers.
    """
    name = "قاضی احمد سعید"
    text = (
        f"{name}، ایک پاکستانی سیاست دان ہیں جو 2002 سے مئی 2018 تک پنجاب کی صوبائی اسمبلی کے "
        "رکن رہے۔\n\nابتدائی زندگی اور تعلیم\n"
        f"{name} یکم جون 1968 کو ضلع رحیم یار خان میں پیدا ہوئے۔ انہوں نے قانون کی بیچلر کی ڈگری "
        "1993 میں کراچی یونیورسٹی سے حاصل کی اور ماسٹر آف آرٹس کی ڈگری 1995 میں شاہ عبداللطیف "
        "یونیورسٹی سے حاصل کی۔\n\nسیاسی کیریئر\n"
        f"{name} 2002 کے پاکستانی عام انتخابات میں حلقہ پی پی 246 سے پاکستان مسلم لیگ (ق) کے "
        "امیدوار کے طور پر پنجاب کی صوبائی اسمبلی کے لیے منتخب ہوئے۔ وہ 2008 کے پاکستانی عام "
        "انتخابات میں حلقہ پی پی 246 سے پاکستان پیپلز پارٹی کے امیدوار کے طور پر پنجاب کی صوبائی "
        "اسمبلی کے لیے دوبارہ منتخب ہوئے۔\n\nحوالہ جات\n"
        "1968ء کی پیدائشیں\nپنجاب ارکان صوبائی اسمبلی 2002ء تا 2007ء\nبقید حیات شخصیات\n"
    )
    result = check(text)
    assert result.accepted, result.reasons


def test_disambiguation_list_page_is_rejected():
    """The other side of the same split: a list page must still go.

    "بفیلو ٹاؤن شپ" once per county is boilerplate by any reading, and it is caught by the
    top-n-gram rules rather than the duplicate ones.
    """
    counties = [
        "کریگہیڈ کاؤنٹی، آرکنساس",
        "ماریون کاؤنٹی، آرکنساس",
        "اوگل کاؤنٹی، الینوائے",
        "بیوکینن کاؤنٹی، آئیووا",
        "کوسوتھ کاؤنٹی، آئیووا",
        "لین کاؤنٹی، آئیووا",
        "سکاٹ کاؤنٹی، آئیووا",
        "لنکن کاؤنٹی، مسوری",
        "ڈالاس کاؤنٹی، مسوری",
        "پیری کاؤنٹی، پنسلوانیا",
    ]
    text = "بفیلو ٹاؤن شپ کے لیے آپ مندرجہ ذیل صفحات سے رجوع کر سکتے ہیں۔\n\n" + "\n".join(
        f"بفیلو ٹاؤن شپ، {county}" for county in counties
    )
    result = check(text)
    assert any(r.startswith("repetition:top_") for r in result.reasons), result.reasons


def test_bigrams_are_not_a_repetition_rule():
    """n=2 measures subject matter in Urdu, not boilerplate.

    A long article about children's rights repeats بچوں کے because that is what it is about; the
    bigram rule scored it 0.38 and was the only top-n-gram rule with a false positive in the
    200-sample validation. Absence of n=2 is a decision, so it is asserted rather than assumed.
    """
    assert 2 not in dict(DEFAULT.max_top_ngram_ratio)
    assert {3, 4} <= set(dict(DEFAULT.max_top_ngram_ratio))


def test_wikipedia_template_stub_is_rejected():
    """The largest single result of the validation: 200 characters was far too low a floor.

    One factual sentence wrapped in section headers and category footers, ~300 characters. At
    `min_chars=200` the filter kept these and they were 24 of the 91 documents a human dropped.
    """
    stub = (
        "جاروسان ایران کا ایک رہائشی علاقہ جو Kakavand-e Gharbi Rural District میں واقع ہے۔\n\n"
        "تفصیلات\nجاروسان کی مجموعی آبادی 77 افراد پر مشتمل ہے۔\n\n"
        "مزید دیکھیے\nایران\nفہرست ایران کے شہر\n\nحوالہ جات\n\n"
        "جغرافیہ شہرستان دلفان کے نامکمل مضامین\n"
    )
    assert "too_short" in check(stub).reasons


def test_empty_and_whitespace_documents_are_rejected_not_crashed():
    for text in ("", "   \n\n  "):
        result = check(text)
        assert not result.accepted
        assert "too_short" in result.reasons


# ---------------------------------------------------------------------------
# Each rule fires on what it is for
# ---------------------------------------------------------------------------


def test_too_short_fires_on_a_stub():
    assert "too_short" in check("یہ ایک مختصر صفحہ ہے۔").reasons


def test_script_ratio_fires_when_another_script_takes_over():
    english = "This is a long English passage that dominates the document. " * 12
    text = CLEAN_URDU[:200] + " " + english
    assert "script_ratio" in check(text).reasons


def test_repetition_fires_on_a_genuinely_degenerate_document():
    text = "یہ سطر بار بار دہرائی گئی ہے اور اس میں کوئی نئی معلومات نہیں ہے۔\n" * 30
    reasons = check(text).reasons
    assert any(r.startswith("repetition:") for r in reasons), reasons


def test_duplicate_lines_are_measured_by_characters_not_lines():
    """One repeated paragraph must weigh more than one repeated word."""
    long_line = "یہ ایک خاصی طویل سطر ہے جو دستاویز میں دو مرتبہ ظاہر ہوتی ہے اور بہت جگہ لیتی ہے۔"
    text = f"{long_line}\n{long_line}\nمختصر\nالف\nب\nج\n"
    metrics = measure(text)
    assert metrics.dup_line_ratio > 0.9


def test_url_density_fires_on_a_link_farm():
    text = " ".join(f"https://example.com/page/{i}/article-title-here" for i in range(40))
    assert "url_density" in check(text, label="other").reasons


def test_html_residue_fires_on_leftover_markup():
    text = "<div class='content'><p>" + CLEAN_URDU[:300] + "</p></div>" + "<span>x</span>" * 12
    assert "html_residue" in check(text).reasons


def test_wiki_markup_counts_as_html_residue():
    """`<ref>` and `<noinclude>` are matched by the same pattern. Observed on Urdu Wikipedia."""
    text = CLEAN_URDU[:250] + "<noinclude>" + "<ref name=census>" * 10 + "</ref>" * 10
    assert "html_residue" in check(text).reasons


def test_replacement_chars_fire_above_the_rate():
    text = CLEAN_URDU + "�" * 40
    assert "replacement_chars" in check(text).reasons


def test_ordinary_angle_brackets_are_not_html():
    """`<` followed by prose is not a tag. A tag detector that thinks otherwise deletes text."""
    text = CLEAN_URDU + " ریاضی میں 5 < 7 اور 9 > 2 لکھا جاتا ہے۔"
    assert measure(text).html_ratio == 0.0


# ---------------------------------------------------------------------------
# Rule accounting
# ---------------------------------------------------------------------------


def test_every_failing_rule_is_reported_not_only_the_first():
    text = "<div class='x'><p>" * 8 + " ".join(
        f"https://example.com/{i}" for i in range(30)
    )
    families = check(text, label="other").families
    assert {"url_density", "html_residue"} <= set(families)


def test_families_collapse_the_repetition_detail():
    text = "یہ سطر بار بار دہرائی گئی ہے اور اس میں کوئی نئی معلومات نہیں ہے۔\n" * 30
    result = check(text)
    assert result.families.count("repetition") == 1
    assert len([r for r in result.reasons if r.startswith("repetition:")]) > 1


def test_log_counts_sole_rejections_separately():
    log = QualityLog()
    log.add(check(CLEAN_URDU))
    log.add(check("مختصر"))  # too_short only
    two_family = "<div class='x'><p>" * 8 + " ".join(
        f"https://example.com/{i}" for i in range(30)
    )
    log.add(check(two_family, label="other"))  # url_density + html_residue
    payload = log.to_dict()
    assert payload["documents"] == 3
    assert payload["documents_kept"] == 1
    assert payload["sole_rejections"].get("too_short") == 1
    # The two-family rejection contributes to `families` but to no `sole_rejections` entry.
    assert payload["families"]["url_density"] == 1
    assert "url_density" not in payload["sole_rejections"]


def test_log_tracks_characters_by_population():
    log = QualityLog()
    log.add(check(CLEAN_URDU))
    log.add(check(CLEAN_ROMAN_URDU, label="roman_urdu"))
    payload = log.to_dict()
    assert payload["chars_kept_by_label"]["urdu"] == len(CLEAN_URDU)
    assert payload["chars_kept_by_label"]["roman_urdu"] == len(CLEAN_ROMAN_URDU)


# ---------------------------------------------------------------------------
# Measurement is separable from scoring
# ---------------------------------------------------------------------------


def test_metrics_can_be_rescored_under_a_new_config_without_the_text():
    """What makes tuning a threshold against the 200-sample validation a minute's work."""
    text = CLEAN_URDU
    metrics = measure(text)
    assert score(metrics, DEFAULT, "urdu") == ()
    strict = QualityConfig(min_chars=100_000)
    assert "too_short" in score(metrics, strict, "urdu")


def test_top_ngram_ratio_is_capped_at_one():
    """Overlapping occurrences can exceed the document length; a ratio above 1 is meaningless."""
    metrics = measure("aa " * 400)
    assert all(0.0 <= v <= 1.0 for _, v in metrics.top_ngram_ratio)


def test_duplicate_ngram_spans_are_merged_not_summed():
    """Summing consecutive n-gram spans double-counts their overlap.

    A document that is one repeated sentence is ~100% duplicate characters, not 500%. If this
    regresses, mildly repetitive documents inflate past every threshold at once.
    """
    sentence = "الف بے جیم دال ہے کاف لام میم نون واو "
    metrics = measure(sentence * 4)
    assert all(v <= 1.0 for _, v in metrics.dup_ngram_ratio)
    assert dict(metrics.dup_ngram_ratio)[5] > 0.8


def test_repetition_analysis_is_capped_and_says_so():
    config = QualityConfig(max_repetition_words=500)
    metrics = measure("لفظ " * 2000, config)
    assert metrics.repetition_truncated
    assert metrics.words == 2000  # the true count, not the examined one


def test_untruncated_documents_are_not_flagged():
    assert not measure(CLEAN_URDU).repetition_truncated


# ---------------------------------------------------------------------------
# Reuse of stage 3's measurements
# ---------------------------------------------------------------------------


def test_script_ratios_from_stage_3_give_the_same_verdict():
    """Passing stage 3's ratios must not change the answer, or the reuse is a bug."""
    result = classify(CLEAN_URDU)
    reused = check(CLEAN_URDU, label=result.label, scripts=result.scripts, letters=result.letters)
    recomputed = check(CLEAN_URDU, label=result.label)
    assert reused.reasons == recomputed.reasons
    assert reused.metrics.script_ratio == pytest.approx(recomputed.metrics.script_ratio)


def test_script_ratios_survive_normalization():
    """Why reusing stage 3's ratios is sound although stage 3 runs before stage 4.

    Stage 4 folds presentation forms to Arabic-block letters, maps digits and strips zero-width
    and bidi marks — none of the latter are letters and none are counted. The one real difference
    is tatweel (U+0640), which *is* category Lm and which stage 4 removes, so the tolerance is not
    zero. It is small enough that no threshold moves.
    """
    dirty = "ﻻ " + CLEAN_URDU.replace("ی", "ي") + " ـــ ١٢٣ ‌‏"
    before, _ = script_ratios(dirty)
    after, _ = script_ratios(normalize_text(dirty))
    assert after.get("arabic", 0.0) == pytest.approx(before.get("arabic", 0.0), abs=0.01)


# ---------------------------------------------------------------------------
# Sentence-unit sources
# ---------------------------------------------------------------------------


def test_sentence_config_keeps_a_single_roman_urdu_sentence():
    """Roman-Urdu-Parl rows are ~45-char sentences; the document rules would delete them all."""
    sentence = "yeh aik saaf urdu jumla hai aur is mein koi kharabi nahi hai"
    assert not check(sentence, label="roman_urdu").accepted
    assert check(sentence, DEFAULT.for_sentences(), label="roman_urdu").accepted


def test_sentence_config_is_a_distinct_fingerprint():
    """Which rules ran on which source has to be visible in the manifest, not implicit."""
    assert DEFAULT.for_sentences().fingerprint() != DEFAULT.fingerprint()
