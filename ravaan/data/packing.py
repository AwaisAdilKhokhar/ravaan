"""Tokenization and sequence packing — stage 10 of the corpus pipeline (PRD §6.3.10).

The last pipeline stage, and the one that turns every estimate upstream into a count. Stage 9
budgets in tokens and can only measure characters (§7's tokenizer is Week 5, the freeze is Weeks
3–4); this stage is where tokens finally exist, so it owes stage 9 a measured fertility and owes
§8.3 the byte counts that make bits-per-byte computable.

**Sequences never span populations, and that is a §8.3 requirement rather than tidiness.** §8.3
reports validation BPB *by script*. A sequence built from Urdu Wikipedia and Roman-Urdu-Parl
sentences has no script, so the metric would not be defined on it — and the aggregate would move
with the mixture rather than with the model, which is the same failure stage 9 avoids by carving
held-out at the arm mixture. Within a population, documents *are* concatenated: Roman-Urdu-Parl
rows are single sentences averaging ~18 tokens, so one-document-per-sequence would be 97% padding.

**Each arm is packed independently.** Arm A's documents are a subset of arm B's (stage 9 makes
that structural), but arm A's *sequences* are not a subset of arm B's, and must not be. Taking
arm A as a prefix of arm B's packed stream would make it a contiguous block of the corpus — Finding
E's defect, arriving one stage after stage 9 spent its whole design avoiding it. §6.1 requires the
arms to share *documents*; each arm is its own training set and packs its own.

**No padding, anywhere except a dropped tail.** §4.3's arithmetic is ``396 × 25M = 9.9B tokens
processed`` and compute is ``C = 6ND`` over exactly that D. A padding token costs compute and
carries no data, so a padded corpus makes the epoch count and the unique-token budget mean two
different things — Finding A's error in miniature. The final partial sequence of each stream is
therefore dropped and counted, never padded: at most 511 tokens per stream against a 100M budget,
and an undershoot, which is the same direction stage 9's band solve errs in for the same reason.

**A separator is a token and is counted as one.** Documents are joined with EOS. On native Urdu
that is ~0.2% of the stream; on Roman-Urdu-Parl's sentence-length rows it is ~5%, which is large
enough that a fertility measured on content alone would put stage 9's Roman band 5% over budget.
The fertility this stage reports back is therefore *effective* — characters per token including
separators — because that is the ratio that makes the arm budgets land.

**The corpus names the instrument that produced it.** Every shard sidecar carries the tokenizer's
id and fingerprint, and :class:`PackedWriter` refuses to write with a placeholder tokenizer unless
told to in as many words. The licence gate of stage 1 is the precedent: a check made once during
planning and then trusted is a check that drifts, and "which tokenizer is this corpus in" is not a
question a frozen artifact should leave to memory.

Written with the same dependency rule as the rest of the deciding stages: standard library only.
``sentencepiece`` is needed to *load* §7's model, never to decide anything about the corpus.
"""

from __future__ import annotations

import hashlib
import json
import sys
from array import array
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

PACKING_VERSION = "1"

# uint16 holds a 16,384-entry vocabulary (§5) exactly and halves the corpus on disk. The width is
# checked against the vocabulary rather than assumed — an id past the dtype wraps silently, which
# would corrupt the corpus in a way no later stage could see.
_DTYPES: dict[str, tuple[str, int]] = {"uint16": ("H", 1 << 16), "uint32": ("I", 1 << 32)}

PLACEHOLDER_PREFIX = "placeholder:"


# ---------------------------------------------------------------------------
# The tokenizer boundary
# ---------------------------------------------------------------------------


@runtime_checkable
class Tokenizer(Protocol):
    """What stage 10 needs from §7's tokenizer, and nothing more.

    Narrow on purpose. The tokenizer is trained in Week 5, one week after the freeze, so this
    stage has to be built and tested against something that does not exist yet. A protocol makes
    the seam explicit; ``tokenizer_id`` makes it impossible for a corpus to forget which side of
    the seam it was written on.
    """

    @property
    def tokenizer_id(self) -> str:
        """Stable name. Prefixed ``placeholder:`` if this cannot produce a freezable corpus."""

    @property
    def vocab_size(self) -> int: ...

    @property
    def eos_id(self) -> int: ...

    def fingerprint(self) -> str:
        """Hash of the model that produced the ids. Goes in the shard sidecar and the manifest."""

    def encode(self, text: str) -> list[int]: ...


