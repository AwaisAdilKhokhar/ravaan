"""Encoding validation — stage 2 of the corpus pipeline (PRD §6.3.2).

Stage 2 sits between acquisition and language ID, and its job is narrow: decide whether a
document is *text at all* before anything downstream tries to reason about it as Urdu.

Three defects account for essentially all of it in Arabic-script web data:

1. **Not valid UTF-8.** Decoding is strict by default. A document that will not decode is
   rejected rather than patched, because `errors="replace"` converts a broken document into a
   plausible-looking one full of U+FFFD, and U+FFFD survives normalization, tokenizes to byte
   fallback, and quietly inflates the vocabulary.

2. **Mojibake** — UTF-8 bytes served with a Latin-1/cp1252 charset header, so `الع` arrives as
   `Ø§Ù„Ø¹`. This is *far* more damaging for Urdu than for English: every Arabic-script codepoint
   is a 2-byte UTF-8 sequence, so a mis-decoded Urdu page contains no Urdu characters at all.
   Stage 3 would score it as European text and drop it; stage 5's Urdu-script ratio would agree.
   The document is fully recoverable and would otherwise be thrown away, so it is worth repairing
   rather than merely detecting. Both the detection and the repair are the *same* byte-exact
   cp1252→UTF-8 round trip, never a guess: text is mojibake exactly when it re-encodes to
   well-formed UTF-8, and the repair is that re-encoding. See :func:`_mojibake_chars` for why
   anything weaker deletes real corpus — measured, it rejected 3% of clean Urdu Wikipedia.

3. **Replacement characters and control bytes** already baked into the source. These indicate an
   upstream decode that already went wrong, or binary content that was never text. Both are
   measured as rates and thresholded.

**Why control characters are stripped here and not in normalization.** Normalization (stage 4)
owns *script* decisions — which Urdu graphemes fold into which. C0/C1 control bytes are not
graphemes and carry no linguistic decision; they are a symptom of the byte layer. Left in place
they reach the tokenizer, where byte fallback dutifully allocates them tokens. `\t`, `\n` and `\r`
are excluded (real whitespace), as are `\v` and `\f`, which stage 4's whitespace rules already
understand.

**Order matters.** Mojibake is repaired *first*: U+0080–U+009F are C1 controls in correctly
decoded text but are the signature of mojibake in broken text, so measuring controls before
repairing would reject exactly the documents that are recoverable.

Entry points:

* :func:`validate_bytes` — from raw bytes (does the strict decode itself).
* :func:`validate_text`  — from an already-decoded ``str``, e.g. a parquet column.

Both return an :class:`EncodingResult`; :class:`EncodingLog` aggregates them for the manifest.
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

__all__ = [
    "ENCODING_VERSION",
    "DecodeErrorPolicy",
    "EncodingConfig",
    "EncodingResult",
    "EncodingLog",
    "Verdict",
    "validate_bytes",
    "validate_text",
    "repair_mojibake",
    "decode_sloppy_cp1252",
]

# Bump on any change to which documents are accepted or to the text they produce.
ENCODING_VERSION = "1.0.0"

REPLACEMENT_CHAR = "�"


# ---------------------------------------------------------------------------
# The cp1252 round trip
# ---------------------------------------------------------------------------


def _build_sloppy_cp1252() -> dict[str, int]:
    """Char → byte for a cp1252 that also accepts its own five undefined slots.

    Real-world mojibake was produced by decoders that did not raise on bytes 0x81, 0x8D, 0x8F,
    0x90 and 0x9D — cp1252 leaves those undefined, and browsers map them straight through to the
    matching C1 control. Strict `cp1252` would refuse to encode them, which would make exactly
    those documents unrepairable. Mapping them through is what makes the round trip byte-exact.
    """
    table: dict[str, int] = {}
    for b in range(256):
        try:
            ch = bytes([b]).decode("cp1252")
        except UnicodeDecodeError:
            ch = chr(b)
        table[ch] = b
    if len(table) != 256:
        raise AssertionError("sloppy cp1252 table is not injective")
    return table


_SLOPPY_CP1252 = _build_sloppy_cp1252()
_SLOPPY_CP1252_DECODE = {b: ch for ch, b in _SLOPPY_CP1252.items()}


def decode_sloppy_cp1252(raw: bytes) -> str:
    """Decode bytes the way the browsers that *created* mojibake did — never raising.

    Exact inverse of :func:`_encode_sloppy_cp1252`. Exported because it is how you construct a
    faithful mojibake fixture: Python's strict `cp1252` codec refuses byte 0x81, and 0x81 is the
    second byte of ہ (U+06C1), so `text.encode("utf-8").decode("cp1252")` raises on most real
    Urdu — the very documents this stage exists to recover.
    """
    return "".join(_SLOPPY_CP1252_DECODE[b] for b in raw)

# Exactly the characters that a byte >= 0x80 decodes to under sloppy cp1252 — i.e. every
# character a mojibake artefact can be made of, and nothing else. Derived from the table so
# there is one source of truth.
MOJIBAKE_ALPHABET = "".join(sorted(ch for ch, b in _SLOPPY_CP1252.items() if b >= 0x80))

# Candidate runs: two or more adjacent, since every multi-byte UTF-8 sequence is made entirely
# of bytes >= 0x80 and therefore lands entirely inside this alphabet. This is only a cheap
# pre-filter — see `_mojibake_chars` for why it cannot be the test itself.
_MOJIBAKE_RUN_RE = re.compile(f"[{re.escape(MOJIBAKE_ALPHABET)}]{{2,}}")

# Well-formed multi-byte UTF-8, as bytes (RFC 3629: no overlongs, no surrogates, capped at
# U+10FFFF). Mojibake *is* the property of round-tripping to valid UTF-8, so this is the
# definition rather than a proxy for it.
_UTF8_MULTIBYTE_RE = re.compile(
    rb"(?:[\xc2-\xdf][\x80-\xbf]"
    rb"|\xe0[\xa0-\xbf][\x80-\xbf]"
    rb"|[\xe1-\xec\xee\xef][\x80-\xbf]{2}"
    rb"|\xed[\x80-\x9f][\x80-\xbf]"
    rb"|\xf0[\x90-\xbf][\x80-\xbf]{2}"
    rb"|[\xf1-\xf3][\x80-\xbf]{3}"
    rb"|\xf4[\x80-\x8f][\x80-\xbf]{2})+"
)

# C0 and C1 controls, minus the whitespace that stages 4 understands (\t \n \r \v \f).
_CONTROL_RE = re.compile("[\x00-\x08\x0e-\x1f\x7f-\x9f]")


def _encode_sloppy_cp1252(text: str) -> bytes | None:
    """Reverse the mis-decode. ``None`` when the text contains anything cp1252 cannot hold."""
    try:
        return text.encode("cp1252")
    except UnicodeEncodeError:
        pass
    try:
        return bytes(_SLOPPY_CP1252[ch] for ch in text)
    except KeyError:
        # A character outside cp1252 entirely — real Urdu, say. Not whole-document mojibake.
        return None


def _mojibake_chars(text: str) -> int:
    """Characters that re-encode to a well-formed multi-byte UTF-8 sequence — i.e. real mojibake.

    An earlier version counted any run of two or more characters from :data:`MOJIBAKE_ALPHABET`.
    Measured against 20,000 Urdu Wikipedia articles that rejected **3% of a clean corpus**, and
    the flagged runs say exactly why: ``‘‘`` and ``’’`` (Urdu Wikipedia's own quotation marks,
    4,460 hits), runs of U+00A0 used as layout padding, ``——————`` rules, ``\\xa0–``, and
    Portuguese ``çã``. All are ordinary text. None of them re-encodes to valid UTF-8 — ``‘‘`` is
    bytes 0x91 0x91, two bare continuation bytes.

    So the round trip is not a repair strategy applied after detection; it *is* the detection.
    The run regex survives only as a cheap pre-filter, because most documents match nothing and
    the byte-level scan is not free.
    """
    if _MOJIBAKE_RUN_RE.search(text) is None:
        return 0
    total = 0
    for run in _MOJIBAKE_RUN_RE.findall(text):
        raw = _encode_sloppy_cp1252(run)
        if raw is None:  # pragma: no cover — every alphabet char encodes by construction
            continue
        # One byte per character here, so a matched byte count is a matched character count.
        total += sum(len(m) for m in _UTF8_MULTIBYTE_RE.findall(raw))
    return total


def _repair_once(text: str) -> str | None:
    """One round trip: re-encode as cp1252, decode as UTF-8. ``None`` if that is not what it is.

    This is not a heuristic rewrite. Either the bytes round-trip exactly and yield valid UTF-8,
    or nothing is returned; there is no partial or best-effort repair.
    """
    raw = _encode_sloppy_cp1252(text)
    if raw is None:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def repair_mojibake(text: str, max_passes: int = 3) -> tuple[str, int]:
    """Repair UTF-8-decoded-as-cp1252 text, iterating for the double-encoded case.

    Returns ``(text, passes_applied)``. A pass is kept only if it strictly reduces the mojibake
    character count and introduces no replacement characters, so text that merely contains
    accented Latin is left alone.
    """
    passes = 0
    score = _mojibake_chars(text)
    while passes < max_passes and score:
        candidate = _repair_once(text)
        if candidate is None or REPLACEMENT_CHAR in candidate:
            break
        candidate_score = _mojibake_chars(candidate)
        if candidate_score >= score:
            break
        text, score = candidate, candidate_score
        passes += 1
    return text, passes


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DecodeErrorPolicy = Literal["reject", "replace"]

Verdict = Literal[
    "ok",  # decoded cleanly, nothing above threshold
    "repaired",  # was mojibake, round-tripped back, accepted
    "undecodable",  # strict UTF-8 decode failed
    "mojibake",  # mojibake detected and *not* repairable — reject
    "replacement_heavy",  # too many U+FFFD already in the source
    "control_heavy",  # too many control bytes — probably not text
]

ACCEPTED_VERDICTS: frozenset[str] = frozenset({"ok", "repaired"})


@dataclass(frozen=True, slots=True)
class EncodingConfig:
    """Thresholds for stage 2. Defaults are the Ravaan corpus v1 settings.

    The rates are deliberately tight. This stage runs before quality filtering, so anything it
    lets through is a document some later stage has to reason about; a document with 1 U+FFFD in
    1,000 characters has already lost information no downstream stage can recover.
    """

    strict_utf8: bool = True
    on_decode_error: DecodeErrorPolicy = "reject"
    strip_bom: bool = True
    repair_mojibake: bool = True
    max_repair_passes: int = 3
    max_mojibake_rate: float = 0.001
    max_replacement_rate: float = 0.001
    strip_control_chars: bool = True
    max_control_rate: float = 0.001

    def __post_init__(self) -> None:
        if self.on_decode_error not in ("reject", "replace"):
            raise ValueError(
                f"on_decode_error must be 'reject' or 'replace', got {self.on_decode_error!r}"
            )
        if self.max_repair_passes < 1:
            raise ValueError("max_repair_passes must be >= 1")
        for name in ("max_mojibake_rate", "max_replacement_rate", "max_control_rate"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value!r}")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> EncodingConfig:
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known - {"encoding_version", "_comment"}
        if unknown:
            raise ValueError(f"unknown encoding config keys: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json_file(cls, path: str | Path) -> EncodingConfig:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json_file(self, path: str | Path) -> None:
        payload = {"encoding_version": ENCODING_VERSION, **self.to_dict()}
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def fingerprint(self) -> str:
        """Short stable hash over version + settings, for the corpus manifest."""
        payload = json.dumps(
            {"version": ENCODING_VERSION, **self.to_dict()}, sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EncodingResult:
    """One document's verdict, with the counts the manifest needs to justify it."""

    verdict: Verdict
    text: str | None
    chars: int = 0
    bytes_in: int = 0
    replacement_chars: int = 0
    mojibake_chars: int = 0
    control_chars: int = 0
    repair_passes: int = 0
    decode_error: str | None = None
    encoding_version: str = ENCODING_VERSION
    config_fingerprint: str = ""

    @property
    def accepted(self) -> bool:
        return self.verdict in ACCEPTED_VERDICTS

    def _rate(self, count: int) -> float:
        return count / self.chars if self.chars else 0.0

    @property
    def replacement_rate(self) -> float:
        return self._rate(self.replacement_chars)

    @property
    def mojibake_rate(self) -> float:
        return self._rate(self.mojibake_chars)

    @property
    def control_rate(self) -> float:
        return self._rate(self.control_chars)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "accepted": self.accepted,
            "chars": self.chars,
            "bytes_in": self.bytes_in,
            "replacement_chars": self.replacement_chars,
            "mojibake_chars": self.mojibake_chars,
            "control_chars": self.control_chars,
            "repair_passes": self.repair_passes,
            "decode_error": self.decode_error,
            "encoding_version": self.encoding_version,
            "config_fingerprint": self.config_fingerprint,
        }


