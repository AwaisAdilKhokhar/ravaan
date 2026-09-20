"""Engineering invariants for evaluation decontamination (PRD §8.1 — CI, never a results table).

Stage 8 is the stage whose failure is *silent*. Stages 2–7 announce themselves: a bad threshold
deletes documents somebody notices, a bad hash makes duplicate counts implausible. A stage 8 that
misses contamination emits no error, removes nothing, and hands back a clean corpus and a confident
zero — and the cost lands months later on §8.2's evaluation numbers, which are what the project
reports. So these tests are weighted toward *detection*, and the ones that matter most assert that
something is found rather than that nothing is broken.

Three are acceptance tests written from measurements taken before the code existed:

* **Finding M** — of 49 sampled cross-source pairs, 11 fall below a 0.80 Jaccard cut, the clearest
  being J = 0.656 with containment 1.000 at 150/96 shingles. ``test_containment_catches_what_a_
  jaccard_threshold_misses`` is that pair's shape, and it is the reason this stage does not reuse
  stage 7's threshold.
* **Finding L** — the hash half returns a confident zero on the wiki path (processed wikitext
  against a rendered page, never byte-identical). ``test_the_exact_half_is_blind_to_the_wiki_path``
  asserts the blindness *and* that the fuzzy half covers it, because the failure being tested is
  the two halves being reported as one number.
* **The banding cannot be retuned to fix this**, measured in session 10: an eval item verbatim
  inside a 15×-longer document scores J ≈ 0.067, which the shipped (32, 4) banding proposes with
  probability 0.0006. ``test_the_contamination_shape_is_invisible_to_stage_7_banding`` pins the
  arithmetic so a later "just reuse the sketch" cannot quietly reintroduce it.

Measured behaviour on real text lives in `reports/probe_decontamination_*.json`. These are the
rules.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ravaan.data.decontamination import (
    DECONTAMINATION_VERSION,
    ContaminationHit,
    DecontaminationConfig,
    Decontaminator,
    EvalSetSpec,
    containment_of,
    decontaminate,
)
from ravaan.data.minhash import MinHashConfig, shingle_hashes

DEFAULT = DecontaminationConfig()
CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "data" / "decontamination.json"

URDU_ARTICLE = (
    "پاکستان جنوبی ایشیا کا ایک اہم ملک ہے جس کی سرحدیں بھارت، افغانستان، ایران اور چین سے ملتی "
    "ہیں۔ اس کا دارالحکومت اسلام آباد ہے جبکہ کراچی سب سے بڑا شہر اور ملک کا معاشی مرکز سمجھا "
    "جاتا ہے۔ ملک کی آبادی بائیس کروڑ سے زیادہ ہے اور یہاں کئی زبانیں بولی جاتی ہیں جن میں اردو "
    "قومی زبان کی حیثیت رکھتی ہے۔ پاکستان کی معیشت کا انحصار زراعت، صنعت اور خدمات کے شعبوں پر ہے "
    "اور حالیہ برسوں میں اطلاعاتی ٹیکنالوجی کا شعبہ بھی تیزی سے ترقی کر رہا ہے۔"
)

URDU_UNRELATED = (
    "اردو زبان کی ترقی میں شاعروں اور ادیبوں نے نمایاں کردار ادا کیا ہے۔ غالب، اقبال اور فیض کی "
    "شاعری آج بھی برصغیر کے قارئین میں یکساں مقبول ہے اور نئی نسل اسے شوق سے پڑھتی ہے۔ اردو نثر "
    "میں ناول اور افسانے کی روایت انیسویں صدی کے آخر میں مضبوط ہوئی اور بیسویں صدی میں اس نے "
    "عالمی ادب کے ساتھ قدم ملا کر چلنا شروع کیا۔"
)

# Finding L's mechanism, in the shape FineWeb2's HTML-to-text extraction carries it. The article is
# unchanged inside; everything around it is the rendering, which is why no hash can match.
WIKI_CHROME_HEAD = (
    "ویکیپیڈیا آزاد دائرۃ المعارف\nمضمون تبادلۂ خیال پڑھیں ترمیم کریں تاریخ دیکھیں تلاش کریں\n"
    "رابطہ عامہ عطیہ دیجیے حالیہ تبدیلیاں نیا صفحہ بےترتیب مضمون\n"
)
WIKI_CHROME_TAIL = (
    "\nمزید دیکھیے حوالہ جات بیرونی روابط\nزمرہ جات: ایشیا کے ممالک جنوبی ایشیا اقوام متحدہ کے "
    "رکن ممالک\nاس صفحے میں آخری بار ترمیم بتاریخ چودہ مارچ کو ہوئی۔ تحریر بموجب اجازت نامہ۔\n"
)

# Sized to the real file rather than invented: Roman-Urdu-Parl's test rows measure 39 characters
# and 4 word-5-grams at the median, and this is 39 / 3 / 35. A comfortable fixture would have hidden
# the whole problem — at 74 characters the same sentence clears min_shingles in *words* and the
# per-set shingling looks unnecessary.
ROMAN_SENTENCE = "hukumat ne naya mansooba shuru kiya hai"

# Above min_line_chars, for the embedded-line case. Deliberately a different object from the one
# above: the median test row is *below* that floor, which is a real interaction and not a fixture
# convenience — see the report. Containment is what covers the short ones.
ROMAN_LINE = "hukumat ne naye taleemi mansoobe ka elaan kiya hai jo agle saal shuru hoga"

SENTENCE_SPEC = EvalSetSpec(name="roman-urdu-parl-test", shingle_unit="char")


def _sealed(*items: tuple[str, str, str], config: DecontaminationConfig | None = None,
            specs: tuple[EvalSetSpec, ...] = ()) -> Decontaminator:
    index = Decontaminator(config)
    for spec in specs:
        index.add_eval_set(spec)
    for eval_set, item_id, text in items:
        index.add_eval_item(eval_set, item_id, text)
    index.seal()
    return index


# ---------------------------------------------------------------------------
# The acceptance tests — written from measurements, before the code
# ---------------------------------------------------------------------------


def test_containment_catches_what_a_jaccard_threshold_misses():
    """Finding M's pair: containment 1.000 at a Jaccard well under stage 7's 0.80 cut.

    The measured original is J = 0.656 with containment 1.000 at 150/96 shingles. If stage 8 had
    inherited stage 7's Jaccard threshold — the obvious reuse, and the one session 9's handoff
    proposed — this document would have been declared clean while containing the entire eval item.

    The exact half is switched off so this measures the fuzzy half alone. Left on, line hashing
    catches this document first, which is a true result and the wrong one to assert here.
    """
    fuzzy_only = DecontaminationConfig(exact_document_match=False, exact_line_match=False)
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE), config=fuzzy_only)
    contaminated = WIKI_CHROME_HEAD + URDU_ARTICLE + WIKI_CHROME_TAIL

    verdict = index.check("fineweb2:1", contaminated)
    assert not verdict.kept
    assert verdict.reason == "contaminated"
    assert verdict.eval_id == "eval:1"

    hit = index.hits()[0]
    assert hit.containment == 1.0, "every shingle of the article is present in the rendered page"
    assert hit.jaccard < DEFAULT.containment_threshold, (
        "the whole point: this pair sits below the threshold stage 7 decides on, so a Jaccard-"
        "scored decontamination would clear a document that contains the entire eval item"
    )


def test_the_contamination_shape_is_invisible_to_stage_7_banding():
    """An eval item verbatim inside a long document is not a candidate stage 7 would ever propose.

    This is why stage 8 holds the eval sets exactly instead of sketching them. Not a style
    preference: the sketch is an estimator of Jaccard and LSH proposes by Jaccard, so the pair has
    to *become a candidate* before any containment could be computed from it — and at these sizes
    it does not.
    """
    eval_text = " ".join(f"word{i}" for i in range(120))
    document = eval_text + " " + " ".join(f"chrome{i}" for i in range(1400))

    index = _sealed(("held-out", "eval:1", eval_text))
    verdict = index.check("doc:1", document)
    hit = index.hits()[0]

    assert not verdict.kept and hit.containment == 1.0
    proposed = MinHashConfig().candidate_probability(hit.jaccard)
    assert proposed < 0.01, (
        f"stage 7's shipped banding would propose this pair with probability {proposed:.6f}; "
        "stage 8 finds it because it does not use banding at all"
    )


def test_the_exact_half_is_blind_to_the_wiki_path_and_the_fuzzy_half_is_not():
    """Finding L, as an invariant: hashing returns zero on exactly the path that matters most.

    §6.3.8 says "hash + fuzzy match" as though the two were co-equal. On this population they are
    not, and the test asserts both directions — that the hash finds nothing, and that the document
    is caught anyway — because the failure being guarded against is a stage 8 that reports the two
    halves as one number and calls a hash-only zero a clean corpus.
    """
    contaminated = WIKI_CHROME_HEAD + URDU_ARTICLE + WIKI_CHROME_TAIL

    hash_only = DecontaminationConfig(containment_threshold=1.0, retain_hits_above=1.0)
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE), config=hash_only)
    # The article's own lines survive rendering intact, so line-level hashing *does* see this one.
    # Document-level hashing — what "hash match" is normally taken to mean — does not.
    assert index.check("fineweb2:1", contaminated).reason != "exact_document"

    no_lines = DecontaminationConfig(exact_line_match=False)
    fuzzy = _sealed(("held-out", "eval:1", URDU_ARTICLE), config=no_lines)
    verdict = fuzzy.check("fineweb2:1", contaminated)
    assert not verdict.kept and verdict.reason == "contaminated"


# ---------------------------------------------------------------------------
# Direction — the thing stage 7's containment helper gets right for stage 7 and wrong here
# ---------------------------------------------------------------------------


def test_containment_is_directed_at_the_eval_item():
    """A short training document overlapping a long eval item is not contamination.

    ``min(|A|, |B|)`` — stage 7's denominator — would call this 100% contained and delete a clean
    document. Stage 8's question has a subject: how much of the *test item* is in the training text.
    """
    long_eval = " ".join(f"word{i}" for i in range(300))
    short_doc = " ".join(f"word{i}" for i in range(20))

    index = _sealed(("held-out", "eval:1", long_eval))
    verdict = index.check("doc:1", short_doc)
    assert verdict.kept, "20 shingles of a 300-shingle eval item is 7% of it, not 100%"


def test_containment_of_divides_by_the_eval_item():
    assert containment_of(50, 100) == 0.5
    assert containment_of(100, 100) == 1.0
    assert containment_of(0, 100) == 0.0
    assert containment_of(5, 0) == 0.0, "an unmeasurable item is not 100% contaminated"
    assert containment_of(120, 100) == 1.0, "clamped — a caller passing an over-count has a bug"


def test_a_document_containing_the_eval_item_is_removed_not_the_eval_item():
    """Stage 8 never shrinks a test set to fit the corpus. There is no survivor rule here.

    Stages 6 and 7 choose *between* two copies; stage 8 has a subject and an object, and the object
    is always the training document. A stage 8 that dropped eval items would improve every metric it
    touched, which is precisely why it must be impossible rather than merely discouraged.
    """
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE))
    index.check("doc:1", WIKI_CHROME_HEAD + URDU_ARTICLE)
    assert index.log.eval_items == 1
    assert index.log.eval_sets["held-out"] == 1
    assert index.log.eval_coverage()["held-out"]["items"] == 1
    assert index.log.removed == 1


# ---------------------------------------------------------------------------
# Both halves of §6.3.8
# ---------------------------------------------------------------------------


def test_an_identical_document_is_an_exact_match():
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE))
    verdict = index.check("doc:1", URDU_ARTICLE)
    assert not verdict.kept and verdict.reason == "exact_document"


def test_exact_matching_sees_through_whitespace_and_case():
    """The exact half canonicalizes with stage 6's rule, so the two stages agree what "same" is."""
    index = _sealed(("held-out", "eval:1", ROMAN_SENTENCE), specs=(SENTENCE_SPEC,))
    index_set = _sealed(("roman-urdu-parl-test", "eval:1", ROMAN_SENTENCE), specs=(SENTENCE_SPEC,))
    assert not index.check("doc:1", f"  {ROMAN_SENTENCE.upper()}  \n").kept
    assert not index_set.check("doc:1", ROMAN_SENTENCE.replace(" ", "  ")).kept