class ByteTokenizer:
    """A stand-in so stage 10 is testable and runnable before §7 exists — and only that.

    Encodes UTF-8 bytes, so its fertility is *not* Urdu's: every Arabic-script codepoint is two
    bytes, giving ~0.5 characters per token against the ~3.5 a 16k SentencePiece model is expected
    to reach. Any number measured with it describes this class, not the corpus.

    That is why the id carries ``placeholder:`` and why :class:`PackedWriter` refuses it by
    default. A placeholder whose output is indistinguishable from the real thing is worse than no
    placeholder — it is Finding D's shape, a component that passes every test it has and is wrong
    about the corpus.
    """

    def __init__(self, *, eos_id: int = 256) -> None:
        if not 0 <= eos_id < 512:
            raise ValueError(f"eos_id must be inside this tokenizer's range, got {eos_id}")
        self._eos = eos_id

    @property
    def tokenizer_id(self) -> str:
        return f"{PLACEHOLDER_PREFIX}utf8-bytes"

    @property
    def vocab_size(self) -> int:
        return 257

    @property
    def eos_id(self) -> int:
        return self._eos

    def fingerprint(self) -> str:
        return hashlib.blake2b(self.tokenizer_id.encode(), digest_size=8).hexdigest()

    def encode(self, text: str) -> list[int]:
        return list(text.encode("utf-8"))


class SentencePieceTokenizer:
    """§7's model, once it exists. Imports ``sentencepiece`` lazily — the ``[tokenizer]`` extra.

    Loaded from a file path so the fingerprint is of the bytes that actually produced the ids,
    not of a name that could be pointed at a different model next week.
    """

    def __init__(self, model_path: str | Path, *, eos_id: int | None = None) -> None:
        try:
            import sentencepiece  # noqa: PLC0415  (optional dependency, by design)
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise ImportError(
                "SentencePieceTokenizer needs the [tokenizer] extra: pip install -e '.[tokenizer]'"
            ) from exc
        self._path = Path(model_path)
        raw = self._path.read_bytes()
        self._digest = hashlib.sha256(raw).hexdigest()
        self._sp = sentencepiece.SentencePieceProcessor(model_file=str(self._path))
        self._eos = self._sp.eos_id() if eos_id is None else eos_id
        if not 0 <= self._eos < self._sp.get_piece_size():
            raise ValueError(
                f"eos_id {self._eos} is outside the model's vocabulary of "
                f"{self._sp.get_piece_size()} — a separator the model cannot emit is not a "
                "separator, and every document boundary in the corpus would be one"
            )

    @property
    def tokenizer_id(self) -> str:
        return f"sentencepiece:{self._path.name}"

    @property
    def vocab_size(self) -> int:
        return int(self._sp.get_piece_size())

    @property
    def eos_id(self) -> int:
        return int(self._eos)

    def fingerprint(self) -> str:
        return self._digest[:16]

    def encode(self, text: str) -> list[int]:
        return list(self._sp.encode(text, out_type=int))


def is_placeholder(tokenizer: Tokenizer) -> bool:
    return tokenizer.tokenizer_id.startswith(PLACEHOLDER_PREFIX)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PackingConfig:
    """Everything about the packed corpus that is a choice rather than a measurement."""

    # §5: context length 512, vocabulary 16,384. Both models, both arms, every seed.
    sequence_length: int = 512
    vocab_size: int = 16_384

    dtype: str = "uint16"

    # Documents are joined inside a population and never across one. See the module docstring:
    # the first is a 97%-padding argument, the second is what makes §8.3's per-script BPB defined.
    cross_document: bool = True

    # Sequences per output shard. 20,000 x 512 x 2 bytes = ~20 MB, small enough to checksum and
    # re-fetch individually and large enough that a 100M-token arm is ~10 files rather than 400.
    shard_sequences: int = 20_000

    # Marks the stage in the fingerprint. Re-packing under a different rule must not be able to
    # produce a corpus that claims to be this one.
    salt: str = "ravaan/pack/v1"

    def __post_init__(self) -> None:
        if self.sequence_length < 2:
            raise ValueError(
                f"sequence_length must be >= 2, got {self.sequence_length} — a one-token "
                "sequence has no context to predict from"
            )
        if self.vocab_size < 2:
            raise ValueError(f"vocab_size must be >= 2, got {self.vocab_size}")
        if self.dtype not in _DTYPES:
            raise ValueError(f"dtype must be one of {sorted(_DTYPES)}, got {self.dtype!r}")
        if self.vocab_size > _DTYPES[self.dtype][1]:
            raise ValueError(
                f"vocab_size {self.vocab_size} does not fit in {self.dtype} — ids past the width "
                "wrap silently, which corrupts the corpus in a way no later stage can detect"
            )
        if self.shard_sequences < 1:
            raise ValueError(f"shard_sequences must be >= 1, got {self.shard_sequences}")
        if not self.salt:
            raise ValueError("salt must be set — an unnamed packing is not reproducible")

    @property
    def typecode(self) -> str:
        return _DTYPES[self.dtype][0]

    @property
    def bytes_per_token(self) -> int:
        return array(self.typecode).itemsize

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PackingConfig:
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known - {"packing_version", "_comment"}
        if unknown:
            raise ValueError(f"unknown packing config keys: {sorted(unknown)}")
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def from_json_file(cls, path: str | Path) -> PackingConfig:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_json_file(self, path: str | Path) -> None:
        payload = {"packing_version": PACKING_VERSION, **self.to_dict()}
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",  # session 4: Path.write_text translates \n to os.linesep otherwise
        )

    def fingerprint(self) -> str:
        payload = json.dumps(
            {"packing_version": PACKING_VERSION, **self.to_dict()}, sort_keys=True
        )
        return hashlib.blake2b(payload.encode(), digest_size=8).hexdigest()