@dataclass
class EncodingLog:
    """Corpus-level aggregate. Feeds the manifest and the stage-2 line of the statistics table."""

    config: EncodingConfig = field(default_factory=EncodingConfig)
    documents: int = 0
    documents_accepted: int = 0
    documents_repaired: int = 0
    bytes_in: int = 0
    chars_out: int = 0
    verdicts: Counter[str] = field(default_factory=Counter)
    replacement_chars: int = 0
    mojibake_chars: int = 0
    control_chars: int = 0

    def add(self, result: EncodingResult) -> None:
        self.documents += 1
        self.verdicts[result.verdict] += 1
        self.bytes_in += result.bytes_in
        self.replacement_chars += result.replacement_chars
        self.mojibake_chars += result.mojibake_chars
        self.control_chars += result.control_chars
        if result.accepted:
            self.documents_accepted += 1
            self.chars_out += result.chars
        if result.repair_passes:
            self.documents_repaired += 1

    @property
    def acceptance_rate(self) -> float:
        return self.documents_accepted / self.documents if self.documents else 0.0

    def to_dict(self) -> dict:
        return {
            "encoding_version": ENCODING_VERSION,
            "config_fingerprint": self.config.fingerprint(),
            "config": self.config.to_dict(),
            "documents": self.documents,
            "documents_accepted": self.documents_accepted,
            "documents_rejected": self.documents - self.documents_accepted,
            "documents_repaired": self.documents_repaired,
            "acceptance_rate": round(self.acceptance_rate, 6),
            "bytes_in": self.bytes_in,
            "chars_out": self.chars_out,
            "replacement_chars": self.replacement_chars,
            "mojibake_chars": self.mojibake_chars,
            "control_chars": self.control_chars,
            "verdicts": dict(sorted(self.verdicts.items())),
        }


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = EncodingConfig()


