"""Engineering invariants for exact deduplication (PRD §8.1 — CI, never a results table).

Stage 6 deletes documents outright, so the tests that matter are the ones that catch it deleting
the wrong ones, or the *right* ones inconsistently. Four classes of them:

* **Order independence.** The headline property. A corpus released as code + manifest + checksums
  is only reconstructible if the same inputs give the same survivors, and
  ``test_survivors_are_identical_under_every_read_order`` is what stops that being traded away for
  a single-pass implementation later.
* **The line between exact and near.** Two documents differing by one character must both
  survive. Stage 7 has a similarity threshold and a way to report it; stage 6 must not acquire one
  by accident through an over-eager canonicalizer.
* **The Finding F prediction.** Normalizing before hashing has to find the cross-publisher
  duplicates that raw hashing misses, on real Arabic-keyboard Urdu rather than on an assertion.
* **Accounting.** ``distinct + duplicates == indexed`` and ``kept + removed == documents``, so the
  manifest's numbers cannot drift from each other.

Measured behaviour on real text lives in `reports/probe_dedup_*.json`. These are the rules.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from ravaan.data.dedup import (
    DEDUP_VERSION,
    DedupConfig,
    ExactDeduplicator,
    canonical,
    content_hash,
    deduplicate,
    document_key,
    lines,
)
from ravaan.data.normalization import normalize_text

DEFAULT = DedupConfig()
CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "data" / "dedup.json"

URDU_A = (
    "پاکستان جنوبی ایشیا کا ایک اہم ملک ہے جس کی سرحدیں بھارت، افغانستان، ایران اور چین سے ملتی "
    "ہیں۔ اس کا دارالحکومت اسلام آباد ہے جبکہ کراچی سب سے بڑا شہر اور معاشی مرکز سمجھا جاتا ہے۔"
)
URDU_B = (
    "اردو زبان کی ترقی میں شاعروں اور ادیبوں نے نمایاں کردار ادا کیا ہے۔ غالب، اقبال اور فیض کی "
    "شاعری آج بھی برصغیر کے قارئین میں یکساں مقبول ہے اور نئی نسل اسے شوق سے پڑھتی ہے۔"
)

# The same sentence typed on an Urdu keyboard and on an Arabic one — Finding F's mechanism, in the
# two spellings the top 1% of domains actually publish. Stage 4 unifies them; raw bytes do not.
URDU_KEYBOARD = (
    "یہ کتاب بہت اچھی ہے اور اس میں کئی باتیں لکھی ہیں۔ کتاب کا موضوع پاکستان کی تاریخ ہے۔"
)
ARABIC_KEYBOARD = URDU_KEYBOARD.replace("ی", "ي").replace("ک", "ك").replace("ہ", "ه")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_shipped_config_matches_code_defaults():
    """The committed config is the defaults, or the manifest describes a pass nobody ran."""
    shipped = DedupConfig.from_json_file(CONFIG_PATH)
    assert shipped == DEFAULT
    assert json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["dedup_version"] == DEDUP_VERSION


def test_config_round_trips_through_json(tmp_path):
    config = DedupConfig(hash_bits=64, min_paragraph_chars=25)
    path = tmp_path / "dedup.json"
    config.to_json_file(path)
    assert DedupConfig.from_json_file(path) == config
    assert DedupConfig.from_json_file(path).fingerprint() == config.fingerprint()


def test_fingerprint_changes_with_any_setting():
    assert DEFAULT.fingerprint() != DedupConfig(casefold=False).fingerprint()
    assert DEFAULT.fingerprint() != DedupConfig(hash_bits=256).fingerprint()
    assert DEFAULT.fingerprint() != DedupConfig(paragraph_min_documents=3).fingerprint()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"hash_bits": 100},
        {"hash_bits": 32},
        {"variant": "canonical"},
        {"paragraph_mode": "remove"},  # removal is a caller's third pass, not a config value
        {"paragraph_min_documents": 1},
        {"min_paragraph_chars": -1},
        {"max_index_entries": 0},
    ],
)
def test_invalid_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        DedupConfig(**kwargs)


def test_unknown_config_keys_are_rejected():
    with pytest.raises(ValueError, match="unknown dedup config keys"):
        DedupConfig.from_dict({"hash_bits": 128, "min_similarity": 0.8})


# ---------------------------------------------------------------------------
# Canonicalization — the boundary with stage 7
# ---------------------------------------------------------------------------


def test_whitespace_differences_do_not_make_two_documents():
    """Two extractors wrapping the same article differently produce one document, not two."""
    wrapped = URDU_A.replace("۔ ", "۔\n")
    assert canonical(wrapped) == canonical(URDU_A)
    assert content_hash(wrapped) == content_hash(URDU_A)


def test_case_folding_merges_roman_urdu_spellings_and_is_a_no_op_on_urdu():
    assert content_hash("Aik Larka School Gaya") == content_hash("aik larka school gaya")
    assert canonical(URDU_A) == canonical(URDU_A.casefold())


@pytest.mark.parametrize(
    ("left", "right"),
    [
        # One character. This is stage 7's territory and stage 6 must not touch it.
        (URDU_A, URDU_A[:-1] + "؟"),
        # Punctuation is content: canonicalization stops at whitespace and case.
        (URDU_A, URDU_A.replace("،", "")),
        # Harakat are information, not noise — the normalizer preserves them and so must this.
        ("کِتاب پڑھی گئی ہے اور بہت پسند آئی", "کتاب پڑھی گئی ہے اور بہت پسند آئی"),
        # Bari ye is a distinct grapheme; folding it here would undo stage 4's whole doctrine.
        ("یہ بات ٹھیک ہے اور سب جانتے ہیں", "یہ بات ٹھیک ہی اور سب جانتے ہیں"),
    ],
)
def test_near_duplicates_are_not_exact_duplicates(left, right):
    assert content_hash(left) != content_hash(right)
    verdicts, _ = deduplicate([("a", left), ("b", right)])
    assert all(verdict.kept for verdict in verdicts)


def test_hashes_do_not_depend_on_the_process():
    """PYTHONHASHSEED must not reach a corpus decision — pinned digests, not just equality.

    ``hash()`` is salted per process; a frozen corpus that used it would put the same document in
    a different group on every run, and nothing downstream would notice.
    """
    assert f"{content_hash('ravaan', bits=64):016x}" == "f8918a71b1771652"
    assert f"{document_key('urdu-wikipedia:122264', bits=64):016x}" == "ce231401b2072199"
    # And the two keyed spaces are genuinely independent: same input, different personalisation.
    assert content_hash("ravaan", bits=64) != document_key("ravaan", bits=64)


# ---------------------------------------------------------------------------
# Order independence — the property the second pass buys
# ---------------------------------------------------------------------------


def _corpus(copies: int = 4) -> list[tuple[str, str]]:
    records = [(f"doc-{i}", URDU_A) for i in range(copies)]
    records += [(f"other-{i}", URDU_B) for i in range(copies - 1)]
    records += [(f"unique-{i}", f"{URDU_A} فقرہ نمبر {i} یہاں ختم ہوتا ہے۔") for i in range(5)]
    return records


def test_survivors_are_identical_under_every_read_order():
    """The corpus is a function of its inputs, not of the seed the reader happened to shuffle with.

    PRD §6.3 releases code, manifest and checksums but no text, so re-running the pipeline is the
    only way the frozen corpus is ever reconstructed. If this fails, it cannot be.
    """
    records = _corpus()
    baseline = None
    for seed in range(12):
        shuffled = records[:]
        random.Random(seed).shuffle(shuffled)
        verdicts, _ = deduplicate(shuffled)
        kept = frozenset(v.doc_id for v in verdicts if v.kept)
        if baseline is None:
            baseline = kept
        assert kept == baseline, f"seed {seed} produced a different corpus"
    assert baseline is not None and len(baseline) == 7  # 1 + 1 + 5


def test_survivor_is_the_lowest_key_not_the_first_seen():
    ids = [f"doc-{i}" for i in range(6)]
    expected = min(ids, key=lambda doc_id: document_key(doc_id))
    verdicts, _ = deduplicate([(doc_id, URDU_A) for doc_id in ids])
    kept = [v.doc_id for v in verdicts if v.kept]
    assert kept == [expected]
    assert kept != [ids[0]] or expected == ids[0]


def test_a_document_that_was_not_indexed_is_an_error_not_a_deletion():
    """Phase 2 reading a different set than phase 1 shortens the corpus silently. Refuse instead."""
    index = ExactDeduplicator()
    index.index("a", URDU_A)
    with pytest.raises(KeyError, match="was not indexed in phase 1"):
        index.decide("b", URDU_B)


# ---------------------------------------------------------------------------
# Finding F — normalizing before hashing is the point of the stage order
# ---------------------------------------------------------------------------


def test_normalizing_before_hashing_finds_cross_publisher_duplicates():
    """The same text from an Arabic-keyboard publisher and an Urdu one is one document.

    Session 5 measured this: the top 1% of domains carry 65.3% of Arabic-variant hits, and
    religious publishers republish the same texts across many domains. Stage 4 before stage 6 is
    what makes those copies hash alike, and this is that claim as a test.
    """
    records = [
        ("pk-site:1", normalize_text(URDU_KEYBOARD), URDU_KEYBOARD),
        ("ir-site:1", normalize_text(ARABIC_KEYBOARD), ARABIC_KEYBOARD),
    ]
    assert records[0][1] == records[1][1]  # stage 4 unified them
    assert records[0][2] != records[1][2]  # the bytes never were

    verdicts, index = deduplicate(records)
    assert sum(1 for v in verdicts if v.kept) == 1
    assert index.log.duplicate_documents == 1
    # And the counterfactual, from the same pass: raw hashing would have kept both.
    assert index.log.alternate_duplicate_documents == 0


def test_variant_raw_decides_on_the_unnormalized_text():
    """The comparison run, for the report. Same inputs, the other hash deciding."""
    records = [
        ("pk-site:1", normalize_text(URDU_KEYBOARD), URDU_KEYBOARD),
        ("ir-site:1", normalize_text(ARABIC_KEYBOARD), ARABIC_KEYBOARD),
    ]
    verdicts, index = deduplicate(records, DedupConfig(variant="raw"))
    assert all(v.kept for v in verdicts)
    assert index.log.duplicate_documents == 0
    assert index.log.alternate_duplicate_documents == 1
    assert index.config.alternate_variant == "normalized"


# ---------------------------------------------------------------------------
# Accounting
# ---------------------------------------------------------------------------


def test_the_log_balances():
    verdicts, index = deduplicate([(f"d{i}", text) for i, text in enumerate(_texts())])
    log = index.log
    assert log.documents == log.documents_kept + sum(1 for v in verdicts if not v.kept)
    assert index.distinct_documents + log.duplicate_documents == log.indexed
    assert log.documents_kept == index.distinct_documents
    assert log.chars_kept <= log.chars_in


def _texts() -> list[str]:
    return [URDU_A, URDU_A, URDU_B, URDU_A, URDU_B, f"{URDU_A}{URDU_B}"]


def test_group_size_and_sources_are_reported():
    records = [
        ("fineweb2-urd_Arab:1", URDU_A, None, "fineweb2-urd_Arab"),
        ("urdu-wikipedia:1", URDU_A, None, "urdu-wikipedia"),
        ("urdu-wikipedia:2", URDU_B, None, "urdu-wikipedia"),
    ]
    verdicts, index = deduplicate(records)
    assert {v.group_size for v in verdicts if v.group_size > 1} == {2}
    assert index.log.cross_source_groups == 1
    assert index.log.cross_source_pairs == {"fineweb2-urd_Arab|urdu-wikipedia": 1}
    top = index.top_groups()
    assert top[0]["size"] == 2
    assert top[0]["sources"] == ["fineweb2-urd_Arab", "urdu-wikipedia"]
    assert top[0]["kept"] in {"fineweb2-urd_Arab:1", "urdu-wikipedia:1"}


def test_single_source_groups_allocate_no_per_group_side_tables():
    """Per-group bookkeeping must not be sized by the number of groups.

    PRD §6.2 predicts Roman-Urdu-Parl's 6.37M pairs collapse to ~1.09M unique Urdu sentences, so
    on that source nearly *every* group repeats. A source set and an example list per group is
    about a gigabyte of Python objects describing a corpus that indexes in a fraction of it, and
    the failure only shows up on the one source whose whole point is being heavily duplicated.
    """
    records = [(f"d{i}", f"{URDU_A} فقرہ {i % 50}۔", None, "urdu-wikipedia") for i in range(300)]
    _, index = deduplicate(records)
    assert index.log.duplicate_groups == 50
    assert index._group_sources == {}, "a one-source group needs no set to say so"
    assert index.log.cross_source_groups == 0
    # ...and the report can still name each group's source, from the per-hash record.
    assert {tuple(group["sources"]) for group in index.top_groups()} == {("urdu-wikipedia",)}


def test_example_ids_are_kept_only_for_the_largest_groups():
    records = [(f"d{i}", f"{URDU_A} فقرہ {i % 30}۔") for i in range(90)]
    index = ExactDeduplicator(example_groups=5)
    for doc_id, text in records:
        index.index(doc_id, text)
    for doc_id, text in records:
        index.decide(doc_id, text)
    assert index.log.duplicate_groups == 30
    assert len(index._group_examples) == 5
    top = index.top_groups(limit=30)
    assert all(group["duplicates"] for group in top[:5])
    assert all(not group["duplicates"] for group in top[5:]), "sizes without ids past the cap"


def test_removed_by_source_is_tracked_separately_from_kept():
    records = [(f"s{i}", URDU_A, None, "urdu-wikipedia") for i in range(3)]
    _, index = deduplicate(records)
    assert index.log.by_source["urdu-wikipedia"] == 3
    assert index.log.kept_by_source["urdu-wikipedia"] == 1
    assert index.log.removed_by_source["urdu-wikipedia"] == 2


def test_to_dict_is_json_serializable_and_carries_the_fingerprint():
    _, index = deduplicate([("a", URDU_A), ("b", URDU_A)])
    payload = index.to_dict()
    assert payload["config_fingerprint"] == DEFAULT.fingerprint()
    assert payload["duplicate_documents"] == 1
    json.dumps(payload, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Paragraph level
# ---------------------------------------------------------------------------

BOILERPLATE = "اس ویب سائٹ پر شائع ہونے والے تمام مضامین کے جملہ حقوق محفوظ ہیں اور اجازت ضروری ہے۔"
SHORT_FURNITURE = "مزید پڑھیں"


def _page(body: str) -> str:
    return f"{SHORT_FURNITURE}\n{body}\n{BOILERPLATE}"


def test_lines_skips_furniture_below_the_floor():
    found = list(lines(_page(URDU_A), min_chars=60))
    assert SHORT_FURNITURE not in found
    assert BOILERPLATE in found


def test_paragraph_counts_come_from_survivors_not_from_the_indexed_set():
    """Counting lines in phase 1 would inflate every count by the copies stage 6 is deleting.

    Three documents, two of them byte-identical. The shared footer appears in two *surviving*
    documents, not three, and the duplicated-character figure the report quotes has to say two.
    """
    records = [
        ("a", _page(URDU_A)),
        ("a-copy", _page(URDU_A)),
        ("b", _page(URDU_B)),
    ]
    _, index = deduplicate(records)
    index.finish_paragraphs()
    log = index.log
    assert log.documents_kept == 2
    assert log.paragraph_duplicate_units == 2  # the footer, in two survivors
    assert log.paragraph_chars_duplicated == 2 * len(BOILERPLATE)
    assert log.paragraph_chars_removable == len(BOILERPLATE)


def test_paragraph_mode_off_measures_nothing():
    _, index = deduplicate([("a", _page(URDU_A))], DedupConfig(paragraph_mode="off"))
    index.finish_paragraphs()
    assert index.log.paragraph_units == 0
    assert index.log.paragraph_chars == 0


def test_a_line_repeated_inside_one_document_is_not_corpus_boilerplate():
    """That is stage 5's dup_line_ratio. Counting it here makes one bad page look like a corpus."""
    text = "\n".join([BOILERPLATE] * 5)
    _, index = deduplicate([("a", text)])
    index.finish_paragraphs()
    assert index.log.paragraph_units == 1
    assert index.log.paragraph_duplicate_units == 0