# ---------------------------------------------------------------------------
# Sequences
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Sequence:
    """One packed training sequence.

    ``text_bytes`` is not decoration. §8.3 reports **bits-per-byte**, so every evaluated sequence
    needs the byte count of the text its tokens stand for, and §4.5's paired bootstrap resamples
    *sequences* — so the count has to be per sequence, not a corpus total. Separators stand for no
    text and contribute none.
    """

    tokens: tuple[int, ...]
    text_bytes: int
    documents: int
    separators: int

    @property
    def content_tokens(self) -> int:
        return len(self.tokens) - self.separators


def _attribute_bytes(total_bytes: int, total_tokens: int, taken: int, already: int) -> int:
    """Bytes attributable to ``taken`` of a document's tokens, given ``already`` handed out.

    Integer arithmetic that sums to ``total_bytes`` exactly across the whole document however it
    is cut. A document split across a sequence boundary is the only place the attribution is an
    approximation at all, and the totals — which is what BPB is computed from — stay exact.

    §7 requires stable offset mappings; when they exist this becomes a lookup rather than a
    proportion, and the per-sequence numbers get exact too.
    """
    if total_tokens <= 0:
        return 0
    end = (total_bytes * (already + taken)) // total_tokens
    start = (total_bytes * already) // total_tokens
    return end - start


