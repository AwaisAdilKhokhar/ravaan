"""Engineering invariants for MinHash near-deduplication (PRD §8.1 — CI, never a results table).

Stage 7 deletes documents on an *estimate*, which is the thing stage 6 never did, so the tests
split into two kinds that stage 6 did not need to distinguish.

* **Is the estimator right?** ``test_the_estimate_tracks_exact_jaccard`` and its short-document
  companion compare the sketch against exact set Jaccard on real Urdu. One-permutation hashing with
  densification is a published construction but this is a hand-rolled implementation of it, and an
  estimator that is quietly biased by 0.05 would move the threshold decision without failing a
  single behavioural test.
* **Is the decision right given the estimate?** Order independence, the survivor rule, eligibility,
  and the accounting — the same shapes as `test_dedup.py`, because stage 7 inherits stage 6's
  doctrine that a released corpus must be reconstructible from code and manifest alone.

Two of these are **acceptance tests written before the code, from measurements taken in session
8**, which is the only time such a thing is credible:

* **Finding I** — the Wikipedia geo-stub farm tops out at word-shingle Jaccard 0.677 (n=2) and
  0.423 (n=5). Stage 7 at 0.8 must *not* cluster it. That is the expected result, and the test
  exists so a later "improvement" to the threshold cannot quietly turn it into a bug.
* **Finding L** — Urdu Wikipedia articles also live inside FineWeb2 as crawled HTML, same content
  wrapped in navigation chrome, never byte-identical. That population is what stage 8 needs stage 7
  to have found, and ``test_containment_sees_what_jaccard_cannot`` is the shape of it.

Measured behaviour on real text lives in `reports/probe_minhash_*.json`. These are the rules.
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

import pytest

from ravaan.data.dedup import canonical, document_key
from ravaan.data.minhash import (
    MINHASH_VERSION,
    MinHashConfig,
    MinHashDeduplicator,
    containment_from_jaccard,
    jaccard,
    near_deduplicate,
    shingle_hashes,
    shingles,
)

DEFAULT = MinHashConfig()
CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "data" / "minhash.json"

URDU_ARTICLE = (
    "پاکستان جنوبی ایشیا کا ایک اہم ملک ہے جس کی سرحدیں بھارت، افغانستان، ایران اور چین سے ملتی "
    "ہیں۔ اس کا دارالحکومت اسلام آباد ہے جبکہ کراچی سب سے بڑا شہر اور ملک کا معاشی مرکز سمجھا "
    "جاتا ہے۔ ملک کی آبادی بائیس کروڑ سے زیادہ ہے اور یہاں کئی زبانیں بولی جاتی ہیں جن میں اردو "
    "قومی زبان کی حیثیت رکھتی ہے۔ پاکستان کی معیشت کا انحصار زراعت، صنعت اور خدمات کے شعبوں پر ہے "
    "اور حالیہ برسوں میں اطلاعاتی ٹیکنالوجی کا شعبہ بھی تیزی سے ترقی کر رہا ہے۔ ملک کے شمال میں "
    "دنیا کے بلند ترین پہاڑی سلسلے واقع ہیں جو سیاحوں کی توجہ کا مرکز بنے رہتے ہیں۔"
)

URDU_OTHER = (
    "اردو زبان کی ترقی میں شاعروں اور ادیبوں نے نمایاں کردار ادا کیا ہے۔ غالب، اقبال اور فیض کی "
    "شاعری آج بھی برصغیر کے قارئین میں یکساں مقبول ہے اور نئی نسل اسے شوق سے پڑھتی ہے۔ اردو نثر "
    "میں ناول اور افسانے کی روایت انیسویں صدی کے آخر میں مضبوط ہوئی اور بیسویں صدی میں اس نے "
    "عالمی ادب کے ساتھ قدم ملا کر چلنا شروع کیا۔ آج اردو دنیا بھر میں کروڑوں افراد کی زبان ہے۔"
)

# Wikipedia's navigation chrome, in the shape FineWeb2's HTML-to-text extraction carries it —
# Finding L's mechanism. The article is unchanged inside it; everything else is the rendering.
WIKI_CHROME_HEAD = (
    "آزاد دائرۃ المعارف، ویکیپیڈیا سے مندرجات کی طرف جائیں تلاش کریں اہم صفحہ حالیہ تبدیلیاں "
    "کوئی بھی صفحہ برائے مہربانی لاگ ان کریں کھاتہ بنائیں ذاتی اوزار بحث تعاون تبادلۂ خیال "
    "مضمون تبادلہ خیال پڑھیں ترمیم کریں تاریخچہ دیکھیں مزید تلاش"
)
WIKI_CHROME_FOOT = (
    "زمرہ جات جنوبی ایشیا کے ممالک اسلامی جمہوریہ مخفی زمرہ جات مضامین جن میں حوالہ جات کی کمی ہے "
    "یہ صفحہ آخری بار ترمیم ہوا اجازت نامہ تحریری مواد اجازت نامے کے تحت دستیاب ہے رازداری کی "
    "پالیسی ویکیپیڈیا کے بارے میں دستبرداری موبائل نظارہ ڈویلپرز شماریات کوکی بیان"
)


def _words(text: str) -> list[str]:
    return canonical(text).split(" ")


def _variant(text: str, replaced: float, seed: int) -> str:
    """The same document with a share of its words swapped — a controlled near-duplicate."""
    words = _words(text)
    rng = random.Random(seed)
    keep = int(len(words) * (1.0 - replaced))
    filler = [f"لفظ{rng.randrange(9999)}" for _ in range(len(words) - keep)]
    return " ".join(words[:keep] + filler)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_shipped_config_matches_code_defaults():
    """The committed config is the defaults, or the manifest describes a pass nobody ran."""
    shipped = MinHashConfig.from_json_file(CONFIG_PATH)
    assert shipped == DEFAULT
    assert json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["minhash_version"] == MINHASH_VERSION


def test_config_round_trips_through_json(tmp_path):
    config = MinHashConfig(num_bins=64, bands=8, rows=8, similarity_threshold=0.7)
    path = tmp_path / "minhash.json"
    config.to_json_file(path)
    assert MinHashConfig.from_json_file(path) == config
    assert MinHashConfig.from_json_file(path).fingerprint() == config.fingerprint()


def test_fingerprint_changes_with_any_setting():
    assert DEFAULT.fingerprint() != MinHashConfig(similarity_threshold=0.75).fingerprint()
    assert DEFAULT.fingerprint() != MinHashConfig(shingle_size=3).fingerprint()
    # The seed fixes the densification probe order, so two seeds are two estimators. A frozen
    # corpus has to name the one that produced it.
    assert DEFAULT.fingerprint() != MinHashConfig(seed=1).fingerprint()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"num_bins": 4},
        {"bands": 5},  # 5 * 8 != 128
        {"rows": 0},
        {"shingle_unit": "sentence"},
        {"shingle_size": 0},
        {"min_shingles": 0},
        {"similarity_threshold": 0.0},
        {"similarity_threshold": 1.5},
        # Retaining fewer pairs than the threshold uses makes sweep() silently incomplete.
        {"retain_pairs_above": 0.9},
        {"max_index_entries": 0},
    ],
)
def test_invalid_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        MinHashConfig(**kwargs)


def test_unknown_config_keys_are_rejected():
    with pytest.raises(ValueError, match="unknown minhash config keys"):
        MinHashConfig.from_dict({"num_bins": 128, "hash_bits": 64})


def test_banding_casts_a_wide_net_and_lets_verification_do_the_cutting():
    """Banding is the recall stage; verification is the precision stage.

    If the S-curve's inflection ever rises above the similarity threshold, the pass silently stops
    generating candidates for pairs it is supposed to remove, and the only symptom is a duplicate
    rate that looks pleasingly low.

    The shipped (32, 4) is deliberately far wider than a textbook 0.8 configuration, and *not*
    because it removes more: measured on the complete Urdu Wikipedia dump at threshold 0.80,
    (16, 8) and (32, 4) both find 118 clusters and remove 178 and 179 documents respectively. It
    is wider so the **sweep** is honest. (16, 8) has 6% recall at J = 0.5, so every threshold row
    below ~0.7 would report the bands rather than the corpus, and choosing a threshold from that
    is choosing it from an artefact. Verification against the full signature is exact and costs
    microseconds, so candidates that fail are cheap and candidates never generated cannot be
    recovered. This test pins the direction of the trade so a later tightening has to argue with
    the measurement.
    """
    assert DEFAULT.band_threshold < DEFAULT.similarity_threshold
    assert DEFAULT.candidate_probability(DEFAULT.similarity_threshold) > 0.99
    # Wide enough to see the asymmetric wiki-against-crawled-page region Finding L lives in...
    assert DEFAULT.candidate_probability(0.5) > 0.8
    # ...and still not so wide that unrelated documents flood verification.
    assert DEFAULT.candidate_probability(0.1) < 0.01


# ---------------------------------------------------------------------------
# Shingling — the unit of comparison
# ---------------------------------------------------------------------------


def test_shingles_come_from_the_same_canonical_form_stage_6_hashes():
    """Two stages that disagree about what a document is will disagree about duplicates.

    Stage 6 collapses whitespace and case-folds before hashing. If stage 7 shingled raw text it
    would call two documents different over a line break stage 6 had already ruled irrelevant.
    """
    wrapped = URDU_ARTICLE.replace("۔ ", "۔\n")
    assert shingle_hashes(wrapped) == shingle_hashes(URDU_ARTICLE)
    mixed_case = "Aik Larka School Gaya Aur"
    assert shingle_hashes(mixed_case) == shingle_hashes(mixed_case.lower())


def test_shingles_are_a_set_so_a_repeated_phrase_counts_once():
    """Jaccard is defined over sets. Urdu news copy restating its own headline (session 6's
    finding on Gopher repetition) must not inflate its own similarity to everything else."""
    phrase = "کے مطابق ذرائع نے بتایا"
    once = shingle_hashes(phrase, size=3)
    twice = shingle_hashes(f"{phrase} {phrase}", size=3)
    assert once <= twice
    assert len(twice) < 2 * len(once)


def test_char_shingles_exist_for_sources_with_no_words_to_spare():
    """Roman-Urdu-Parl rows are ~10-word sentences: six word-5-grams and nothing to estimate."""
    sentence = "aik larka school gaya"
    assert len(list(shingles(sentence, size=5, unit="word"))) == 0
    assert len(list(shingles(sentence, size=5, unit="char"))) > 15


def test_a_document_shorter_than_the_shingle_size_yields_nothing_rather_than_raising():
    assert list(shingles("ایک دو", size=5)) == []
    assert shingle_hashes("ایک دو") == set()


# ---------------------------------------------------------------------------
# The estimator — is the sketch actually estimating Jaccard?
# ---------------------------------------------------------------------------


def _estimate(index: MinHashDeduplicator, left: str, right: str) -> float:
    from ravaan.data.minhash import _agreement

    sketches = [index._sketch(shingle_hashes(text)) for text in (left, right)]
    return _agreement(*sketches) / index.config.num_bins


# The vocabulary the bias trials draw their documents from. Real Urdu words, so the shingles carry
# the script's actual byte distribution, but *drawn afresh per trial* — see the note in
# ``_bias_over_independent_pairs`` on why a fixed base document cannot measure bias.
_VOCABULARY = sorted(set(_words(URDU_ARTICLE) + _words(URDU_OTHER)))


def _bias_over_independent_pairs(words_per_document: int, overlap: float, trials: int) -> float:
    """Mean (estimate − exact) over ``trials`` *independent* document pairs.

    The independence is the whole point and it is easy to get wrong: MinHash's randomness lives in
    the hash function, which is fixed here on purpose (a frozen corpus cannot have a per-run
    estimator). So for one fixed pair of documents the estimate is a *deterministic* number, and
    averaging it over variants of a single base document averages correlated errors that do not
    cancel — which reads exactly like a biased estimator and is not one. A fresh base document per
    trial is what makes the mean converge on the bias rather than on one document's luck.
    """
    index = MinHashDeduplicator()
    errors = []
    for trial in range(trials):
        rng = random.Random(9_000 + trial)
        base = [rng.choice(_VOCABULARY) for _ in range(words_per_document)]
        keep = int(words_per_document * overlap)
        variant = base[:keep] + [
            f"لفظ{rng.randrange(99_999)}" for _ in range(words_per_document - keep)
        ]
        left, right = shingle_hashes(" ".join(base)), shingle_hashes(" ".join(variant))
        if min(len(left), len(right)) < DEFAULT.min_shingles:
            continue
        errors.append(
            _estimate(index, " ".join(base), " ".join(variant)) - jaccard(left, right)
        )
    assert len(errors) > trials // 2
    return statistics.mean(errors)


@pytest.mark.parametrize("overlap", [0.95, 0.9, 0.8, 0.65, 0.5])
def test_the_estimate_tracks_exact_jaccard(overlap):
    """The whole stage rests on this, and it is a hand-rolled estimator.

    One-permutation hashing with densification is unbiased by construction, but a bug in the
    densification probe — reading fill state written by densification itself, say — biases it
    without changing any behaviour a functional test would notice. So: measure it, against exact
    set Jaccard. The tolerance is roughly four standard errors of the mean at K=128
    (sqrt(J(1-J)/K) ≈ 0.035 at J = 0.8, over 80 trials), which is loose enough not to flake and
    far tighter than any bias that would move a threshold decision.
    """
    bias = _bias_over_independent_pairs(200, overlap, trials=80)
    assert abs(bias) < 0.015, f"biased by {bias:+.4f}"


def test_the_estimate_survives_documents_with_fewer_shingles_than_bins():
    """The regime where densification does most of the work — and where a wrong probe order shows.

    A 400-character document (stage 5's floor) has ~79 word-5-grams against 128 bins, so half the
    signature is densified for a large share of the corpus, and a 30-word document leaves five
    bins in six empty. Measured, the estimator stays unbiased there and only the variance grows —
    which is what makes ``min_shingles`` 8 rather than 128.
    """
    assert abs(_bias_over_independent_pairs(30, 0.85, trials=120)) < 0.03
    assert abs(_bias_over_independent_pairs(14, 0.85, trials=120)) < 0.04


def test_densification_fills_empty_bins_at_the_jaccard_rate():
    """The subtle half of the estimator, pinned directly rather than through its average.

    A bin empty in *both* documents is filled by copying from elsewhere in the signature, and the
    copy has to agree between two documents exactly as often as they are similar — otherwise every
    short document is quietly reported as less similar than it is, and the threshold gets tuned to
    compensate for a bug. Measured here on documents that leave ~40% of bins jointly empty.
    """
    from array import array as _array

    from ravaan.data.minhash import _EMPTY, _MASK32

    index = MinHashDeduplicator()
    bins = DEFAULT.num_bins
    jointly_empty = matches = 0
    exact_total = pairs = 0

    for trial in range(150):
        rng = random.Random(4_000 + trial)
        base = [rng.choice(_VOCABULARY) for _ in range(100)]
        variant = base[:85] + [f"لفظ{rng.randrange(99_999)}" for _ in range(15)]
        left, right = shingle_hashes(" ".join(base)), shingle_hashes(" ".join(variant))
        exact_total += jaccard(left, right)
        pairs += 1

        def occupancy(hashes: set[int]) -> list[bool]:
            filled = [False] * bins
            for value in hashes:
                filled[value % bins] = True
            return filled

        left_filled, right_filled = occupancy(left), occupancy(right)
        left_sig, right_sig = _array("I"), _array("I")
        left_sig.frombytes(index._sketch(left))
        right_sig.frombytes(index._sketch(right))
        for position in range(bins):
            if not left_filled[position] and not right_filled[position]:
                jointly_empty += 1
                matches += left_sig[position] == right_sig[position]

    assert jointly_empty > 3_000, "the trial documents must actually leave bins empty"
    assert _EMPTY > _MASK32  # the sentinel can never be mistaken for a real value
    assert abs(matches / jointly_empty - exact_total / pairs) < 0.02


def test_densification_is_deterministic_and_seed_dependent():
    """Same document, same signature — or two runs cluster the same corpus differently."""
    text = " ".join(_words(URDU_ARTICLE)[:40])
    hashes = shingle_hashes(text)
    first = MinHashDeduplicator()
    second = MinHashDeduplicator()
    assert first._sketch(hashes) == second._sketch(hashes)
    other_seed = MinHashDeduplicator(MinHashConfig(seed=1))
    assert other_seed._sketch(hashes) != first._sketch(hashes)


def test_identical_documents_agree_on_every_bin():
    index = MinHashDeduplicator()
    assert _estimate(index, URDU_ARTICLE, URDU_ARTICLE) == 1.0


def test_unrelated_documents_do_not_agree():
    index = MinHashDeduplicator()
    assert _estimate(index, URDU_ARTICLE, URDU_OTHER) < 0.1


# ---------------------------------------------------------------------------
# Containment — Finding L's instrument
# ---------------------------------------------------------------------------


def test_containment_sees_what_jaccard_cannot():
    """Finding L, as a test: a Wikipedia article inside its own crawled-and-rendered copy.

    The article is present verbatim; the chrome is in the union but not the intersection, so
    Jaccard is dragged well below the 0.8 threshold while containment stays near 1. This is the
    population §6.3.8's fuzzy matching has to catch, and it is the reason stage 7 reports both
    numbers rather than the one it removes on.
    """
    rendered = f"{WIKI_CHROME_HEAD} {URDU_ARTICLE} {WIKI_CHROME_FOOT}"
    article_shingles = shingle_hashes(URDU_ARTICLE)
    rendered_shingles = shingle_hashes(rendered)

    exact = jaccard(article_shingles, rendered_shingles)
    contained = containment_from_jaccard(
        exact, len(article_shingles), len(rendered_shingles)
    )
    assert exact < 0.8, "if this ever passes 0.8, Jaccard alone would have sufficed"
    assert contained > 0.95, "the article is present verbatim"


def test_containment_is_derived_from_the_sketch_not_from_the_text():
    """It has to be free, or it does not get measured on a full pass."""
    left, right = shingle_hashes(URDU_ARTICLE), shingle_hashes(f"{URDU_ARTICLE} {WIKI_CHROME_FOOT}")
    exact = jaccard(left, right)
    assert containment_from_jaccard(exact, len(left), len(right)) == pytest.approx(
        len(left & right) / min(len(left), len(right)), abs=1e-9
    )


def test_containment_clamps_at_one():
    assert containment_from_jaccard(1.0, 10, 10) == 1.0
    assert containment_from_jaccard(0.0, 0, 0) == 0.0


# ---------------------------------------------------------------------------
# Finding I — the acceptance test written before the code
# ---------------------------------------------------------------------------

_STUB = (
    "{name} ریاستہائے متحدہ امریکہ کی ریاست {state} کے {county} کاؤنٹی میں واقع ایک شہر ہے۔ "
    "دو ہزار دس کی مردم شماری کے مطابق اس شہر کی آبادی {population} افراد پر مشتمل تھی۔ "
    "شہر کا رقبہ {area} مربع کلومیٹر ہے جس میں سے {land} مربع کلومیٹر خشکی اور باقی پانی پر "
    "مشتمل ہے۔ یہ شہر سطح سمندر سے {elevation} میٹر کی بلندی پر واقع ہے۔ مزید دیکھیے حوالہ جات "
    "بیرونی روابط زمرہ جات {state} کے شہر {county} کاؤنٹی کے شہر"
)


def _geo_stubs(count: int = 24) -> list[tuple[str, str]]:
    rng = random.Random(11)
    states = ["الاباما", "ٹیکساس", "اوہائیو", "کینساس", "مشی گن", "اوریگون"]
    return [
        (
            f"urdu-wikipedia:stub{i}",
            _STUB.format(
                name=f"شہر{i}",
                state=rng.choice(states),
                county=f"کاؤنٹی{rng.randrange(400)}",
                population=rng.randrange(500, 90000),
                area=round(rng.uniform(2, 90), 2),
                land=round(rng.uniform(1, 80), 2),
                elevation=rng.randrange(5, 2000),
            ),
        )
        for i in range(count)
    ]


def test_the_geo_stub_farm_is_not_clustered_at_the_shipped_threshold():
    """Finding I, measured before this module existed: no stub pair reaches Jaccard 0.7 at any n.

    Session 7 booked two of stage 5's four surviving false accepts as "the stub farm, which is
    stage 7's". Session 8 measured that prediction and it is wrong — the variable parts (place
    name, county, population, area, elevation) are a large share of a 92-word document, so every
    shingle spanning a changed word is destroyed. This test pins the *expected* result so a later
    threshold change cannot turn a known negative into a silent surprise.
    """
    verdicts, index = near_deduplicate(_geo_stubs())
    assert all(verdict.kept for verdict in verdicts)
    assert index.log.clusters == 0
    assert index.log.duplicate_documents == 0


def test_the_geo_stubs_do_however_look_similar_to_a_looser_threshold():
    """The other half of Finding I: they are *not* unrelated, they are under the cut.

    Without this the test above would also pass if shingling were broken and every document looked
    unique. The stubs share their template, so they must show up as measured pairs well above zero
    and still land beneath 0.8.
    """
    _, index = near_deduplicate(_geo_stubs(), MinHashConfig(retain_pairs_above=0.1))
    similarities = [example.similarity for example in index.pair_examples()]
    assert similarities, "template-sharing stubs must at least become candidates"
    assert max(similarities) < DEFAULT.similarity_threshold


# ---------------------------------------------------------------------------
# Order independence — stage 6's headline property, inherited
# ---------------------------------------------------------------------------


def _near_duplicate_corpus() -> list[tuple[str, str]]:
    records = [("base-0", URDU_ARTICLE)]
    records += [(f"base-{i}", _variant(URDU_ARTICLE, 0.03, seed=i)) for i in range(1, 4)]
    records += [("other-0", URDU_OTHER)]
    records += [(f"other-{i}", _variant(URDU_OTHER, 0.02, seed=100 + i)) for i in range(1, 3)]
    records += [(f"solo-{i}", _variant(URDU_ARTICLE, 0.9, seed=200 + i)) for i in range(4)]
    return records


def test_survivors_are_identical_under_every_read_order():
    """PRD §6.3 releases code, manifest and checksums but no text. If this fails, a frozen corpus
    cannot be reconstructed from what was released — the same argument stage 6 makes, and the
    reason the bucket representative is the lowest-keyed member rather than the first one read."""
    records = _near_duplicate_corpus()
    baseline = None
    for seed in range(12):
        shuffled = records[:]
        random.Random(seed).shuffle(shuffled)
        verdicts, _ = near_deduplicate(shuffled)
        kept = frozenset(verdict.doc_id for verdict in verdicts if verdict.kept)
        if baseline is None:
            baseline = kept
        assert kept == baseline, f"seed {seed} produced a different corpus"
    assert baseline is not None


def test_the_survivor_is_the_lowest_key_member_of_its_cluster():
    """And it is stage 6's key function, imported rather than reimplemented — two dedup stages that
    disagreed about which copy is canonical would produce a corpus neither of them describes."""
    records = [(f"copy-{i}", _variant(URDU_ARTICLE, 0.02, seed=i)) for i in range(6)]
    verdicts, index = near_deduplicate(records)
    kept = [verdict.doc_id for verdict in verdicts if verdict.kept]
    assert len(kept) == 1, "all six are near-duplicates of each other"
    assert kept[0] == min((doc_id for doc_id, _ in records), key=document_key)
    assert index.log.largest_cluster == 6


# ---------------------------------------------------------------------------
# Eligibility — stage 7 must not delete what it cannot measure
# ---------------------------------------------------------------------------


def test_documents_below_min_shingles_are_kept_and_counted_not_compared():
    records = [("short-a", "ایک دو تین چار"), ("short-b", "ایک دو تین چار"), ("long", URDU_ARTICLE)]
    verdicts, index = near_deduplicate(records)
    assert all(verdict.kept for verdict in verdicts)
    assert index.log.skipped_short == 2
    assert index.log.eligible == 1
    assert {v.reason for v in verdicts if v.doc_id.startswith("short")} == {"too_few_shingles"}


def test_a_skipped_document_is_still_in_the_character_accounting():
    """It survives the stage, so it is part of what the stage kept, or the manifest under-counts."""
    _, index = near_deduplicate([("short", "ایک دو تین"), ("long", URDU_ARTICLE)])
    assert index.log.chars_kept == index.log.chars_in
    assert index.log.documents_kept == 2


# ---------------------------------------------------------------------------
# Accounting
# ---------------------------------------------------------------------------


def test_the_log_balances():
    verdicts, index = near_deduplicate(_near_duplicate_corpus())
    log = index.log
    removed = sum(1 for verdict in verdicts if not verdict.kept)
    assert log.indexed == log.documents_kept + removed
    assert log.duplicate_documents == removed
    assert log.eligible + log.skipped_short == log.indexed
    assert log.chars_kept <= log.chars_in
    assert log.verified_pairs <= log.candidate_pairs


def test_cross_source_clusters_are_reported_separately():
    """Finding L's number, when the run is a joint one.

    §6.1's budget and stage 8 want different halves of it: a source's removals are internal plus
    cross-source, and the two mean different things.
    """
    records = [
        ("urdu-wikipedia:1", URDU_ARTICLE, "urdu-wikipedia"),
        ("fineweb2-urd_Arab:1", _variant(URDU_ARTICLE, 0.02, seed=5), "fineweb2-urd_Arab"),
        ("urdu-wikipedia:2", URDU_OTHER, "urdu-wikipedia"),
    ]
    _, index = near_deduplicate(records)
    assert index.log.cross_source_clusters == 1
    assert index.log.cross_source_pairs == {"fineweb2-urd_Arab|urdu-wikipedia": 1}
    removed_cross = index.log.removed_cross_source_by_source
    assert sum(removed_cross.values()) == 1


def test_to_dict_is_json_serializable_and_carries_the_fingerprint():
    _, index = near_deduplicate(_near_duplicate_corpus())
    payload = index.to_dict()
    assert payload["config_fingerprint"] == DEFAULT.fingerprint()
    assert payload["minhash_version"] == MINHASH_VERSION
    json.dumps(payload, ensure_ascii=False)


def test_top_clusters_are_ordered_largest_first_and_name_their_survivor():
    records = [(f"big-{i}", _variant(URDU_ARTICLE, 0.02, seed=i)) for i in range(5)]
    records += [(f"small-{i}", _variant(URDU_OTHER, 0.02, seed=50 + i)) for i in range(2)]
    _, index = near_deduplicate(records)
    top = index.top_clusters()
    assert [cluster["size"] for cluster in top] == [5, 2]
    assert top[0]["kept"].startswith("big-")
    assert all(cluster["kept"] not in cluster["duplicates"] for cluster in top)


# ---------------------------------------------------------------------------
# The threshold sweep — deciding on measured pairs rather than on an inherited number
# ---------------------------------------------------------------------------


def test_sweep_reproduces_the_shipped_threshold_exactly():
    """A sweep entry at the configured threshold must equal what the pass actually did, or the
    sweep is a different instrument than the one the decision will be made with."""
    _, index = near_deduplicate(_near_duplicate_corpus())
    at_threshold = index.sweep([DEFAULT.similarity_threshold])[0]
    assert at_threshold["duplicate_documents"] == index.log.duplicate_documents
    assert at_threshold["clusters"] == index.log.clusters
    assert at_threshold["largest_cluster"] == index.log.largest_cluster


def test_sweep_is_monotone_in_the_threshold():
    _, index = near_deduplicate(_near_duplicate_corpus())
    rows = index.sweep([0.5, 0.6, 0.7, 0.8, 0.9])
    removals = [row["duplicate_documents"] for row in rows]
    assert removals == sorted(removals, reverse=True)


def test_sweep_refuses_a_threshold_whose_pairs_were_not_kept():
    """Silently answering from an incomplete pair list is how a threshold gets chosen on evidence
    that was thrown away during the pass that measured it."""
    _, index = near_deduplicate(_near_duplicate_corpus())
    with pytest.raises(ValueError, match="retain_pairs_above"):
        index.sweep([0.2])


def test_pair_examples_do_not_depend_on_read_order():
    """Session 6 learned this on stage 5's rejections, session 8 again on stage 6's snippets."""
    records = _near_duplicate_corpus()
    seen = []
    for seed in range(4):
        shuffled = records[:]
        random.Random(seed).shuffle(shuffled)
        _, index = near_deduplicate(shuffled)
        seen.append({(min(e.left, e.right), max(e.left, e.right)) for e in index.pair_examples()})
    assert all(sample == seen[0] for sample in seen)


# ---------------------------------------------------------------------------
# Degenerate input and misuse
# ---------------------------------------------------------------------------


def test_indexing_the_same_id_twice_is_an_error():
    """Stage 7 holds one sketch per document, so a repeated id is the reader emitting a document
    twice or under two identities — either way the cluster sizes below would be fiction."""
    index = MinHashDeduplicator()
    index.index("a", URDU_ARTICLE)
    with pytest.raises(ValueError, match="indexed twice"):
        index.index("a", URDU_OTHER)


def test_asking_about_an_unindexed_document_is_an_error_not_a_keep():
    index = MinHashDeduplicator()
    index.index("a", URDU_ARTICLE)
    with pytest.raises(KeyError, match="was not indexed"):
        index.verdict("b")


def test_indexing_after_build_is_refused():
    index = MinHashDeduplicator()
    index.index("a", URDU_ARTICLE)
    index.build()
    with pytest.raises(RuntimeError, match="build\\(\\) has already run"):
        index.index("b", URDU_OTHER)


def test_index_ceiling_raises_rather_than_swaps():
    index = MinHashDeduplicator(MinHashConfig(max_index_entries=2))
    index.index("a", URDU_ARTICLE)
    index.index("b", URDU_OTHER)
    with pytest.raises(MemoryError, match="max_index_entries"):
        index.index("c", URDU_ARTICLE)


def test_an_empty_corpus_builds_and_reports_nothing():
    index = MinHashDeduplicator()
    index.build()
    payload = index.to_dict()
    assert payload["indexed"] == 0
    assert payload["clusters"] == 0
    assert payload["keep_rate"] == 0.0


def test_empty_documents_are_skipped_rather_than_collapsed():
    """Stage 6 puts every empty document in one group. Stage 7 must not.

    With no shingles there is nothing to estimate, and a cluster of everything short would be the
    loudest possible false positive.
    """
    verdicts, index = near_deduplicate([("a", ""), ("b", "   "), ("c", "\n\n")])
    assert all(verdict.kept for verdict in verdicts)
    assert index.log.skipped_short == 3


# --- drop(): the single-pass driver's half ----------------------------------
# Stage 6 cannot decide until it has seen the corpus, so stage 7 used to sketch during stage 6's
# *second* pass — paying stages 2-5 twice, which is ~90% of the cost. `drop` lets a driver sketch
# everything in phase 1 and un-index stage 6's removals afterwards. The property that makes it safe
# is that dropping happens before banding, so a dropped document is never compared to anything.


def _sketch_all(texts: dict[str, str], **kwargs) -> MinHashDeduplicator:
    index = MinHashDeduplicator(MinHashConfig(**kwargs) if kwargs else None)
    for doc_id, text in texts.items():
        index.index(doc_id, text, source="test")
    return index


def _corpus() -> dict[str, str]:
    """Three near-duplicate families, one singleton, and exact copies of two of them."""
    base = {
        f"a{i}": "the quick brown fox jumps over the lazy dog in the park " * 3 + f"tail {i}"
        for i in range(4)
    }
    base.update(
        {f"b{i}": "a wholly different document about ships and harbours and salt " * 3 + f"end {i}"
         for i in range(3)}
    )
    base["solo"] = "nothing here resembles anything else in this small corpus whatsoever " * 3
    # Exact duplicates, which is what stage 6 would remove.
    base["a0copy"] = base["a0"]
    base["solocopy"] = base["solo"]
    return base


def test_dropping_before_build_equals_never_indexing() -> None:
    """The equivalence the single-pass driver rests on, asserted rather than argued.

    Sketch everything and drop the exact duplicates, against sketching only the survivors: the same
    clusters, the same survivors, the same counters. True by construction — `_band` and `_cluster`
    both iterate `_eligible`, which `drop` has already left — and this is the test that keeps it so.
    """
    corpus = _corpus()
    removed = ["a0copy", "solocopy"]
    survivors = {k: v for k, v in corpus.items() if k not in removed}

    one_pass = _sketch_all(corpus)
    one_pass.drop(removed)
    one_pass.build()

    two_pass = _sketch_all(survivors)
    two_pass.build()

    assert one_pass.removed_ids() == two_pass.removed_ids()
    assert one_pass.log.indexed == two_pass.log.indexed
    assert one_pass.log.eligible == two_pass.log.eligible
    assert one_pass.log.chars_in == two_pass.log.chars_in
    assert one_pass.log.clusters == two_pass.log.clusters
    assert one_pass.log.documents_kept == two_pass.log.documents_kept
    assert one_pass.log.chars_kept == two_pass.log.chars_kept
    assert one_pass.log.largest_cluster == two_pass.log.largest_cluster
    assert one_pass.log.by_source == two_pass.log.by_source
    assert one_pass.log.kept_by_source == two_pass.log.kept_by_source
    assert one_pass.log.shingles_total == two_pass.log.shingles_total


def test_a_dropped_document_is_not_reported_as_kept() -> None:
    """`kept=True` would be a true statement about stage 7 and a false one about the corpus."""
    index = _sketch_all(_corpus())
    index.drop(["a0copy"])
    index.build()

    verdict = index.verdict("a0copy")
    assert not verdict.kept
    assert verdict.reason == "removed_before_stage_7"
    assert "a0copy" not in index.removed_ids()  # stage 7 did not remove it; stage 6 did


def test_drop_frees_the_signature_and_counts_itself() -> None:
    index = _sketch_all(_corpus())
    before = index.log.indexed
    assert index.drop(["a0copy", "solocopy"]) == 2
    assert index.log.dropped_before_build == 2
    assert index.log.indexed == before - 2
    assert index._sigs[index._position["a0copy"]] == b""
    assert index.drop(["a0copy"]) == 0  # idempotent


def test_drop_refuses_an_unindexed_id() -> None:
    """A removal list naming documents this pass never saw was computed over a different corpus."""
    index = _sketch_all(_corpus())
    with pytest.raises(KeyError, match="was not indexed"):
        index.drop(["never-seen"])


def test_drop_after_build_is_refused() -> None:
    """By then it has been banded, clustered, and may be a cluster's named survivor."""
    index = _sketch_all(_corpus())
    index.build()
    with pytest.raises(RuntimeError, match=r"build\(\) has already run"):
        index.drop(["a0copy"])