def test_an_eval_sentence_quoted_as_one_line_is_caught_by_the_line_half():
    """The shape document-level hashing structurally cannot see, and every sentence-unit set has.

    §8.2's transliteration and real-OCR sets are sentences and lines. A training document quoting
    one of them is not equal to it and never will be, so document hashing is the wrong instrument
    and containment over a 4,000-shingle document is a weak one. Line hashing is exact and cheap.
    """
    document = f"{URDU_UNRELATED}\n{ROMAN_LINE}\n{URDU_ARTICLE}"
    index = _sealed(("roman-urdu-parl-test", "eval:1", ROMAN_LINE), specs=(SENTENCE_SPEC,))
    verdict = index.check("doc:1", document)
    assert not verdict.kept and verdict.reason == "exact_line"
    assert verdict.eval_id == "eval:1"


def test_short_lines_are_not_indexed_for_exact_matching():
    """"اہم خبریں" is a true exact match against thousands of documents and evidence of nothing."""
    index = _sealed(("held-out", "eval:1", "اہم خبریں"))
    assert index.log.eval_lines == 0
    assert index.check("doc:1", f"اہم خبریں\n{URDU_UNRELATED}").kept


def test_the_two_halves_can_be_switched_off_independently():
    both_off = DecontaminationConfig(exact_document_match=False, exact_line_match=False)
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE), config=both_off)
    verdict = index.check("doc:1", URDU_ARTICLE)
    assert not verdict.kept
    assert verdict.reason == "contaminated", "an identical document is also 100% contained"