@lru_cache(maxsize=16)
def _fingerprint(config: EncodingConfig) -> str:
    return config.fingerprint()


def _reject(verdict: Verdict, config: EncodingConfig, **counts: object) -> EncodingResult:
    return EncodingResult(
        verdict=verdict, text=None, config_fingerprint=_fingerprint(config), **counts
    )


def validate_bytes(raw: bytes, config: EncodingConfig | None = None) -> EncodingResult:
    """Strict-decode and validate a document held as raw bytes."""
    config = config or _DEFAULT_CONFIG

    if config.strip_bom and raw.startswith(codecs.BOM_UTF8):
        raw = raw[len(codecs.BOM_UTF8) :]

    errors = "strict" if config.strict_utf8 else "replace"
    try:
        text = raw.decode("utf-8", errors=errors)
    except UnicodeDecodeError as exc:
        if config.on_decode_error == "reject":
            return _reject(
                "undecodable",
                config,
                bytes_in=len(raw),
                decode_error=f"{exc.reason} at byte {exc.start}",
            )
        text = raw.decode("utf-8", errors="replace")

    return _validate(text, config, bytes_in=len(raw))


def validate_text(text: str, config: EncodingConfig | None = None) -> EncodingResult:
    """Validate an already-decoded document — a parquet string column, say.

    The decode already happened somewhere else, so `undecodable` is not reachable here; the
    mojibake, replacement and control checks all still apply.
    """
    return _validate(text, config or _DEFAULT_CONFIG, bytes_in=len(text.encode("utf-8")))