class SequencePacker:
    """Concatenates a stream of documents into fixed-length sequences.

    One packer per stream, where a stream is a (population, split) pair — and, for training data,
    a (population, split, arm) triple. Nothing crosses a population boundary and nothing crosses
    an arm boundary; see the module docstring for why each of those is a requirement rather than a
    preference.
    """

    def __init__(self, config: PackingConfig, tokenizer: Tokenizer) -> None:
        self.config = config
        self.tokenizer = tokenizer
        if tokenizer.eos_id >= tokenizer.vocab_size:
            raise ValueError(
                f"eos_id {tokenizer.eos_id} is outside the tokenizer's vocabulary of "
                f"{tokenizer.vocab_size}"
            )
        if tokenizer.vocab_size > config.vocab_size:
            raise ValueError(
                f"tokenizer vocabulary {tokenizer.vocab_size} exceeds the configured "
                f"{config.vocab_size} — §5 fixes the vocabulary for both models and every seed, "
                "so a corpus that quietly used a larger one is not the corpus the design specifies"
            )
        self._buffer: list[int] = []
        self._bytes = 0
        self._documents = 0
        self._separators = 0
        self.dropped_tokens = 0
        self.dropped_bytes = 0
        # Everything the tokenizer produced, separators included, whether or not it reached a
        # shard. Fertility is measured against this and never against what was written: the two
        # differ by the dropped tail, and a ratio whose numerator and denominator are counted over
        # different sets of documents is the defect Findings O, P and S were each an instance of.
        self.encoded_tokens = 0

    # --- state, so a long pass survives being resumed ----------------------

    def state(self) -> dict:
        return {
            "buffer": list(self._buffer),
            "bytes": self._bytes,
            "documents": self._documents,
            "separators": self._separators,
            "dropped_tokens": self.dropped_tokens,
            "dropped_bytes": self.dropped_bytes,
            "encoded_tokens": self.encoded_tokens,
        }

    def load_state(self, state: dict) -> None:
        """Restore a partial sequence.

        Without this a resumed pass restarts its buffer at empty, which shifts every subsequent
        sequence boundary — the corpus would still be valid and would not be the corpus the
        checkpoint claims to continue. Stage 9's ``resume()`` refuses a mismatched plan for the
        same reason: a pass that silently produces different output is worse than one that failed.
        """
        self._buffer = list(state["buffer"])
        self._bytes = int(state["bytes"])
        self._documents = int(state["documents"])
        self._separators = int(state["separators"])
        self.dropped_tokens = int(state.get("dropped_tokens", 0))
        self.dropped_bytes = int(state.get("dropped_bytes", 0))
        self.encoded_tokens = int(state.get("encoded_tokens", 0))

    # --- packing ------------------------------------------------------------

    def add(self, text: str) -> Iterator[Sequence]:
        """Tokenize one document and yield every sequence it completes."""
        ids = self.tokenizer.encode(text)
        if not ids:
            return
        self._check_ids(ids)
        ids = [*ids, self.tokenizer.eos_id]
        total_bytes = len(text.encode("utf-8"))
        total_tokens = len(ids)
        self.encoded_tokens += total_tokens

        if not self.config.cross_document:
            self._drop_partial()

        handed = 0
        self._documents += 1
        while handed < total_tokens:
            room = self.config.sequence_length - len(self._buffer)
            take = min(room, total_tokens - handed)
            self._buffer.extend(ids[handed : handed + take])
            self._bytes += _attribute_bytes(total_bytes, total_tokens, take, handed)
            # The EOS is the last id, so the chunk that contains it carries exactly one separator.
            if handed + take == total_tokens:
                self._separators += 1
            handed += take
            if len(self._buffer) == self.config.sequence_length:
                yield self._emit(continues=handed < total_tokens)

    def _emit(self, *, continues: bool) -> Sequence:
        sequence = Sequence(
            tokens=tuple(self._buffer),
            text_bytes=self._bytes,
            documents=self._documents,
            separators=self._separators,
        )
        self._buffer = []
        self._bytes = 0
        self._separators = 0
        # A document straddling the boundary is already counted in the sequence it started in.
        # It still occupies the next one, so it is counted there too — the per-sequence figure is
        # "documents with text in this sequence", which is what a reader of the manifest wants.
        self._documents = 1 if continues else 0
        return sequence

    def _drop_partial(self) -> None:
        """Drop, never pad. See the module docstring — a pad token costs compute and is not data."""
        if not self._buffer:
            return
        self.dropped_tokens += len(self._buffer)
        self.dropped_bytes += self._bytes
        self._buffer = []
        self._bytes = 0
        self._documents = 0
        self._separators = 0

    def finish(self) -> None:
        """End the stream. The residual partial sequence is dropped and counted, never padded."""
        self._drop_partial()

    def _check_ids(self, ids: Iterable[int]) -> None:
        limit = self.config.vocab_size
        for token in ids:
            if not 0 <= token < limit:
                raise ValueError(
                    f"token id {token} is outside the configured vocabulary of {limit} — writing "
                    f"it as {self.config.dtype} would wrap it to a different, entirely valid-"
                    "looking token, and no later stage could tell"
                )


# ---------------------------------------------------------------------------
# On-disk shards
# ---------------------------------------------------------------------------


@dataclass
class ShardRecord:
    """One written shard, as it appears in the corpus manifest."""

    path: str
    stream: str
    population: str
    split: str
    arm: str | None
    sequences: int
    tokens: int
    text_bytes: int
    separators: int
    sha256: str

    def to_dict(self) -> dict:
        return asdict(self)


