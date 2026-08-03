"""Engineering invariants for encoding validation (PRD §8.1 — CI, never a results table)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ravaan.data.encoding import (
    ENCODING_VERSION,
    MOJIBAKE_ALPHABET,
    EncodingConfig,
    EncodingLog,
    decode_sloppy_cp1252,
    repair_mojibake,
    validate_bytes,
    validate_text,
)

DEFAULT = EncodingConfig()

CLEAN = "یہ ایک صاف اردو جملہ ہے۔ قیمت 500 روپے ہے۔"

# The same sentence after the classic failure: UTF-8 bytes served as cp1252. Built with the
# sloppy decoder because ہ (U+06C1) is UTF-8 D9 81 and Python's strict cp1252 codec refuses
# byte 0x81 — the browsers that produced this material did not.
MOJIBAKE = decode_sloppy_cp1252(CLEAN.encode("utf-8"))


# --- Mojibake: the defect that costs us real Urdu ---------------------------
# For Arabic script every codepoint is a 2-byte UTF-8 sequence, so a mis-decoded Urdu page
# contains no Urdu at all. These documents are fully recoverable and would otherwise be dropped
# by stage 3 as "European text". Highest-value tests in the file.


def test_the_mojibake_fixture_really_is_broken() -> None:
    # Guard the fixture itself: if it is not actually broken, the tests below prove nothing.
    assert MOJIBAKE != CLEAN
    # Every Arabic-script codepoint is a 2-byte UTF-8 sequence, so a mis-decoded Urdu page
    # contains no Urdu whatsoever. This is why stage 3 would score it as European text and drop
    # a perfectly recoverable document.
    assert not any("؀" <= ch <= "ۿ" for ch in MOJIBAKE)
    assert set(MOJIBAKE) & set(MOJIBAKE_ALPHABET)


def test_mojibake_round_trips_back_to_the_original() -> None:
    repaired, passes = repair_mojibake(MOJIBAKE)
    assert repaired == CLEAN
    assert passes == 1


def test_double_encoded_mojibake_needs_two_passes() -> None:
    twice = decode_sloppy_cp1252(MOJIBAKE.encode("utf-8"))
    repaired, passes = repair_mojibake(twice)
    assert repaired == CLEAN
    assert passes == 2


def test_repair_stops_at_the_configured_pass_limit() -> None:
    twice = decode_sloppy_cp1252(MOJIBAKE.encode("utf-8"))
    repaired, passes = repair_mojibake(twice, max_passes=1)
    assert passes == 1
    assert repaired == MOJIBAKE  # one pass undoes one layer, no more


def test_validate_accepts_and_repairs_mojibake() -> None:
    result = validate_text(MOJIBAKE)
    assert result.verdict == "repaired"
    assert result.accepted
    assert result.text == CLEAN
    assert result.repair_passes == 1


def test_mojibake_is_rejected_when_repair_is_disabled() -> None:
    result = validate_text(MOJIBAKE, EncodingConfig(repair_mojibake=False))
    assert result.verdict == "mojibake"
    assert not result.accepted
    assert result.text is None


# --- Repair must not fire on text that is merely non-English ----------------
# A repair pass that "fixes" correct text is worse than no repair at all: it is silent and it
# corrupts the corpus. Every one of these must come out byte-identical.


@pytest.mark.parametrize(
    "text",
    [
        CLEAN,
        "Hello, world.",
        "café",  # single accented char — one mojibake-alphabet char, no run
        "naïve résumé",
        "Ünnötig große Ölkännchen",  # German: adjacent umlauts inside words, but not a run
        "ہم نے café میں chai پی",  # code-switched, which Ravaan's corpus is full of
        "«guillemets» and — dashes",
        "",
    ],
)
def test_correct_text_is_never_repaired(text: str) -> None:
    repaired, passes = repair_mojibake(text)
    assert passes == 0
    assert repaired == text
    assert validate_text(text).text == text


# Every string below was flagged as mojibake by the first version of the detector, which counted
# any run of two or more characters from the cp1252 alphabet. It rejected 591 of 20,000 Urdu
# Wikipedia articles — 3% of a clean corpus, deleted silently. Counts are hits in that sample.
@pytest.mark.parametrize(
    ("run", "why"),
    [
        ("‘‘", "Urdu Wikipedia's own opening quotation mark, doubled — 2,234 hits"),
        ("’’", "its closing pair — 2,226 hits"),
        ("\xa0\xa0", "non-breaking spaces used as layout padding — 47 hits"),
        ("\xa0\xa0\xa0\xa0\xa0\xa0\xa0", "longer padding run"),
        ("——————————", "an em-dash horizontal rule"),
        ("\xa0–", "non-breaking space before an en dash"),
        ("\xa0°", "non-breaking space before a degree sign"),
        ("çã", "a Portuguese name in an Urdu article"),
        ("‘‘’’", "an empty quotation"),
    ],
)
def test_real_wikipedia_punctuation_is_not_mojibake(run: str, why: str) -> None:
    document = f"یہ ایک اقتباس ہے {run} اور یہ متن درست ہے۔"
    result = validate_text(document)
    assert result.verdict == "ok", why
    assert result.mojibake_chars == 0, why
    assert result.text == document


def test_the_detector_is_the_round_trip_not_the_character_class() -> None:
    # ‘‘ re-encodes to 0x91 0x91: two bare UTF-8 continuation bytes, which no sequence can start
    # with. ÙŒ re-encodes to D9 8C, a well-formed 2-byte sequence. Only the second is mojibake,
    # and both are equally "a run of two cp1252 characters".
    assert all(ch in MOJIBAKE_ALPHABET for ch in "‘‘")
    assert validate_text("‘‘" * 500).mojibake_chars == 0
    assert validate_text(MOJIBAKE).repair_passes == 1


def test_a_run_of_accented_latin_that_is_not_utf8_is_left_alone() -> None:
    # "ÀÀÀ" is a run in the mojibake alphabet but is not valid UTF-8 when re-encoded, so the
    # round trip fails and the text survives. Repair is byte-exact or it does not happen.
    repaired, passes = repair_mojibake("ÀÀÀ")
    assert (repaired, passes) == ("ÀÀÀ", 0)


def test_partial_mojibake_is_flagged_but_not_silently_rewritten() -> None:
    # Only half the document is broken, so the whole-document round trip cannot apply. It must
    # not be half-repaired either — it is counted and left for the threshold to judge.
    mixed = CLEAN + " " + MOJIBAKE
    repaired, passes = repair_mojibake(mixed)
    assert passes == 0
    assert repaired == mixed
    assert validate_text(mixed).verdict == "mojibake"


def test_mojibake_alphabet_is_exactly_the_high_bytes() -> None:
    assert len(MOJIBAKE_ALPHABET) == 128
    assert all(ord(ch) >= 0x80 for ch in MOJIBAKE_ALPHABET)


# --- Strict UTF-8 -----------------------------------------------------------


def test_valid_utf8_decodes_and_is_accepted() -> None:
    result = validate_bytes(CLEAN.encode("utf-8"))
    assert result.verdict == "ok"
    assert result.text == CLEAN
    assert result.bytes_in == len(CLEAN.encode("utf-8"))


def test_invalid_utf8_is_rejected_not_patched() -> None:
    # A 2-byte Urdu character cut in half — what a shard truncated on a chunk boundary looks
    # like. `errors="replace"` would turn this into a plausible document with one U+FFFD in it.
    result = validate_bytes(CLEAN.encode("utf-8")[:-1])
    assert result.verdict == "undecodable"
    assert result.text is None
    assert "byte" in (result.decode_error or "")


def test_replace_policy_keeps_the_document_but_the_rate_check_still_applies() -> None:
    lenient = EncodingConfig(on_decode_error="replace")
    # One bad byte in a long document survives; a document that is mostly bad bytes does not.
    ok = validate_bytes(b"\xff" + CLEAN.encode("utf-8") * 40, lenient)
    assert ok.verdict == "ok"
    assert ok.replacement_chars == 1

    bad = validate_bytes(b"\xff\xfe\xfd" + b"abc", lenient)
    assert bad.verdict == "replacement_heavy"


def test_bom_is_stripped_at_the_byte_layer() -> None:
    result = validate_bytes(b"\xef\xbb\xbf" + CLEAN.encode("utf-8"))
    assert result.text == CLEAN
    assert not result.text.startswith("﻿")


def test_bom_survives_when_stripping_is_disabled() -> None:
    # Stage 4 removes it as a zero-width character; this only asserts stage 2 stays out of the way.
    keep = EncodingConfig(strip_bom=False)
    result = validate_bytes(b"\xef\xbb\xbf" + CLEAN.encode("utf-8"), keep)
    assert result.text.startswith("﻿")


# --- Replacement characters -------------------------------------------------


def test_replacement_heavy_documents_are_rejected() -> None:
    result = validate_text("���سلام")
    assert result.verdict == "replacement_heavy"
    assert not result.accepted


def test_a_single_replacement_char_in_a_long_document_passes() -> None:
    result = validate_text(CLEAN * 60 + "�")
    assert result.verdict == "ok"
    assert result.replacement_chars == 1
    assert result.replacement_rate < DEFAULT.max_replacement_rate


# --- Control characters -----------------------------------------------------


def test_control_characters_are_stripped_so_they_never_reach_the_tokenizer() -> None:
    result = validate_text(CLEAN * 60 + "\x00\x07")
    assert result.verdict == "ok"
    assert result.control_chars == 2
    assert "\x00" not in result.text
    assert result.chars == len(CLEAN * 60)


def test_binary_garbage_is_rejected_rather_than_stripped_down_to_nothing() -> None:
    result = validate_text("\x00\x01\x02\x03\x04 abc")
    assert result.verdict == "control_heavy"
    assert not result.accepted


@pytest.mark.parametrize("ws", ["\t", "\n", "\r", "\v", "\f"])
def test_real_whitespace_is_not_treated_as_a_control_character(ws: str) -> None:
    # Stage 4 owns these; stage 2 must leave them alone.
    result = validate_text(f"سلام{ws}دنیا")
    assert result.control_chars == 0
    assert ws in result.text


def test_control_stripping_can_be_switched_off() -> None:
    keep = EncodingConfig(strip_control_chars=False)
    result = validate_text(CLEAN * 60 + "\x00", keep)
    assert result.verdict == "ok"
    assert "\x00" in result.text


# --- Ordering: mojibake before controls -------------------------------------


def test_mojibake_is_repaired_before_control_characters_are_counted() -> None:
    # ہ (U+06C1) is UTF-8 D9 81, and 0x81 is simultaneously a cp1252-undefined slot and a C1
    # control. A mis-decoded Urdu document is therefore full of characters that look like
    # control bytes. Counting controls first would reject exactly the documents that are
    # recoverable — and it would look like a quality filter doing its job.
    assert any(0x80 <= ord(ch) <= 0x9F for ch in MOJIBAKE)
    result = validate_text(MOJIBAKE)
    assert result.verdict == "repaired"
    assert result.text == CLEAN
    assert result.control_chars == 0


# --- Empty and degenerate input ---------------------------------------------


def test_empty_document_is_accepted_without_dividing_by_zero() -> None:
    result = validate_text("")
    assert result.verdict == "ok"
    assert result.chars == 0
    assert result.replacement_rate == 0.0
    assert result.mojibake_rate == 0.0
    assert result.control_rate == 0.0


# --- Config -----------------------------------------------------------------


def test_shipped_config_matches_the_code_defaults() -> None:
    path = Path(__file__).resolve().parents[1] / "configs" / "data" / "encoding.json"
    shipped = json.loads(path.read_text(encoding="utf-8"))
    assert shipped["encoding_version"] == ENCODING_VERSION
    assert EncodingConfig.from_json_file(path) == DEFAULT


def test_config_round_trips_through_json(tmp_path: Path) -> None:
    config = EncodingConfig(max_replacement_rate=0.01, repair_mojibake=False)
    path = tmp_path / "encoding.json"
    config.to_json_file(path)
    assert EncodingConfig.from_json_file(path) == config


def test_unknown_config_keys_are_rejected() -> None:
    with pytest.raises(ValueError, match="unknown encoding config keys"):
        EncodingConfig.from_dict({"max_replacement_rate": 0.1, "typo_here": True})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"on_decode_error": "ignore"},
        {"max_repair_passes": 0},
        {"max_replacement_rate": 1.5},
        {"max_control_rate": -0.1},
        {"max_mojibake_rate": 2.0},
    ],
)
def test_invalid_config_is_rejected_at_construction(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        EncodingConfig(**kwargs)


def test_fingerprint_changes_with_settings_and_is_stable() -> None:
    a = EncodingConfig()
    assert a.fingerprint() == EncodingConfig().fingerprint()
    assert a.fingerprint() != EncodingConfig(max_replacement_rate=0.5).fingerprint()
    assert len(a.fingerprint()) == 12


def test_results_carry_the_config_fingerprint_for_the_manifest() -> None:
    config = EncodingConfig(max_replacement_rate=0.5)
    assert validate_text(CLEAN, config).config_fingerprint == config.fingerprint()


# --- Corpus-level log -------------------------------------------------------


def test_log_aggregates_verdicts_and_acceptance() -> None:
    log = EncodingLog()
    log.add(validate_text(CLEAN))
    log.add(validate_text(MOJIBAKE))
    log.add(validate_text("��x"))
    log.add(validate_bytes(b"\xff\xfe"))

    assert log.documents == 4
    assert log.documents_accepted == 2
    assert log.documents_repaired == 1
    assert log.acceptance_rate == 0.5
    assert log.verdicts == {
        "ok": 1,
        "repaired": 1,
        "replacement_heavy": 1,
        "undecodable": 1,
    }


def test_log_serializes_to_json_for_the_manifest() -> None:
    log = EncodingLog()
    log.add(validate_text(CLEAN))
    payload = log.to_dict()
    assert payload["encoding_version"] == ENCODING_VERSION
    assert payload["config_fingerprint"] == DEFAULT.fingerprint()
    assert payload["documents_rejected"] == 0
    json.dumps(payload)  # must be serializable as-is


# --- CLI --------------------------------------------------------------------


def test_cli_filters_a_jsonl_shard(tmp_path: Path) -> None:
    from ravaan.data.encoding import main

    shard = tmp_path / "shard.jsonl"
    shard.write_text(
        "\n".join(
            json.dumps(record, ensure_ascii=False)
            for record in (
                {"id": 1, "text": CLEAN},
                {"id": 2, "text": MOJIBAKE},
                {"id": 3, "text": "���x"},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    out, log = tmp_path / "clean.jsonl", tmp_path / "stage2.json"
    assert main([str(shard), "--jsonl", "-o", str(out), "--log", str(log)]) == 0

    kept = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [r["id"] for r in kept] == [1, 2]
    assert kept[1]["text"] == CLEAN  # the mojibake record came back as Urdu
    assert json.loads(log.read_text(encoding="utf-8"))["documents_rejected"] == 1