def _validate(text: str, config: EncodingConfig, *, bytes_in: int) -> EncodingResult:
    # 1. Mojibake, before anything else — U+0080–U+009F are its signature, and would otherwise
    #    be counted as control bytes and get the document rejected.
    mojibake = _mojibake_chars(text)
    passes = 0
    if mojibake and config.repair_mojibake:
        text, passes = repair_mojibake(text, config.max_repair_passes)
        if passes:
            mojibake = _mojibake_chars(text)

    chars = len(text)
    counts: dict[str, object] = {"chars": chars, "bytes_in": bytes_in, "mojibake_chars": mojibake}

    if chars and mojibake / chars > config.max_mojibake_rate:
        return _reject("mojibake", config, repair_passes=passes, **counts)

    # 2. Replacement characters — either present in the source or introduced by a `replace` decode.
    replacements = text.count(REPLACEMENT_CHAR)
    counts["replacement_chars"] = replacements
    if chars and replacements / chars > config.max_replacement_rate:
        return _reject("replacement_heavy", config, repair_passes=passes, **counts)

    # 3. Control bytes. Cheap early exit: most documents have none.
    controls = len(_CONTROL_RE.findall(text)) if _CONTROL_RE.search(text) else 0
    counts["control_chars"] = controls
    if chars and controls / chars > config.max_control_rate:
        return _reject("control_heavy", config, repair_passes=passes, **counts)
    if controls and config.strip_control_chars:
        text = _CONTROL_RE.sub("", text)
        counts["chars"] = len(text)

    return EncodingResult(
        verdict="repaired" if passes else "ok",
        text=text,
        repair_passes=passes,
        config_fingerprint=_fingerprint(config),
        **counts,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# CLI — validate a file or a JSONL corpus shard, print the log to stderr
# ---------------------------------------------------------------------------


def _iter_documents(raw: bytes, jsonl: bool, field_name: str):
    """Yield ``(bytes, passthrough_record)`` pairs. One document, or one per JSONL line."""
    if not jsonl:
        yield raw, None
        return
    for line in raw.split(b"\n"):
        if not line.strip():
            continue
        record = json.loads(line)
        if field_name not in record:
            raise KeyError(f"JSONL record has no field {field_name!r}")
        yield record[field_name].encode("utf-8"), record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("input", nargs="?", help="input file (default: stdin)")
    parser.add_argument("-o", "--output", help="accepted documents (default: stdout)")
    parser.add_argument("-c", "--config", help="encoding config JSON")
    parser.add_argument("--log", help="write the stage-2 log here as JSON")
    parser.add_argument("--jsonl", action="store_true", help="one JSON document per line")
    parser.add_argument("--field", default="text", help="JSONL text field (default: text)")
    args = parser.parse_args(argv)

    config = EncodingConfig.from_json_file(args.config) if args.config else EncodingConfig()
    raw = Path(args.input).read_bytes() if args.input else sys.stdin.buffer.read()

    log = EncodingLog(config=config)
    out: list[bytes] = []
    for chunk, record in _iter_documents(raw, args.jsonl, args.field):
        result = validate_bytes(chunk, config)
        log.add(result)
        if not result.accepted:
            continue
        if record is None:
            out.append(result.text.encode("utf-8"))  # type: ignore[union-attr]
        else:
            record[args.field] = result.text
            out.append(json.dumps(record, ensure_ascii=False).encode("utf-8"))

    payload = b"\n".join(out)
    if args.jsonl and payload:
        payload += b"\n"
    if args.output:
        Path(args.output).write_bytes(payload)
    else:
        sys.stdout.buffer.write(payload)

    report = json.dumps(log.to_dict(), indent=2, ensure_ascii=False)
    if args.log:
        Path(args.log).write_text(report + "\n", encoding="utf-8", newline="\n")
    else:
        print(report, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
