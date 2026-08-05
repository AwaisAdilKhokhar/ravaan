"""PII redaction — one regex pass for phone numbers and email addresses (PRD §6.3).

PRD §6.3 asks for exactly this and then says what not to do: *"Minimal PII handling: one regex
pass for phone numbers and emails. Do not build a PII system."* So this module has two patterns
and no model, no gazetteer and no name detection. Four properties it is built around, each of
which is a decision that a plainer implementation would have got wrong.

1. **The placeholders are inert to every stage that already ran.** The obvious choice —
   ``<EMAIL>`` — is matched by stage 5's ``_HTML_TAG_RE``, so re-running the quality filter over
   the frozen corpus would score our own redactions as HTML residue and reject documents the
   original run kept. The obvious *second* choice — ``[EMAIL]`` — puts five Latin letters into
   stage 3's letter count and stage 5's ``script_ratio`` denominator, moving a rule whose
   precision is already 0.50. So the shipped placeholders are ``[@]`` and ``[#]``: no letters, no
   digits, no angle brackets. :class:`PIIConfig` *enforces* those three properties rather than
   documenting them, because the whole point is that the corpus survives being re-measured.

2. **Phone matching is anchored on dialling structure, not on runs of digits.** A "7+ digits"
   rule deletes dates, year ranges, prices, ISBNs and Quranic citations (``2:255``), and this
   corpus is full of all five — Finding F put religious publishers among its largest
   contributors. Every match must therefore begin with an international prefix (``+`` / ``00``)
   or a national trunk zero followed by a contiguous 2–3 digit area or mobile prefix, and must
   carry a plausible number of digits. ``2024-03-15`` does not start with a trunk zero;
   ``05-03-2024`` has eight digits, under the floor; ``2:255`` has no separator this pass
   recognises, because ``:`` is deliberately not one.

3. **Nothing here ever stores what it matched.** :class:`PIIResult` has no ``original`` field —
   unlike :class:`~ravaan.data.normalization.NormalizationResult`, which keeps one — and
   :class:`PIIMatch` carries a *shape* (``0300-1234567`` → ``dddd-ddddddd``) instead of the text.
   A result object that carried the match would serialise the corpus's phone numbers into
   whatever log wrote it out, which is the artifact this stage exists to prevent. The shape is
   enough to adjudicate precision: a false positive is a date or an ISBN, and those have
   different shapes.

4. **Redaction is idempotent.** ``redact(redact(x)) == redact(x)``, which follows from property 1
   and is locked by a test. The freeze re-reads its sources more than once.

**Where this runs.** After stage 5, before stage 6 — see ``reports/pii.md`` §2. Stage 5's
thresholds were calibrated against the 200-sample of *unredacted* text, so redacting earlier
would measure documents the validation never saw; hashing at stage 6 or 7 first would fingerprint
text that the frozen corpus does not contain. Between them, every hash, shingle, split assignment
and packed token is over the redacted text and nothing is over anything else.

Two entry points share one scanner:

* :func:`redact_text` — fast path, redacted text only, for the corpus run.
* :func:`redact` — same output plus per-match shapes, for sampling and the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

__all__ = [
    "PII_VERSION",
    "PIIConfig",
    "PIILog",
    "PIIMatch",
    "PIIResult",
    "redact",
    "redact_text",
]

# Bump on any change to the *output* of redaction. The corpus manifest records this.
PII_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Separators a phone number is written with. `.` and `/` are excluded on purpose: `.` makes
# every version string, IP address and dotted date a candidate, and `/` merges the two numbers in
# "0300-1234567 / 0321-7654321" into one over-long candidate. Both cost a little recall on
# unusual formatting and buy precision on material this corpus actually contains. `:` is excluded
# for the same reason and matters more — it is how surah:ayah citations are written.
_PHONE_SEP = r"[  ‐-―\-()]"

# A *candidate*: the structure is checked here, the digit count in `_trim_phone`. The two
# openings are the whole precision argument — an international prefix, or a national trunk zero
# glued to a 2-3 digit area/mobile prefix (0300…, 021…, 042…). A bare digit run matches neither.
# No country code begins with 0, which is what keeps zero-padded identifiers (`0001-0002-…`) out
# of the international branch. The optional `(` is so that `(021) 34567890` does not leave a
# stray opening bracket behind in the corpus.
_PHONE_RE = re.compile(
    r"(?<![\d+])"
    r"(?:(?:\+|00)[1-9]\d{0,2}|\(?0\d{2,3})"
    rf"(?:{_PHONE_SEP}{{0,2}}\d{{1,6}}){{1,7}}"
    r"(?!\d)"
)

# Local part, then a domain with at least one real label and an alphabetic TLD. Requiring the
# TLD keeps `@handle` mentions and "Rs 500 @ 10.5%" out; requiring a character of the local class
# immediately before the `@` keeps every `@handle` out regardless of what follows it.
_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+\-])"
    r"[A-Za-z0-9._%+\-]{1,64}"
    r"@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.){1,4}"
    r"[A-Za-z]{2,24}"
    r"(?![A-Za-z0-9\-])"
)

_DIGIT_RUN_RE = re.compile(r"\d+")

# Longest shape recorded per match. Shapes are the log's adjudication instrument, and an
# unbounded key would let one 64-character local part bloat the manifest.
_MAX_SHAPE = 40


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PIIConfig:
    """Shipped defaults are the Ravaan corpus v1 settings; the fingerprint goes in the manifest.

    The digit bounds are dialling-plan facts, not tuning knobs. A Pakistani number written
    nationally is 10–12 digits including the trunk zero (``051-9201234`` is 10, ``0300-1234567``
    and ``021-99201234`` are 11, ``042-111-123-456`` is 12). Internationally the ``00``
    dialling prefix is the operator's rather than the subscriber's and is not counted; the range
    10–13 covers every country that plausibly appears in an Urdu corpus (+92, +91, +971, +966 and
    +44 are all 12–13, +1 is 11) against E.164's theoretical 7–15. The floor of 10 rather than 8
    is also measured: at 8 an ISBN-10 whose registration group begins ``00`` reads as an
    international number with eight subscriber digits, which is where Urdu Wikipedia's last two
    false positives came from.

    ``min_national_digits_unseparated`` is the one bound that came from reading corpus text
    rather than from a dialling plan, and it is the most load-bearing setting here. See
    ``reports/pii.md`` §3: an unhyphenated ISBN-10 in the English registration group is ten digits
    beginning with a zero, which is indistinguishable from a ten-digit landline written without
    separators. On Urdu Wikipedia that shape was **eleven of thirteen** phone matches. Requiring
    a separator below eleven digits removed all eleven and kept both genuine numbers, because
    people write phone numbers with separators and databases write identifiers without them.
    """

    redact_emails: bool = True
    redact_phones: bool = True
    email_placeholder: str = "[@]"
    phone_placeholder: str = "[#]"
    min_national_digits: int = 10
    min_national_digits_unseparated: int = 11
    max_national_digits: int = 12
    min_international_digits: int = 10
    max_international_digits: int = 13
    max_shapes: int = 200

    def __post_init__(self) -> None:
        for name in ("email_placeholder", "phone_placeholder"):
            _validate_placeholder(name, getattr(self, name))
        if not 0 < self.min_national_digits <= self.max_national_digits:
            raise ValueError("need 0 < min_national_digits <= max_national_digits")
        if not self.min_national_digits <= self.min_national_digits_unseparated:
            raise ValueError("need min_national_digits <= min_national_digits_unseparated")
        if not 0 < self.min_international_digits <= self.max_international_digits:
            raise ValueError("need 0 < min_international_digits <= max_international_digits")
        if self.max_shapes < 1:
            raise ValueError("max_shapes must be >= 1")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PIIConfig:
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known - {"pii_version", "_comment"}
        if unknown:
            raise ValueError(f"unknown pii config keys: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json_file(cls, path: str | Path) -> PIIConfig:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json_file(self, path: str | Path) -> None:
        payload = {"pii_version": PII_VERSION, **self.to_dict()}
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def fingerprint(self) -> str:
        """Short stable hash over version + settings, for the corpus manifest."""
        payload = json.dumps(
            {"version": PII_VERSION, **self.to_dict()}, sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _validate_placeholder(name: str, value: str) -> None:
    """The three properties module docstring §1 depends on, enforced rather than documented.

    Each rejection names a stage that would otherwise disagree with itself when re-run over the
    frozen corpus.
    """
    if not value:
        raise ValueError(f"{name} must not be empty")
    if any(ch.isalpha() for ch in value):
        raise ValueError(
            f"{name}={value!r} contains a letter: it would enter stage 3's letter counts and "
            f"stage 5's script_ratio denominator"
        )
    if any(ch.isdigit() for ch in value):
        raise ValueError(
            f"{name}={value!r} contains a digit: redaction would not be idempotent, because the "
            f"phone pattern can match a placeholder"
        )
    if "<" in value or ">" in value:
        raise ValueError(
            f"{name}={value!r} contains an angle bracket: stage 5 counts it as an HTML tag, so "
            f"re-running the quality filter over the frozen corpus would reject documents the "
            f"run that produced it kept"
        )


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------


def _shape(text: str) -> str:
    """``0300-1234567`` -> ``dddd-ddddddd``; ``a.b@gmail.com`` -> ``x.x@xxxxx.xxx``.

    Enough to tell a phone number from a date or an ISBN when adjudicating precision, and not
    enough to contact anybody. This is what gets written to reports.
    """
    out = []
    for ch in text[:_MAX_SHAPE]:
        if ch.isdigit():
            out.append("d")
        elif ch.isalpha():
            out.append("x")
        else:
            out.append(ch)
    if len(text) > _MAX_SHAPE:
        out.append("…")
    return "".join(out)


def _trim_phone(candidate: str, config: PIIConfig) -> int | None:
    """Length of the leading part of ``candidate`` that is a plausible number, or ``None``.

    Trailing digit groups are dropped one at a time while the count is over the maximum, so that
    ``"03001234567 03217654321"`` — two numbers the candidate pattern swallows as one, because a
    space is a legitimate separator — yields the first number rather than nothing. The scanner
    resumes after it and finds the second.
    """
    groups = [m.span() for m in _DIGIT_RUN_RE.finditer(candidate)]
    if not groups:
        return None

    opening = candidate.lstrip("(")
    international = opening.startswith("+") or opening.startswith("00")
    # The `00` international-dialling prefix is the operator's, not the subscriber's: `+92 300
    # 1234567` and `0092 300 1234567` are the same 12-digit number and must count the same.
    offset = 2 if opening.startswith("00") else 0
    low = config.min_international_digits if international else config.min_national_digits
    high = config.max_international_digits if international else config.max_national_digits

    kept = len(groups)
    while kept > 0:
        digits = sum(end - start for start, end in groups[:kept]) - offset
        if digits <= high:
            if digits < low:
                return None
            # An unseparated national run is the shape of an identifier as much as of a number,
            # and on Urdu Wikipedia it was overwhelmingly the identifier: unhyphenated ISBN-10s
            # are ten digits starting with a zero. People separate phone numbers; databases do
            # not. See PIIConfig's docstring and reports/pii.md §3.
            if (
                not international
                and kept == 1
                and digits < config.min_national_digits_unseparated
            ):
                return None
            return groups[kept - 1][1]
        kept -= 1
    return None


def _iter_phone_spans(
    text: str, config: PIIConfig, blocked: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Phone spans, skipping any that overlap an already-claimed span.

    ``blocked`` is the sorted list of email spans. Without it the digits inside
    ``0300123456@example.com`` would be redacted as a phone number *and* as an email, and the
    second replacement would land in the middle of the first.
    """
    spans: list[tuple[int, int]] = []
    pos = 0
    next_blocked = 0
    while True:
        match = _PHONE_RE.search(text, pos)
        if match is None:
            return spans
        start = match.start()

        while next_blocked < len(blocked) and blocked[next_blocked][1] <= start:
            next_blocked += 1

        length = _trim_phone(match.group(), config)
        if length is None:
            pos = start + 1
            continue
        end = start + length

        # Take the opening bracket only when the number's own closing bracket goes with it.
        # `(021) 34567890` should not leave a stray `(`, and `(0300-1234567)` should not lose its
        # opening bracket while keeping its closing one — the first version of this fixed the one
        # case by creating the other.
        if text[start] == "(" and ")" not in text[start:end]:
            start += 1

        if next_blocked < len(blocked) and blocked[next_blocked][0] < end:
            pos = blocked[next_blocked][1]
            continue

        spans.append((start, end))
        pos = end