class PackedWriter:
    """Writes packed sequences as a flat little-endian token array plus a JSON sidecar.

    Two properties worth naming.

    **Byte order is pinned, not inherited.** ``array`` is native-endian, so a corpus written on a
    big-endian machine and read on a little-endian one would decode to entirely different, entirely
    valid token ids — a silent corruption with no symptom until the loss curve. Every shard is
    byte-swapped to little-endian on write if it has to be, and the sidecar says so.

    **The sidecar names the tokenizer.** A packed corpus is unreadable without knowing which
    tokenizer produced the ids, and "we know which one" is not a property that survives a month.
    """

    def __init__(
        self,
        root: str | Path,
        config: PackingConfig,
        tokenizer: Tokenizer,
        *,
        allow_placeholder: bool = False,
    ) -> None:
        if is_placeholder(tokenizer) and not allow_placeholder:
            raise ValueError(
                f"{tokenizer.tokenizer_id} is a placeholder and cannot produce a freezable "
                "corpus — its fertility is a property of the placeholder, not of Urdu. Pass "
                "allow_placeholder=True (CLI: --allow-placeholder) to write a throwaway corpus "
                "for plumbing checks, and re-pack when §7's tokenizer is frozen in Week 5"
            )
        self.root = Path(root)
        self.config = config
        self.tokenizer = tokenizer
        self.allow_placeholder = allow_placeholder
        self.shards: list[ShardRecord] = []
        self._open: dict[str, list[Sequence]] = {}
        self._counts: Counter[str] = Counter()

    def add(self, stream: str, sequence: Sequence) -> None:
        buffer = self._open.setdefault(stream, [])
        buffer.append(sequence)
        if len(buffer) >= self.config.shard_sequences:
            self.flush(stream)

    def flush(self, stream: str) -> ShardRecord | None:
        buffer = self._open.get(stream)
        if not buffer:
            return None
        index = self._counts[stream]
        self._counts[stream] += 1
        population, split, arm = parse_stream(stream)
        name = f"{stream.replace('/', '_')}_{index:05d}"
        directory = self.root / stream
        directory.mkdir(parents=True, exist_ok=True)

        tokens = array(self.config.typecode)
        lengths = array("I")
        for sequence in buffer:
            tokens.extend(sequence.tokens)
            lengths.append(sequence.text_bytes)
        if sys.byteorder != "little":  # pragma: no cover - CI and the operator are little-endian
            tokens.byteswap()
            lengths.byteswap()

        bin_path = directory / f"{name}.bin"
        bytes_path = directory / f"{name}.bytes"
        _write_bytes(bin_path, tokens.tobytes())
        _write_bytes(bytes_path, lengths.tobytes())

        record = ShardRecord(
            path=str(bin_path.relative_to(self.root)).replace("\\", "/"),
            stream=stream,
            population=population,
            split=split,
            arm=arm,
            sequences=len(buffer),
            tokens=sum(len(s.tokens) for s in buffer),
            text_bytes=sum(s.text_bytes for s in buffer),
            separators=sum(s.separators for s in buffer),
            sha256=hashlib.sha256(bin_path.read_bytes()).hexdigest(),
        )
        self.shards.append(record)
        self._open[stream] = []
        return record

    def close(self) -> list[ShardRecord]:
        for stream in list(self._open):
            self.flush(stream)
        return self.shards

    def manifest(self, log: PackingLog | None = None) -> dict:
        payload: dict = {
            "packing_version": PACKING_VERSION,
            "config": {"packing_version": PACKING_VERSION, **self.config.to_dict()},
            "config_fingerprint": self.config.fingerprint(),
            "tokenizer": {
                "id": self.tokenizer.tokenizer_id,
                "fingerprint": self.tokenizer.fingerprint(),
                "vocab_size": self.tokenizer.vocab_size,
                "eos_id": self.tokenizer.eos_id,
                "placeholder": is_placeholder(self.tokenizer),
            },
            "layout": {
                "dtype": self.config.dtype,
                "byte_order": "little",
                "sequence_length": self.config.sequence_length,
                "sidecar": ".bytes is one uint32 per sequence: UTF-8 bytes of the text its "
                "tokens stand for, which is BPB's denominator (§8.3)",
            },
            "shards": [s.to_dict() for s in sorted(self.shards, key=lambda s: s.path)],
        }
        if log is not None:
            payload["log"] = log.to_dict()
        return payload

    def write_manifest(self, path: str | Path, log: PackingLog | None = None) -> dict:
        payload = self.manifest(log)
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return payload


def _write_bytes(path: Path, payload: bytes) -> None:
    """Write via a ``.part`` file and rename, so an interrupted run leaves no half shard.

    Stage 1 takes the same precaution for downloads and for the same reason: a truncated file that
    looks complete to the next stage is the failure that costs a whole pass to notice.
    """
    part = path.with_suffix(path.suffix + ".part")
    part.write_bytes(payload)
    part.replace(path)


def stream_name(population: str, split: str, arm: str | None = None) -> str:
    """``urdu/validation`` for held-out, ``urdu/train/A`` for an arm's training data.

    Held-out is not arm-scoped: stage 9 carves one validation and one test set shared by both
    arms, because §4.3's endpoint compares the A and B curves and two sets would make that a
    comparison of numbers computed on different data.
    """
    return f"{population}/{split}" if arm is None else f"{population}/{split}/{arm}"


def parse_stream(stream: str) -> tuple[str, str, str | None]:
    parts = stream.split("/")
    if len(parts) == 2:
        return parts[0], parts[1], None
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    raise ValueError(f"not a stream name: {stream!r}")


def read_shard(path: str | Path, config: PackingConfig) -> list[tuple[int, ...]]:
    """Read a shard back. Used by the tests, and by anything that wants to audit the corpus."""
    tokens = array(config.typecode)
    tokens.frombytes(Path(path).read_bytes())
    if sys.byteorder != "little":  # pragma: no cover
        tokens.byteswap()
    length = config.sequence_length
    if len(tokens) % length:
        raise ValueError(
            f"{path} holds {len(tokens)} tokens, not a multiple of the {length}-token sequence "
            "length — the shard is truncated or was written under a different config"
        )
    return [tuple(tokens[i : i + length]) for i in range(0, len(tokens), length)]