# ---------------------------------------------------------------------------
# Per-set shingling — 77.8% of Roman-Urdu-Parl's test rows are unmeasurable in words
# ---------------------------------------------------------------------------


def test_a_sentence_eval_set_is_measurable_in_characters_and_not_in_words():
    """Measured on the real file: 77.8% of test rows carry fewer than 8 word-5-grams, 2.6% in char.

    This is why :class:`EvalSetSpec` exists. One global shingling would leave stage 8 blind to an
    entire test set while reporting a clean number for it.
    """
    words = len(shingle_hashes(ROMAN_SENTENCE, size=5, unit="word"))
    chars = len(shingle_hashes(ROMAN_SENTENCE, size=5, unit="char"))
    assert words < DEFAULT.min_shingles <= chars

    word_index = _sealed(("roman-urdu-parl-test", "eval:1", ROMAN_SENTENCE))
    assert word_index.log.eval_items_unmeasurable == 1, "counted, and reported — never silent"

    char_index = _sealed(("roman-urdu-parl-test", "eval:1", ROMAN_SENTENCE), specs=(SENTENCE_SPEC,))
    assert char_index.log.eval_items_unmeasurable == 0


def test_an_unmeasurable_eval_item_is_still_covered_by_the_exact_half():
    """The reason the exact half is not optional: it is the only cover for unshingleable items.

    The Roman-Urdu-Parl path exactly — a test row that is 3 word-5-grams long, reappearing as a
    training row of its own. Containment cannot score it; the document hash does not need to.
    """
    index = _sealed(("roman-urdu-parl-test", "eval:1", ROMAN_SENTENCE))  # word shingles: too short
    assert index.log.eval_items_unmeasurable == 1
    verdict = index.check("train-row:1", ROMAN_SENTENCE)
    assert not verdict.kept and verdict.reason == "exact_document"