def test_strip_refuses_until_phase_2_has_finished():
    """Half-built line counts would keep every line whose second copy had not been read yet.

    That is a corpus that depends on where the pass got to — the exact failure the two-phase
    design exists to prevent at document level, one level down.
    """
    index = ExactDeduplicator()
    index.index("a", _page(URDU_A))
    index.decide("a", _page(URDU_A))
    with pytest.raises(RuntimeError, match="finish_paragraphs"):
        index.strip("a", _page(URDU_A))
    index.finish_paragraphs()
    index.strip("a", _page(URDU_A))  # now allowed

    off = ExactDeduplicator(DedupConfig(paragraph_mode="off"))
    off.index("a", URDU_A)
    off.decide("a", URDU_A)
    off.finish_paragraphs()
    with pytest.raises(RuntimeError, match="paragraph_mode is 'off'"):
        off.strip("a", URDU_A)


def test_strip_removes_shared_lines_from_all_but_one_document():
    records = [("a", _page(URDU_A)), ("b", _page(URDU_B))]
    _, index = deduplicate(records)
    index.finish_paragraphs()
    stripped = {doc_id: index.strip(doc_id, text) for doc_id, text in records}

    keepers = [doc_id for doc_id, result in stripped.items() if BOILERPLATE in result.text]
    assert len(keepers) == 1, "exactly one copy of a duplicated line survives"
    for doc_id, result in stripped.items():
        assert SHORT_FURNITURE in result.text, "lines below the floor are never touched"
        assert (URDU_A if doc_id == "a" else URDU_B) in result.text
    assert index.log.paragraph_documents_changed == 1
    assert index.log.paragraphs_removed == 1