def read_sequence_bytes(path: str | Path) -> list[int]:
    """Read a ``.bytes`` sidecar — one uint32 per sequence, BPB's denominator."""
    lengths = array("I")
    lengths.frombytes(Path(path).read_bytes())
    if sys.byteorder != "little":  # pragma: no cover
        lengths.byteswap()
    return list(lengths)


# ---------------------------------------------------------------------------
# The log
# ---------------------------------------------------------------------------


@dataclass
class PackingLog:
    """Corpus-level counts, and the measured fertility stage 9 has been waiting on."""

    config: PackingConfig = field(default_factory=PackingConfig)
    tokenizer_id: str = ""
    tokenizer_fingerprint: str = ""
    sample_rate: float | None = None

    documents: Counter[str] = field(default_factory=Counter)  # by stream
    sequences: Counter[str] = field(default_factory=Counter)
    # `tokens` is what reached a shard; `encoded_tokens` is everything the tokenizer produced.
    # They differ by the dropped tail. Corpus size is the first; fertility is the second, because
    # only it is counted over the same documents as `chars`.
    tokens: Counter[str] = field(default_factory=Counter)
    encoded_tokens: Counter[str] = field(default_factory=Counter)
    separators: Counter[str] = field(default_factory=Counter)
    text_bytes: Counter[str] = field(default_factory=Counter)
    # Characters, so the ratio stage 9 budgets in can be computed directly rather than inferred
    # from bytes. Urdu is 2 bytes per character in UTF-8 and Roman Urdu is 1, so the two are not
    # interchangeable across populations — which is exactly where a single ratio would go wrong.
    chars: Counter[str] = field(default_factory=Counter)
    dropped_tokens: Counter[str] = field(default_factory=Counter)
    dropped_bytes: Counter[str] = field(default_factory=Counter)
    empty_documents: Counter[str] = field(default_factory=Counter)

    def _by_population(self, counter: Counter[str], population: str) -> int:
        return sum(v for k, v in counter.items() if k.split("/", 1)[0] == population)

    @property
    def populations(self) -> tuple[str, ...]:
        return tuple(sorted({k.split("/", 1)[0] for k in self.encoded_tokens}))

    def chars_per_token(self, population: str) -> float:
        """The number stage 9 estimated and this stage counts.

        **Effective**, i.e. separators included in the denominator. Stage 9's band budgets are in
        tokens and every token in a packed stream costs compute, so a ratio computed on content
        alone would put the Roman-Urdu-Parl band ~5% over its budget — the population where
        document-length is a single sentence and the separator share is largest.

        Measured against encoded tokens, so numerator and denominator cover the same documents.
        """
        tokens = self._by_population(self.encoded_tokens, population)
        return self._by_population(self.chars, population) / tokens if tokens else 0.0

    def bytes_per_token(self, population: str) -> float:
        """Bytes per token. §8.3's BPB is a ratio of these two quantities, so it is worth a number.

        Not derivable from ``chars_per_token``: Urdu is 2 UTF-8 bytes per character and Roman
        Urdu is 1, so the two ratios differ by ~2× between populations that sit in one corpus.
        """
        tokens = self._by_population(self.tokens, population)
        return self._by_population(self.text_bytes, population) / tokens if tokens else 0.0

    def separator_share(self, population: str) -> float:
        """Share of the stream that is document separators rather than text.

        Counted as one EOS per encoded document rather than from the written shards, so it pairs
        with ``encoded_tokens``. ~0.2% on native Urdu; ~5% on Roman-Urdu-Parl, whose documents are
        single sentences — which is why the fertility handed back to stage 9 includes it.
        """
        tokens = self._by_population(self.encoded_tokens, population)
        return self._by_population(self.documents, population) / tokens if tokens else 0.0

    def measured_chars_per_token(self) -> dict[str, float]:
        """Ready to hand to ``SplitConfig(chars_per_token=...)`` and re-solve stage 9's plan."""
        return {p: round(self.chars_per_token(p), 4) for p in self.populations}

    def fertility_report(self) -> dict:
        """Measured against configured, per population — the estimate this stage retires.

        A sampled pass measures this honestly: characters-per-token is a ratio of two per-document
        sums, so a sample estimates it at rate *r* in both numerator and denominator. That is
        Finding G's test — the quantity is a property of one document, not of a *pair* — and it is
        the reason this one number can be measured cheaply when stages 6 and 7 could not be.
        """
        return {
            population: {
                "chars_per_token_measured": round(self.chars_per_token(population), 4),
                "bytes_per_token_measured": round(self.bytes_per_token(population), 4),
                "separator_share": round(self.separator_share(population), 5),
                "encoded_tokens": self._by_population(self.encoded_tokens, population),
                "written_tokens": self._by_population(self.tokens, population),
                "chars": self._by_population(self.chars, population),
                "documents": self._by_population(self.documents, population),
            }
            for population in self.populations
        }

    def to_dict(self) -> dict:
        streams = sorted(set(self.encoded_tokens) | set(self.documents))
        return {
            "packing_version": PACKING_VERSION,
            "config_fingerprint": self.config.fingerprint(),
            "tokenizer_id": self.tokenizer_id,
            "tokenizer_fingerprint": self.tokenizer_fingerprint,
            "sample_rate": self.sample_rate,
            "totals": {
                "documents": sum(self.documents.values()),
                "sequences": sum(self.sequences.values()),
                "tokens_written": sum(self.tokens.values()),
                "tokens_encoded": sum(self.encoded_tokens.values()),
                "separators": sum(self.separators.values()),
                "text_bytes": sum(self.text_bytes.values()),
                "dropped_tokens": sum(self.dropped_tokens.values()),
                "empty_documents": sum(self.empty_documents.values()),
            },
            "fertility": self.fertility_report(),
            "measured_chars_per_token": self.measured_chars_per_token(),
            "streams": {
                stream: {
                    "documents": self.documents[stream],
                    "sequences": self.sequences[stream],
                    "tokens_written": self.tokens[stream],
                    "tokens_encoded": self.encoded_tokens[stream],
                    "chars": self.chars[stream],
                    "separators": self.separators[stream],
                    "text_bytes": self.text_bytes[stream],
                    "dropped_tokens": self.dropped_tokens[stream],
                }
                for stream in streams
            },
        }