def test_the_median_test_row_is_below_min_line_chars_and_containment_covers_it():
    """A real interaction between two defaults, pinned rather than discovered later.

    Roman-Urdu-Parl's median test row is 39 characters, and ``min_line_chars`` is 40 — so the line
    half deliberately does *not* index it, because a 39-character line matches too much to be
    evidence. That leaves one instrument for "this test sentence is quoted inside a longer training
    document", and it is character-shingle containment. The test asserts the gap is covered, not
    that it does not exist.
    """
    assert len(ROMAN_SENTENCE) < DEFAULT.min_line_chars

    index = _sealed(("roman-urdu-parl-test", "eval:1", ROMAN_SENTENCE), specs=(SENTENCE_SPEC,))
    assert index.log.eval_lines == 0, "too short to be indexed as a line"

    verdict = index.check("doc:1", f"{URDU_UNRELATED} {ROMAN_SENTENCE}")
    assert not verdict.kept and verdict.reason == "contaminated"


def test_for_sentences_moves_all_four_settings_together():
    """They were measured together on real hits, so they travel together — stage 5's pattern."""
    spec = EvalSetSpec(name="roman-urdu-parl-test").for_sentences()
    assert spec.shingle_unit == "char"
    assert spec.min_shingles == 25
    assert spec.containment_threshold == 0.90
    assert spec.retain_hits_above == 0.80
    assert spec.name == "roman-urdu-parl-test"


def test_the_sentence_retention_floor_keeps_a_full_pass_under_its_ceiling():
    """A freeze-time hazard, pinned: the global 0.50 floor would blow the ceiling on FineWeb2.

    A 30-shingle test sentence shares half its character 5-grams with a long article constantly.
    Measured on Urdu Wikipedia, a 0.50 floor retains **11.9 hits per document** of which 0.05% are
    above threshold — ~17.7M over a full FineWeb2 shard against a 20M ceiling, i.e. a MemoryError
    hours into the pass that writes the frozen corpus. This asserts the floor that prevents it, and
    that it still brackets the 0.90 decision from below so `sweep()` stays useful.
    """
    spec = EvalSetSpec(name="s").for_sentences()
    assert spec.retain_hits_above < spec.containment_threshold, "must still bracket the decision"

    # A 70% prefix scores containment 0.685 — squarely between the two floors, which is exactly the
    # partial-overlap band a long article hits by chance and where all the retained noise lives.
    sentence = "hukumat ne naya mansooba shuru kiya hai aur logon ne khush hokar istaqbal kiya"
    article = f"{URDU_UNRELATED} {sentence[: int(len(sentence) * 0.70)]} {URDU_ARTICLE}"

    loose = _sealed(
        ("s", "eval:1", sentence),
        specs=(replace(spec, retain_hits_above=0.50),),
    )
    loose.check("doc:1", article)

    tight = _sealed(("s", "eval:1", sentence), specs=(spec,))
    tight.check("doc:1", article)

    assert tight.log.hits_retained < loose.log.hits_retained, (
        "the partial-overlap noise a 0.50 floor retains is what fills the ceiling"
    )
    assert tight.log.removed == loose.log.removed, "and none of it changed a verdict"