def _find_spans(text: str, config: PIIConfig) -> list[tuple[int, int, str]]:
    """Every span to redact, sorted, non-overlapping. Emails are claimed first — see above."""
    emails: list[tuple[int, int]] = []
    if config.redact_emails:
        emails = [m.span() for m in _EMAIL_RE.finditer(text)]

    spans: list[tuple[int, int, str]] = [(s, e, "email") for s, e in emails]
    if config.redact_phones:
        spans += [(s, e, "phone") for s, e in _iter_phone_spans(text, config, emails)]
    spans.sort()
    return spans


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PIIMatch:
    """One redaction. Carries a shape, never the matched text — see module docstring §3."""

    category: str
    start: int
    end: int
    shape: str

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "start": self.start,
            "end": self.end,
            "shape": self.shape,
        }


@dataclass(frozen=True, slots=True)
class PIIResult:
    """Redacted text and what was replaced.

    There is deliberately **no** ``original`` field. Stage 4 keeps one because the PRD requires
    the transformation to be auditable; here the original *is* the personal data, and a result
    that carried it would put it into every log that serialises a result.
    """

    text: str
    matches: tuple[PIIMatch, ...] = ()
    chars_in: int = 0
    pii_version: str = PII_VERSION
    config_fingerprint: str = ""

    @property
    def changed(self) -> bool:
        return bool(self.matches)

    @property
    def counts(self) -> dict[str, int]:
        counts: Counter[str] = Counter(m.category for m in self.matches)
        return dict(sorted(counts.items()))

    def to_dict(self) -> dict:
        return {
            "counts": self.counts,
            "chars_in": self.chars_in,
            "chars_out": len(self.text),
            "shapes": sorted(Counter(m.shape for m in self.matches).items()),
            "pii_version": self.pii_version,
            "config_fingerprint": self.config_fingerprint,
        }