def test_strip_never_empties_a_document():
    """Every line living elsewhere is a near-duplicate finding, not a removal instruction."""
    shared = f"{BOILERPLATE}\n{URDU_A}"
    records = [("a", shared), ("b", f"{shared}\n{URDU_B}")]
    _, index = deduplicate(records)
    index.finish_paragraphs()
    loser = min(("a", "b"), key=lambda doc_id: -document_key(doc_id))
    result = index.strip(loser, dict(records)[loser])
    assert result.text.strip()
    if result.emptied:
        assert result.text == dict(records)[loser]
        assert index.log.paragraph_documents_emptied == 1


def test_strip_is_lossless_when_nothing_is_shared():
    text = _page(URDU_A)
    _, index = deduplicate([("a", text), ("b", URDU_B)])
    index.finish_paragraphs()
    assert index.strip("a", text).text == text


# ---------------------------------------------------------------------------
# Degenerate input
# ---------------------------------------------------------------------------


def test_empty_and_whitespace_documents_collapse_to_one_group():
    verdicts, index = deduplicate([("a", ""), ("b", "   "), ("c", "\n\n\t")])
    assert sum(1 for v in verdicts if v.kept) == 1
    assert index.log.duplicate_documents == 2


def test_sentence_sources_deduplicate_at_their_own_unit():
    """Roman-Urdu-Parl's 6.37M pairs collapse to ~1.09M unique Urdu sentences (PRD §6.2).

    Sentences are short, so nothing about stage 6 may assume a document floor — this is the source
    that decides whether §6.1's 40M-token Roman Urdu budget survives.
    """
    sentences = ["aik larka school gaya", "Aik larka school gaya", "larki ghar wapas aayi"]
    verdicts, index = deduplicate([(f"r{i}", s) for i, s in enumerate(sentences)])
    assert sum(1 for v in verdicts if v.kept) == 2
    assert index.log.duplicate_documents == 1