@pytest.mark.parametrize("threshold", [0.80, 0.90, 0.75, 0.60, 0.95])
def test_a_document_exactly_at_the_threshold_is_removed(threshold):
    """The boundary is inclusive at the value the config *declares*, not near it.

    A regression for a real bug: the per-set thresholds were first stored in an ``array("f")``, and
    single precision rounds 0.80 **up** to 0.80000001192. A document containing exactly 0.80 of an
    eval item — 20 of 25 shingles, ordinary at these sizes — then compared as below threshold and
    was kept. Silent, boundary-only, and on the removal side, which is the direction this stage
    cannot afford. Caught because a histogram band that could not have changed lost 16 hits.
    """
    total = 100
    hit = round(total * threshold)
    eval_text = " ".join(f"word{i}" for i in range(total + 4))
    document = " ".join(f"word{i}" for i in range(hit + 4))

    index = _sealed(
        ("s", "eval:1", eval_text),
        specs=(EvalSetSpec(name="s", containment_threshold=threshold, retain_hits_above=0.1),),
    )
    verdict = index.check("doc:1", document)
    measured = index.hits()[0].containment
    assert measured == pytest.approx(threshold, abs=1e-9), "fixture must land *on* the boundary"
    assert not verdict.kept, f"containment {measured!r} should meet a threshold of {threshold!r}"


def test_the_sweep_reports_the_highest_per_set_floor_not_the_config_one():
    """With per-set floors, a single config number would lie about the half it does not cover."""
    index = Decontaminator()
    index.add_eval_set(EvalSetSpec(name="documents"))  # floor 0.50 from the config
    index.add_eval_set(EvalSetSpec(name="sentences").for_sentences())  # floor 0.80
    index.add_eval_item("documents", "a", URDU_ARTICLE)
    index.add_eval_item("sentences", "b", URDU_ARTICLE)
    index.seal()
    index.check("doc:1", URDU_ARTICLE)

    row = index.sweep([0.6])[0]
    assert "note" in row and "0.80" in row["note"]


def test_min_shingles_means_two_different_things_in_the_two_units():
    """The measured bug behind ``for_sentences``: one number, two meanings, nothing saying so.

    Eight shingles is ~12 words in the word unit and ~12 *characters* in the character unit. At the
    global floor of 8, two thirds of every hit measured on real text came from 12-to-19-character
    fragments — genuinely contained, and evidence of nothing.
    """
    fragment = "angrezi blog"  # 12 characters: a real hit from the first Roman-Urdu-Parl pass
    assert len(shingle_hashes(fragment, size=5, unit="char")) >= DEFAULT.min_shingles
    assert len(shingle_hashes(fragment, size=5, unit="word")) < DEFAULT.min_shingles

    haystack = "az rashid Kamraan urdu blog angrezi blog az Shah"
    loose = _sealed(
        ("roman-urdu-parl-test", "eval:1", fragment),
        specs=(EvalSetSpec(name="roman-urdu-parl-test", shingle_unit="char"),),
    )
    assert not loose.check("doc:1", haystack).kept, "the false positive the global floor admits"

    measured = _sealed(
        ("roman-urdu-parl-test", "eval:1", fragment),
        specs=(EvalSetSpec(name="roman-urdu-parl-test").for_sentences(),),
    )
    assert measured.check("doc:1", haystack).kept
    assert measured.log.eval_items_unmeasurable == 1, "excluded from containment, not from the run"


def test_a_per_set_threshold_overrides_the_stage_default():
    """A template that clears 0.80 and not 0.90 — the family the sentence variant exists to drop."""
    eval_text = " ".join(f"word{i}" for i in range(100))
    partial = " ".join(f"word{i}" for i in range(85)) + " " + URDU_UNRELATED

    lenient = _sealed(("s", "eval:1", eval_text), specs=(EvalSetSpec(name="s"),))
    assert not lenient.check("doc:1", partial).kept

    strict = _sealed(
        ("s", "eval:1", eval_text),
        specs=(EvalSetSpec(name="s", containment_threshold=0.90),),
    )
    assert strict.check("doc:1", partial).kept


def test_per_set_thresholds_are_independent_of_each_other():
    """Two test sets, two thresholds, one pass — the reason these live on the spec at all."""
    eval_text = " ".join(f"word{i}" for i in range(100))
    partial = " ".join(f"word{i}" for i in range(85)) + " " + URDU_UNRELATED
    index = Decontaminator()
    index.add_eval_set(EvalSetSpec(name="lenient", containment_threshold=0.80))
    index.add_eval_set(EvalSetSpec(name="strict", containment_threshold=0.95))
    index.add_eval_item("lenient", "a", eval_text)
    index.add_eval_item("strict", "b", eval_text)
    index.seal()

    verdict = index.check("doc:1", partial)
    assert not verdict.kept and verdict.eval_set == "lenient"


def test_a_per_set_threshold_lands_in_the_report():
    """It changes which documents survive, so it has to be visible in the manifest."""
    index = _sealed(
        ("s", "eval:1", URDU_ARTICLE),
        specs=(EvalSetSpec(name="s").for_sentences(),),
    )
    spec = index.to_dict()["eval_specs"][0]
    assert spec["containment_threshold"] == 0.90
    assert spec["min_shingles"] == 25