@dataclass
class PIILog:
    """Corpus-level aggregate, for the manifest and for ``reports/pii.md``."""

    config: PIIConfig = field(default_factory=PIIConfig)
    documents: int = 0
    documents_redacted: int = 0
    chars_in: int = 0
    chars_out: int = 0
    counts: Counter[str] = field(default_factory=Counter)
    shapes: Counter[str] = field(default_factory=Counter)
    shapes_dropped: int = 0

    def add(self, result: PIIResult) -> None:
        self.documents += 1
        self.documents_redacted += int(result.changed)
        self.chars_in += result.chars_in
        self.chars_out += len(result.text)
        for match in result.matches:
            self.counts[match.category] += 1
            key = f"{match.category}:{match.shape}"
            # Bounded: a corpus pass sees millions of documents and the shape alphabet is only
            # small in practice, never by construction.
            if key in self.shapes or len(self.shapes) < self.config.max_shapes:
                self.shapes[key] += 1
            else:
                self.shapes_dropped += 1

    def to_dict(self) -> dict:
        return {
            "pii_version": PII_VERSION,
            "config_fingerprint": self.config.fingerprint(),
            "config": self.config.to_dict(),
            "documents": self.documents,
            "documents_redacted": self.documents_redacted,
            "chars_in": self.chars_in,
            "chars_out": self.chars_out,
            "chars_removed": self.chars_in - self.chars_out,
            "counts": dict(sorted(self.counts.items())),
            "distinct_shapes": len(self.shapes),
            "shapes_dropped": self.shapes_dropped,
            "shapes": dict(self.shapes.most_common()),
        }


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = PIIConfig()