# ---------------------------------------------------------------------------
# The driver
# ---------------------------------------------------------------------------


class CorpusPacker:
    """Routes documents into per-stream packers and keeps the log.

    Stage 9 hands each document a population, a split and a tuple of arms. A training document in
    arm A is also in arm B, so it is packed into both arms' streams — the arms are two training
    sets that share documents, not one stream with a marker.
    """

    def __init__(
        self,
        config: PackingConfig | None = None,
        tokenizer: Tokenizer | None = None,
        *,
        sample_rate: float | None = None,
    ) -> None:
        self.config = config or PackingConfig()
        self.tokenizer = tokenizer or ByteTokenizer()
        if sample_rate is not None and not 0.0 < sample_rate <= 1.0:
            raise ValueError(f"sample_rate must be in (0, 1], got {sample_rate!r}")
        self.sample_rate = sample_rate if sample_rate != 1.0 else None
        self.log = PackingLog(
            config=self.config,
            tokenizer_id=self.tokenizer.tokenizer_id,
            tokenizer_fingerprint=self.tokenizer.fingerprint(),
            sample_rate=self.sample_rate,
        )
        self._packers: dict[str, SequencePacker] = {}

    def packer(self, stream: str) -> SequencePacker:
        if stream not in self._packers:
            self._packers[stream] = SequencePacker(self.config, self.tokenizer)
        return self._packers[stream]

    def add(
        self,
        text: str,
        population: str,
        split: str,
        arms: Iterable[str] = (),
    ) -> Iterator[tuple[str, Sequence]]:
        """Pack one document into every stream it belongs to."""
        if split == "unassigned":
            return
        arms = tuple(arms)
        targets = (
            [stream_name(population, split, arm) for arm in arms]
            if split == "train"
            else [stream_name(population, split)]
        )
        if split == "train" and not arms:
            # In no arm and not held out: stage 9 measured it, budgeted it, and neither arm's cut
            # reached it. It is corpus, not training data, and packing it would silently raise U.
            return
        if not text:
            for stream in targets:
                self.log.empty_documents[stream] += 1
            return
        chars = len(text)
        for stream in targets:
            packer = self.packer(stream)
            before = packer.encoded_tokens
            # Counted per emitted sequence rather than per document: a document's tokens are
            # spread over however many sequences it straddles, and the per-sequence byte counts
            # are what §8.3's BPB and §4.5's bootstrap read.
            for sequence in packer.add(text):
                self.log.sequences[stream] += 1
                self.log.tokens[stream] += len(sequence.tokens)
                self.log.separators[stream] += sequence.separators
                self.log.text_bytes[stream] += sequence.text_bytes
                yield stream, sequence
            encoded = packer.encoded_tokens - before
            if not encoded:
                # Non-empty text that tokenizes to nothing — whitespace a SentencePiece model
                # drops. Counting its characters against zero tokens would bias the fertility
                # this stage hands back to stage 9, and the bias would be in the safe-looking
                # direction: more characters per token, so larger bands, so an arm over budget.
                self.log.empty_documents[stream] += 1
                continue
            self.log.documents[stream] += 1
            self.log.chars[stream] += chars
            self.log.encoded_tokens[stream] += encoded

    def finish(self) -> None:
        """Close every stream. Residual partial sequences are dropped and counted."""
        for stream, packer in self._packers.items():
            packer.finish()
            self.log.dropped_tokens[stream] += packer.dropped_tokens
            self.log.dropped_bytes[stream] += packer.dropped_bytes

    def state(self) -> dict:
        """Checkpoint every open partial sequence, so a resumed pass produces the same corpus."""
        return {
            "packing_version": PACKING_VERSION,
            "config_fingerprint": self.config.fingerprint(),
            "tokenizer_fingerprint": self.tokenizer.fingerprint(),
            "packers": {stream: p.state() for stream, p in self._packers.items()},
        }

    def load_state(self, state: dict) -> None:
        if state.get("config_fingerprint") != self.config.fingerprint():
            raise ValueError(
                "this checkpoint was written under a different packing config — resuming would "
                "splice two corpora together and the result would be neither"
            )
        if state.get("tokenizer_fingerprint") != self.tokenizer.fingerprint():
            raise ValueError(
                "this checkpoint was written with a different tokenizer — the buffered partial "
                "sequence holds ids from a vocabulary this run does not have"
            )
        for stream, packer_state in state.get("packers", {}).items():
            self.packer(stream).load_state(packer_state)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_corpus(manifest_path: str | Path, root: str | Path | None = None) -> dict:
    """Check a packed corpus against its own manifest, shard by shard.

    PRD §6.3's release policy ships "code, manifest, checksums and statistics" and no raw text, so
    the manifest is the only thing a reader can check the corpus against — which makes checking it
    something the pipeline should do rather than describe. Four properties, because each can fail
    independently: the digest (the bytes), the length (a truncated shard), the sequence count (a
    shard written under a different sequence length), and the byte sidecar (§8.3's BPB denominator,
    which is the one nothing downstream would notice was wrong).
    """
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = Path(root) if root is not None else manifest_path.parent
    config = PackingConfig.from_dict(manifest["config"])

    problems: list[str] = []
    sequences = tokens = text_bytes = 0
    for record in manifest["shards"]:
        path = base / record["path"]
        if not path.exists():
            problems.append(f"{record['path']}: missing")
            continue
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != record["sha256"]:
            problems.append(f"{record['path']}: digest mismatch")
        expected = record["sequences"] * config.sequence_length * config.bytes_per_token
        if len(raw) != expected:
            problems.append(f"{record['path']}: {len(raw)} bytes, expected {expected}")
        sidecar = path.with_suffix(".bytes")
        if not sidecar.exists():
            problems.append(f"{record['path']}: no .bytes sidecar — BPB is not computable")
        else:
            lengths = read_sequence_bytes(sidecar)
            if len(lengths) != record["sequences"]:
                problems.append(
                    f"{record['path']}: {len(lengths)} byte counts for "
                    f"{record['sequences']} sequences"
                )
            elif sum(lengths) != record["text_bytes"]:
                problems.append(
                    f"{record['path']}: byte counts sum to {sum(lengths)}, "
                    f"manifest says {record['text_bytes']}"
                )
        sequences += record["sequences"]
        tokens += record["tokens"]
        text_bytes += record["text_bytes"]

    return {
        "manifest": str(manifest_path),
        "shards": len(manifest["shards"]),
        "sequences": sequences,
        "tokens": tokens,
        "text_bytes": text_bytes,
        "tokenizer": manifest.get("tokenizer", {}),
        "problems": problems,
        "ok": not problems,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse  # noqa: PLC0415

    # Windows picks cp1252 for a redirected stdout. Session 12 lost every run of
    # `scripts/crossover.py` to exactly this — the fourth platform-default bug in this repo — and
    # the failure is that a character outside cp1252 raises rather than mangles.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Verify a packed corpus against its manifest.")
    parser.add_argument("manifest", help="corpus manifest written by scripts/pack.py")
    parser.add_argument("--root", help="shard root, if not the manifest's directory")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = parser.parse_args(argv)

    result = verify_corpus(args.manifest, args.root)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["ok"] else 1

    tokenizer = result["tokenizer"]
    print(
        f"{result['shards']:,} shards  {result['sequences']:,} sequences  "
        f"{result['tokens']:,} tokens"
    )
    print(f"tokenizer: {tokenizer.get('id', '?')} ({tokenizer.get('fingerprint', '?')})")
    if tokenizer.get("placeholder"):
        print("  WARNING: written with a placeholder tokenizer — not a freezable corpus")
    for problem in result["problems"]:
        print(f"  FAIL {problem}")
    print("OK" if result["ok"] else f"{len(result['problems'])} problems")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