def test_eval_sets_with_different_shinglings_are_indexed_separately():
    index = Decontaminator()
    index.add_eval_set(SENTENCE_SPEC)
    index.add_eval_item("roman-urdu-parl-test", "s:1", ROMAN_SENTENCE)
    index.add_eval_item("held-out", "d:1", URDU_ARTICLE)  # defaults to word shingles
    index.seal()
    shinglings = {row["shingle_unit"] for row in index.to_dict()["shinglings"]}
    assert shinglings == {"word", "char"}
    assert not index.check("doc:1", WIKI_CHROME_HEAD + URDU_ARTICLE).kept


def test_redeclaring_an_eval_set_with_a_different_shingling_is_an_error():
    index = Decontaminator()
    index.add_eval_set(EvalSetSpec(name="held-out", shingle_unit="word"))
    with pytest.raises(ValueError, match="already declared"):
        index.add_eval_set(EvalSetSpec(name="held-out", shingle_unit="char"))


# ---------------------------------------------------------------------------
# Order independence — stage 8 gets it for free, and the test says why
# ---------------------------------------------------------------------------


def test_a_verdict_does_not_depend_on_what_the_pass_has_already_seen():
    """The property stages 6 and 7 each pay a second corpus pass to obtain.

    A document's fate is a function of that document and the sealed eval index. Nothing about the
    read order, the seed or a resumption point can change it — so unlike stage 6, stage 8 needs no
    two-phase structure and no lowest-key survivor rule to be reconstructible from the manifest.
    """
    documents = [
        ("doc:1", WIKI_CHROME_HEAD + URDU_ARTICLE + WIKI_CHROME_TAIL),
        ("doc:2", URDU_UNRELATED),
        ("doc:3", URDU_ARTICLE),
    ]
    items = [("held-out", "eval:1", URDU_ARTICLE)]

    forward, _ = decontaminate(documents, items)
    backward, _ = decontaminate(list(reversed(documents)), items)
    assert {v.doc_id: v.kept for v in forward} == {v.doc_id: v.kept for v in backward}


def test_eval_items_added_in_any_order_give_the_same_verdicts():
    items = [
        ("held-out", "eval:1", URDU_ARTICLE),
        ("held-out", "eval:2", URDU_UNRELATED),
    ]
    forward, _ = decontaminate([("doc:1", URDU_ARTICLE)], items)
    backward, _ = decontaminate([("doc:1", URDU_ARTICLE)], list(reversed(items)))
    assert forward[0].kept == backward[0].kept is False


# ---------------------------------------------------------------------------
# Sealing — the failure this stage cannot detect after the fact
# ---------------------------------------------------------------------------


def test_checking_before_seal_is_an_error():
    index = Decontaminator()
    index.add_eval_item("held-out", "eval:1", URDU_ARTICLE)
    with pytest.raises(RuntimeError, match="seal"):
        index.check("doc:1", URDU_ARTICLE)


def test_adding_an_eval_item_after_seal_is_an_error():
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE))
    with pytest.raises(RuntimeError, match="seal"):
        index.add_eval_item("held-out", "eval:2", URDU_UNRELATED)


def test_seal_is_idempotent():
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE))
    index.seal()
    assert not index.check("doc:1", URDU_ARTICLE).kept


# ---------------------------------------------------------------------------
# Clean documents stay
# ---------------------------------------------------------------------------


def test_an_unrelated_document_is_kept():
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE))
    verdict = index.check("doc:1", URDU_UNRELATED)
    assert verdict.kept and verdict.reason == ""
    assert index.log.kept == 1 and index.log.removed == 0


def test_an_empty_document_is_kept():
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE))
    assert index.check("doc:1", "").kept


def test_a_shared_phrase_is_not_contamination():
    """Two Urdu articles about Pakistan share vocabulary. That is the language, not an overlap."""
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE))
    partial = "پاکستان جنوبی ایشیا کا ایک اہم ملک ہے۔ " + URDU_UNRELATED
    assert index.check("doc:1", partial).kept


# ---------------------------------------------------------------------------
# Accounting
# ---------------------------------------------------------------------------


def test_the_accounting_balances():
    documents = [
        ("doc:1", URDU_ARTICLE),
        ("doc:2", URDU_UNRELATED),
        ("doc:3", WIKI_CHROME_HEAD + URDU_ARTICLE + WIKI_CHROME_TAIL),
    ]
    _, log = decontaminate(documents, [("held-out", "eval:1", URDU_ARTICLE)])
    assert log.checked == 3
    assert log.kept + log.removed == log.checked
    assert log.removed == sum(log.removed_by_reason.values())
    assert log.chars_in == sum(len(text) for _, text in documents)
    assert log.chars_kept == len(URDU_UNRELATED)