def test_index_ceiling_raises_rather_than_swaps():
    index = ExactDeduplicator(DedupConfig(max_index_entries=2, paragraph_mode="off"))
    index.index("a", URDU_A)
    index.index("b", URDU_B)
    with pytest.raises(MemoryError, match="max_index_entries"):
        index.index("c", f"{URDU_A}{URDU_B}")


def test_is_kept_agrees_with_decide_and_leaves_the_log_alone():
    records = [("a", URDU_A), ("b", URDU_A), ("c", URDU_B)]
    index = ExactDeduplicator()
    for doc_id, text in records:
        index.index(doc_id, text)
    predicted = {doc_id: index.is_kept(doc_id, text) for doc_id, text in records}
    assert index.log.documents == 0
    assert predicted == {doc_id: index.decide(doc_id, text).kept for doc_id, text in records}


# --- wins_group(): the text-free survivor test ------------------------------


def test_wins_group_agrees_with_is_kept_without_the_text() -> None:
    """The accessor a single-pass driver needs. `is_kept` asks the same question and wants the
    document back, which is useless to a caller that has already thrown the corpus away."""
    index = ExactDeduplicator()
    docs = {"d1": "same text", "d2": "same text", "d3": "other text", "d4": "third text"}
    for doc_id, text in docs.items():
        index.index(doc_id, text)
    index.seal()

    for doc_id, text in docs.items():
        assert index.wins_group(doc_id) == index.is_kept(doc_id, text), doc_id

    # Exactly one of the duplicate pair wins, and it is the lower-keyed one either way.
    assert index.wins_group("d1") != index.wins_group("d2")
    assert index.wins_group("d3") and index.wins_group("d4")


def test_wins_group_matches_decide_over_a_whole_corpus() -> None:
    """The property the driver actually depends on: the same surviving set, from ids alone."""
    index = ExactDeduplicator()
    docs = {f"doc{i}": f"body number {i % 7}" for i in range(40)}
    for doc_id, text in docs.items():
        index.index(doc_id, text)
    index.seal()

    by_key = {doc_id for doc_id in docs if index.wins_group(doc_id)}
    by_decide = {doc_id for doc_id, text in docs.items() if index.decide(doc_id, text).kept}
    assert by_key == by_decide
    assert len(by_key) == 7  # one survivor per distinct body


def test_wins_group_cannot_tell_removed_from_never_indexed() -> None:
    """Stated because it is a real limitation, and because the intended caller cannot hit it: it
    iterates its own index of the same pass, so every id it asks about was indexed."""
    index = ExactDeduplicator()
    index.index("d1", "text")
    index.seal()
    assert not index.wins_group("never-indexed")