def _apply(text: str, spans: list[tuple[int, int, str]], config: PIIConfig) -> str:
    if not spans:
        return text
    out: list[str] = []
    last = 0
    for start, end, category in spans:
        out.append(text[last:start])
        out.append(config.email_placeholder if category == "email" else config.phone_placeholder)
        last = end
    out.append(text[last:])
    return "".join(out)


def redact_text(text: str, config: PIIConfig | None = None) -> str:
    """Fast path: redacted text only. Used for the full corpus run."""
    config = config or _DEFAULT_CONFIG
    return _apply(text, _find_spans(text, config), config)


def redact(text: str, config: PIIConfig | None = None) -> PIIResult:
    """Same output as :func:`redact_text`, plus a shape per match.

    Offsets are into the *input* text, so they stay meaningful when several matches are replaced
    by placeholders of a different length.
    """
    config = config or _DEFAULT_CONFIG
    spans = _find_spans(text, config)
    return PIIResult(
        text=_apply(text, spans, config),
        matches=tuple(
            PIIMatch(category=cat, start=s, end=e, shape=_shape(text[s:e])) for s, e, cat in spans
        ),
        chars_in=len(text),
        pii_version=PII_VERSION,
        config_fingerprint=config.fingerprint(),
    )


# ---------------------------------------------------------------------------
# CLI — redact a file, print the log to stderr
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    # Urdu, `→` and `×` on a Windows console are cp1252 by default, which raises rather than
    # mangles. Pin both streams before anything is printed.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("input", nargs="?", help="input file (default: stdin)")
    parser.add_argument("-o", "--output", help="output file (default: stdout)")
    parser.add_argument("-c", "--config", help="pii config JSON")
    parser.add_argument("--log", help="write the redaction log here as JSON")
    args = parser.parse_args(argv)

    config = PIIConfig.from_json_file(args.config) if args.config else PIIConfig()
    raw = (
        Path(args.input).read_text(encoding="utf-8")
        if args.input
        else sys.stdin.buffer.read().decode("utf-8")
    )

    result = redact(raw, config)
    log = PIILog(config=config)
    log.add(result)

    if args.output:
        # `newline="\n"`, never the platform default — see the same note in normalization.main.
        Path(args.output).write_text(result.text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.buffer.write(result.text.encode("utf-8"))

    payload = json.dumps(log.to_dict(), indent=2, ensure_ascii=False)
    if args.log:
        Path(args.log).write_text(payload + "\n", encoding="utf-8", newline="\n")
    else:
        print(payload, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