def test_eval_coverage_reports_the_share_of_a_test_set_found_in_the_corpus():
    """The number §8.2 cares about, and it is not the number of documents removed.

    Removing 40 training documents is housekeeping. Learning that 40% of a *test set* sits in the
    training data is a statement about whether the metric computed on it means anything.
    """
    items = [
        ("held-out", "eval:1", URDU_ARTICLE),
        ("held-out", "eval:2", URDU_UNRELATED),
    ]
    # Two documents, both copies of eval:1 — one eval item compromised, two documents removed.
    documents = [("doc:1", URDU_ARTICLE), ("doc:2", WIKI_CHROME_HEAD + URDU_ARTICLE)]
    _, log = decontaminate(documents, items)
    coverage = log.eval_coverage()["held-out"]
    assert log.removed == 2
    assert coverage["items"] == 2
    assert coverage["items_found_in_corpus"] == 1
    assert coverage["share"] == 0.5


def test_every_eval_item_over_threshold_is_counted_not_just_the_strongest():
    """A regression: one training row can compromise several test items, and all of them count.

    Measured on real text — `roman-urdu-parl:train 58:6137` matches **nine** spelling variants of
    one test sentence. Recording only the highest-containment item under-reported `eval_coverage`,
    which is the number §8.2 actually cares about, by exactly the factor that matters most on the
    most contaminated rows.
    """
    stem = " ".join(f"word{i}" for i in range(120))
    index = Decontaminator()
    for n, tail in enumerate(("alpha", "beta", "gamma")):
        index.add_eval_item("held-out", f"eval:{n}", f"{stem} {tail}")
    index.seal()

    verdict = index.check("doc:1", stem)
    assert not verdict.kept
    coverage = index.log.eval_coverage()["held-out"]
    assert coverage["items_found_in_corpus"] == 3, "one document, three compromised test items"
    assert index.log.removed == 1, "but still one document removed"


def test_an_exact_match_does_not_hide_a_second_compromised_eval_item():
    """The exact half names the reason; it does not short-circuit the count.

    A document that *is* one test item may also *contain* another. Returning early would remove the
    document — right — while reporting only one test item as compromised, which is wrong in the one
    direction this stage cannot afford: silent under-reporting.
    """
    other = " ".join(f"word{i}" for i in range(120))
    document = f"{URDU_ARTICLE}\n{other}"

    index = _sealed(("held-out", "exact:1", document), ("held-out", "contained:1", other))
    verdict = index.check("doc:1", document)

    assert verdict.reason == "exact_document" and verdict.eval_id == "exact:1"
    assert index.log.eval_coverage()["held-out"]["items_found_in_corpus"] == 2
    assert index.log.removed == 1


def test_per_source_counters_track_removals():
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE))
    index.check("a:1", URDU_ARTICLE, source="urdu-wikipedia")
    index.check("b:1", URDU_UNRELATED, source="fineweb2-urd_Arab")
    assert index.log.by_source == {"urdu-wikipedia": 1, "fineweb2-urd_Arab": 1}
    assert index.log.removed_by_source == {"urdu-wikipedia": 1}


def test_the_log_is_json_serializable():
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE))
    index.check("doc:1", URDU_ARTICLE)
    json.dumps(index.to_dict())  # the manifest has to be able to hold this


# ---------------------------------------------------------------------------
# The sweep — session 6's lesson, one stage on
# ---------------------------------------------------------------------------


def test_the_sweep_is_exact_from_one_pass():
    """Re-deciding at another threshold is a filter over retained hits, not another corpus read."""
    eval_text = " ".join(f"word{i}" for i in range(100))
    three_quarters = " ".join(f"word{i}" for i in range(75)) + " " + URDU_UNRELATED

    index = _sealed(("held-out", "eval:1", eval_text))
    assert index.check("doc:1", three_quarters).kept, "0.73 contained, under the 0.80 threshold"

    rows = {row["threshold"]: row for row in index.sweep([0.5, 0.7, 0.9])}
    assert rows[0.5]["documents_removed"] == 1
    assert rows[0.7]["documents_removed"] == 1
    assert rows[0.9]["documents_removed"] == 0


def test_the_sweep_refuses_thresholds_it_did_not_measure():
    """A sweep below the retention floor would silently under-report rather than say it cannot."""
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE))
    index.check("doc:1", URDU_ARTICLE)
    row = index.sweep([0.1])[0]
    assert "note" in row and "retain_hits_above" in row["note"]


def test_hits_carry_both_scores():
    """They disagree, and the disagreement is the finding — so neither may be dropped."""
    index = _sealed(("held-out", "eval:1", URDU_ARTICLE))
    index.check("doc:1", WIKI_CHROME_HEAD + URDU_ARTICLE + WIKI_CHROME_TAIL)
    hit = index.hits()[0]
    assert hit.containment > hit.jaccard
    assert set(hit.to_dict()) >= {"containment", "jaccard", "intersection", "eval_shingles"}


