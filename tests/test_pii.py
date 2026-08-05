"""Engineering invariants for PII redaction (PRD §6.3, §8.1 — CI, never a results table).

The tests are ordered by what they protect. The first group is precision: a phone regex that
eats dates, years, prices and Quranic citations deletes ordinary Urdu prose, and this corpus
contains a great deal of all four. The second is the placeholder contract — the reason `[@]` and
`[#]` look the way they do is that `<EMAIL>` is an HTML tag to stage 5 and `[EMAIL]` is five
Latin letters to stage 3, and either would make the frozen corpus disagree with itself when
re-measured. The third is that nothing here ever retains what it matched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ravaan.data.normalization import normalize_text
from ravaan.data.pii import (
    PII_VERSION,
    PIIConfig,
    PIILog,
    redact,
    redact_text,
)
from ravaan.data.quality import QualityConfig, check, measure

DEFAULT = PIIConfig()
CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "data" / "pii.json"

URDU = "رابطے کے لیے فون نمبر "
PROSE = "پاکستان جنوبی ایشیا کا ایک اہم ملک ہے اور اس کا دارالحکومت اسلام آباد ہے۔ "


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_shipped_config_matches_code_defaults():
    """The committed config is the defaults, or the manifest describes a pass nobody ran."""
    shipped = PIIConfig.from_json_file(CONFIG_PATH)
    assert shipped == DEFAULT
    assert json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["pii_version"] == PII_VERSION


def test_config_round_trips_through_json(tmp_path):
    config = PIIConfig(phone_placeholder="[?]", max_national_digits=11)
    path = tmp_path / "pii.json"
    config.to_json_file(path)
    assert PIIConfig.from_json_file(path) == config


def test_unknown_config_key_is_rejected():
    with pytest.raises(ValueError, match="unknown pii config keys"):
        PIIConfig.from_dict({"redact_names": True})


def test_fingerprint_changes_with_settings():
    assert PIIConfig().fingerprint() != PIIConfig(phone_placeholder="[?]").fingerprint()


# ---------------------------------------------------------------------------
# Precision — what must NOT be redacted
#
# Every fixture here is text this corpus actually contains. A rule that deletes them is not a
# PII pass, it is a corpus-destroying bug of the kind Finding D was.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "یہ واقعہ 2024-03-15 کو پیش آیا۔",  # ISO date
        "تاریخ 05-03-2024 ہے۔",  # trunk-zero-looking date, 8 digits
        "جنگ 1947 سے 1948 تک جاری رہی۔",  # year range
        "سورہ البقرہ 2:255 میں آیت الکرسی ہے۔",  # surah:ayah — why `:` is not a separator
        "قیمت 1,200,000 روپے ہے۔",  # price with thousands separators
        "صفحہ 1234567890 پر درج ہے۔",  # bare 10-digit run, no trunk zero
        "ISBN 978-3-16-148410-0 ہے۔",  # ISBN-13
        "ISBN 0-306-40615-2 درج ہے۔",  # ISBN-10 whose group is a bare `0`
        # The measured false-positive family — 11 of the first 13 phone matches on Urdu
        # Wikipedia. See reports/pii.md §3; every one of these is a real corpus string.
        "آئی ایس بی این 0306406152 ہے۔",  # unhyphenated ISBN-10, ten digits, leading zero
        "بین الاقوامی معیاری کتابی عدد-13: 978-0306406152",  # its ISBN-13 form
        "اکاؤنٹ نمبر 0010012345678901 ہے۔",  # 16-digit account: `00` is not a country code here
        "آئی ایس بی این 0048100221 ہے۔",  # ISBN-10 beginning `00` — not `+92` with 8 digits
        "بین الاقوامی معیاری کتابی عدد-13:978-0048100221",
        "شناختی کارڈ 35202-1234567-1 ہے۔",  # CNIC — PII, but out of §6.3's stated scope
        "وقت 10:30:45 پر۔",
        "ورژن 1.2.3.4 جاری ہوا۔",
    ],
)
def test_ordinary_urdu_text_is_left_alone(text: str) -> None:
    assert redact_text(text) == text


def test_at_sign_used_as_a_word_is_not_an_email():
    assert redact_text("Rs 500 @ 10.5% per unit") == "Rs 500 @ 10.5% per unit"


def test_social_handle_is_not_an_email():
    assert redact_text("follow @urdupoint for updates") == "follow @urdupoint for updates"


def test_bare_digit_run_without_a_trunk_zero_is_not_a_phone():
    # The whole precision argument: a number has to *start* like a number.
    assert redact_text("کوڈ 923001234567 ہے") == "کوڈ 923001234567 ہے"


def test_a_plus_preceded_by_a_digit_is_arithmetic_not_a_country_code():
    assert redact_text("1+923001234567") == "1+923001234567"


# ---------------------------------------------------------------------------
# Recall — what must be redacted
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "number",
    [
        "03001234567",  # mobile, no separators
        "0300-1234567",  # mobile, the usual written form
        "0300 1234567",
        "021-99201234",  # Karachi landline
        "051-9201234",  # Islamabad landline, 10 digits
        "042-111-123-456",  # UAN with a city code, 12 digits
        "+92 300 1234567",
        "+923001234567",
        "0092-300-1234567",  # 00 dialling prefix, same number as the two above
        "(021) 34567890",
        "+44 20 7123 4567",  # not every number in an Urdu corpus is Pakistani
    ],
)
def test_phone_numbers_are_redacted(number: str) -> None:
    result = redact(URDU + number + "۔")
    assert result.counts == {"phone": 1}
    assert number not in result.text
    assert "[#]" in result.text


@pytest.mark.parametrize(
    "address",
    [
        "info@example.com",
        "first.last@sub.example.co.uk",
        "urdu_news+tips@example.pk",
        "A.B@EXAMPLE.ORG",
    ],
)
def test_email_addresses_are_redacted(address: str) -> None:
    result = redact(PROSE + address)
    assert result.counts == {"email": 1}
    assert address not in result.text
    assert result.text.endswith("[@]")


def test_two_space_separated_numbers_both_survive_trimming():
    """The candidate pattern swallows both — a space is a legitimate separator inside one number.

    Returning nothing would be the silent failure: two numbers written this way would sail
    through the pass that exists to remove them.
    """
    result = redact("رابطہ 03001234567 03217654321")
    assert [m.category for m in result.matches] == ["phone", "phone"]
    assert "0300" not in result.text and "0321" not in result.text
    assert result.text.count("[#]") == 2


def test_number_next_to_urdu_letters_is_found():
    # RTL text runs into Latin and digits without a space far more often than English does.
    assert "0300" not in redact_text("فون0300-1234567رابطہ")


def test_an_over_long_digit_run_is_not_a_phone_number():
    assert redact_text("0300-1234567890123") == "0300-1234567890123"


@pytest.mark.parametrize(
    "number",
    [
        "051- 1234567-8",  # 11 digits, separated — a measured true positive
        "061- 4567890",  # 10 digits, separated — the other one
    ],
)
def test_separated_national_numbers_survive_the_isbn_fix(number: str) -> None:
    """Both genuine numbers the Wikipedia probe found were separated; both must still be caught.

    A flat floor of 11 digits would also have removed every ISBN, and would have taken the second
    of these with it. The separator is what distinguishes them, which is why it is the rule.
    """
    assert "[#]" in redact_text(f"ملتان آفس | {number}")


def test_an_unseparated_national_run_needs_the_mobile_length():
    assert redact_text("0414567890") == "0414567890"  # 10 digits, unseparated — not redacted
    assert redact_text("03001234567") == "[#]"  # 11 digits, unseparated — a mobile


def test_brackets_are_left_balanced_either_way():
    # Both directions matter, and fixing the first by consuming `(` unconditionally created the
    # second: `(0300-1234567)` came out as `[#])`.
    assert redact_text("Fax: (051) 9203355") == "Fax: [#]"
    assert redact_text("تحریر : زاہد محمود (0300-1234567)") == "تحریر : زاہد محمود ([#])"


# ---------------------------------------------------------------------------
# Overlap
# ---------------------------------------------------------------------------


def test_digits_inside_an_email_are_not_also_redacted_as_a_phone():
    result = redact("رابطہ 0300123456@example.com پر")
    assert result.counts == {"email": 1}
    assert result.text == "رابطہ [@] پر"


def test_a_phone_after_an_email_is_still_found():
    result = redact("info@example.com یا 0300-1234567")
    assert [m.category for m in result.matches] == ["email", "phone"]


# ---------------------------------------------------------------------------
# The placeholder contract — module docstring §1
#
# These are the tests that stop the corpus disagreeing with itself when re-measured.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("placeholder", "reason"),
    [
        ("<EMAIL>", "angle bracket"),
        ("[EMAIL]", "letter"),
        ("[000]", "digit"),
        ("", "empty"),
    ],
)
def test_unsafe_placeholders_are_refused(placeholder: str, reason: str) -> None:
    with pytest.raises(ValueError):
        PIIConfig(email_placeholder=placeholder)
    with pytest.raises(ValueError):
        PIIConfig(phone_placeholder=placeholder)


def test_placeholders_are_not_html_to_stage_5():
    """`<EMAIL>` would be. Stage 5 rejects at html_ratio > 0.10, and this is the rule that
    would fire on our own redactions when someone re-runs the quality filter over the corpus."""
    redacted = redact_text(PROSE * 3 + " info@example.com 0300-1234567")
    assert measure(redacted).html_ratio == 0.0


def test_placeholders_do_not_move_the_script_ratio():
    """`[EMAIL]`/`[PHONE]` would: five or six Latin letters each, into the denominator of the
    one stage-5 rule whose measured precision is 0.50."""
    clean = PROSE * 3
    redacted = redact_text(clean + " info@example.com 0300-1234567 rابطہ".replace("r", ""))
    assert measure(redacted).script_ratio == pytest.approx(measure(clean).script_ratio, abs=1e-9)


def test_redaction_is_idempotent():
    text = URDU + "0300-1234567 اور info@example.com"
    once = redact_text(text)
    assert redact_text(once) == once


def test_placeholders_survive_normalization_unchanged():
    """Stage 4 runs before this pass, but the freeze re-reads its own output more than once."""
    assert normalize_text("[@] [#]") == "[@] [#]"


def test_redaction_does_not_change_a_stage_5_verdict():
    """Roman-Urdu-Parl rows are single sentences, where a placeholder is a larger share of the
    document than anywhere else in the corpus. If redaction can flip a verdict it flips it here."""
    config = QualityConfig().for_sentences()
    text = "ap ka number 0300-1234567 hai aur email info@example.com hai."
    before = check(text, config, label="roman_urdu")
    after = check(redact_text(text), config, label="roman_urdu")
    assert before.accepted and after.accepted
    assert before.families == after.families


# ---------------------------------------------------------------------------
# Nothing retains what it matched — module docstring §3
# ---------------------------------------------------------------------------


def test_result_does_not_carry_the_original_text():
    assert not hasattr(redact("0300-1234567"), "original")


def test_shapes_describe_without_identifying():
    result = redact(URDU + "0300-1234567 اور ali.raza@example.com")
    shapes = [m.shape for m in result.matches]
    assert shapes == ["dddd-ddddddd", "xxx.xxxx@xxxxxxx.xxx"]


def test_no_serialised_field_contains_the_matched_text():
    number, address = "0300-1234567", "ali.raza@example.com"
    result = redact(f"{URDU}{number} اور {address}")
    blob = json.dumps(result.to_dict(), ensure_ascii=False)
    assert number not in blob and address not in blob
    assert "0300" not in blob and "ali.raza" not in blob

    log = PIILog()
    log.add(result)
    blob = json.dumps(log.to_dict(), ensure_ascii=False)
    assert number not in blob and address not in blob


def test_match_offsets_index_the_input_not_the_output():
    text = "0300-1234567 اور 0321-7654321"
    result = redact(text)
    for match in result.matches:
        assert text[match.start : match.end].startswith("03")


# ---------------------------------------------------------------------------
# Entry points agree, and the log aggregates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "",
        PROSE,
        URDU + "0300-1234567",
        "info@example.com، 0321-7654321 اور 2024-03-15",
        PROSE * 5 + " +92 51 111 222 333",
    ],
)
def test_fast_path_and_logging_path_agree(text: str) -> None:
    assert redact_text(text) == redact(text).text


def test_log_aggregates_documents_and_characters():
    log = PIILog()
    for text in (URDU + "0300-1234567", PROSE, "x info@example.com"):
        log.add(redact(text))
    payload = log.to_dict()
    assert payload["documents"] == 3
    assert payload["documents_redacted"] == 2
    assert payload["counts"] == {"email": 1, "phone": 1}
    assert payload["chars_removed"] == payload["chars_in"] - payload["chars_out"]
    assert payload["config_fingerprint"] == DEFAULT.fingerprint()


def test_log_shape_table_is_bounded():
    log = PIILog(config=PIIConfig(max_shapes=2))
    for i in range(10):
        log.add(redact(f"0300-123456{i} 0092-300-123456{i} +44 20 7123 456{i}"))
    assert len(log.shapes) == 2
    assert log.shapes_dropped > 0


def test_disabling_a_family_leaves_it_alone():
    text = "info@example.com 0300-1234567"
    assert redact(text, PIIConfig(redact_phones=False)).counts == {"email": 1}
    assert redact(text, PIIConfig(redact_emails=False)).counts == {"phone": 1}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_writes_lf_only_and_never_logs_the_match(tmp_path, capsys):
    from ravaan.data.pii import main

    src = tmp_path / "in.txt"
    src.write_text(URDU + "0300-1234567\ninfo@example.com\n", encoding="utf-8", newline="\n")
    out, log = tmp_path / "out.txt", tmp_path / "log.json"

    assert main([str(src), "-o", str(out), "--log", str(log)]) == 0

    written = out.read_bytes()
    assert b"\r" not in written  # the CRLF bug from session 4, one module later
    text = written.decode("utf-8")
    assert "0300" not in text and "info@example.com" not in text
    payload = json.loads(log.read_text(encoding="utf-8"))
    assert payload["counts"] == {"email": 1, "phone": 1}
    assert "0300" not in log.read_text(encoding="utf-8")