def test_hits_are_ordered_by_strength_not_arrival():
    eval_a = " ".join(f"alpha{i}" for i in range(100))
    eval_b = " ".join(f"beta{i}" for i in range(100))
    index = _sealed(("held-out", "weak", eval_a), ("held-out", "strong", eval_b))
    index.check("doc:1", " ".join(f"alpha{i}" for i in range(70)) + " " + URDU_UNRELATED)
    index.check("doc:2", eval_b)
    assert index.hits()[0].eval_id == "strong"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_the_shipped_config_file_matches_the_code_defaults():
    """The same lock every other stage carries: the file and the dataclass cannot drift apart."""
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assert payload["decontamination_version"] == DECONTAMINATION_VERSION
    assert DecontaminationConfig.from_dict(payload) == DEFAULT


def test_config_round_trips_through_json(tmp_path):
    config = DecontaminationConfig(containment_threshold=0.7, retain_hits_above=0.3)
    path = tmp_path / "decontamination.json"
    config.to_json_file(path)
    assert DecontaminationConfig.from_json_file(path) == config
    assert "\r" not in path.read_bytes().decode("utf-8"), "CRLF would change the corpus checksum"


def test_config_fingerprint_changes_with_the_threshold():
    a = DecontaminationConfig()
    b = DecontaminationConfig(containment_threshold=0.7)
    assert a.fingerprint() != b.fingerprint()


def test_unknown_config_keys_are_refused():
    with pytest.raises(ValueError, match="unknown decontamination config keys"):
        DecontaminationConfig.from_dict({**DEFAULT.to_dict(), "containmentThreshold": 0.9})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"containment_threshold": 0.0},
        {"containment_threshold": 1.5},
        {"retain_hits_above": 0.9},  # above containment_threshold
        {"min_shingles": 0},
        {"min_line_chars": -1},
        {"max_index_shingles": 0},
    ],
)
def test_invalid_configs_are_refused(kwargs):
    with pytest.raises(ValueError):
        DecontaminationConfig(**kwargs)


def test_an_eval_set_needs_a_name():
    with pytest.raises(ValueError, match="needs a name"):
        EvalSetSpec(name="")


def test_an_eval_set_refuses_an_unknown_shingle_unit():
    with pytest.raises(ValueError, match="shingle_unit"):
        EvalSetSpec(name="held-out", shingle_unit="sentence")


def test_the_index_ceiling_fails_loudly():
    """It exists so that pointing stage 8 at a corpus by mistake raises instead of swapping."""
    tiny = DecontaminationConfig(max_index_shingles=4)
    index = Decontaminator(tiny)
    with pytest.raises(MemoryError, match="max_index_shingles"):
        index.add_eval_item("held-out", "eval:1", URDU_ARTICLE)


def test_the_hit_dataclass_rounds_for_the_report():
    hit = ContaminationHit(
        eval_set="held-out",
        eval_id="e",
        doc_id="d",
        containment=0.123456789,
        jaccard=0.987654321,
        intersection=10,
        eval_shingles=20,
        doc_shingles=30,
    )
    assert hit.to_dict()["containment"] == 0.1235
    assert hit.to_dict()["jaccard"] == 0.9877


def test_threshold_for_is_per_eval_set_not_global():
    """The removals list has to agree with the counters beside it.

    `for_sentences()` raises the cut to 0.90 because the 0.80-0.90 band on a sentence set is
    templates. A removals list written at the global 0.80 deletes training documents on evidence
    this stage already judged to be nothing, and no counter in the report disagrees with it —
    measured on the freeze at 432,249 ids against a reported 349,823.
    """
    index = Decontaminator(DecontaminationConfig(containment_threshold=0.80))
    index.add_eval_set(EvalSetSpec(name="documents"))
    index.add_eval_set(EvalSetSpec(name="sentences").for_sentences())

    assert index.threshold_for("documents") == 0.80
    assert index.threshold_for("sentences") == 0.90
    # An undeclared set falls back rather than raising: add_eval_item declares one on first use.
    assert index.threshold_for("never-declared") == 0.80


def test_a_sentence_set_hit_between_the_two_cuts_is_not_a_removal():
    """The 82,426-document gap on the freeze, as one case."""
    index = Decontaminator(DecontaminationConfig(containment_threshold=0.80))
    index.add_eval_set(EvalSetSpec(name="sentences").for_sentences())
    assert 0.85 >= index.config.containment_threshold
    assert 0.85 < index.threshold_for("sentences")


def test_a_document_is_not_contaminated_by_being_itself():
    """§8.2's held-out sets are carved out of the corpus, so each arrives twice at the freeze.

    Without the guard the document matches itself at containment 1.0 and is removed, which
    deletes the evaluation set. Measured on the freeze: 100% of heldout_urdu (5,400) and
    heldout_code_switched (384) went this way, and stage 10 wrote a corpus with no urdu
    validation or test stream.
    """
    index = Decontaminator()
    index.add_eval_item("held-out", "corpus:7", URDU_ARTICLE)
    index.seal()

    assert index.check("corpus:7", URDU_ARTICLE).kept
    # A *different* document holding the same text is still contamination.
    assert not index.check("corpus:8", URDU_ARTICLE).kept
