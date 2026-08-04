"""Stage 10 — tokenization and sequence packing (PRD §6.3.10)."""

from __future__ import annotations

import json
from array import array

import pytest

from ravaan.data.packing import (
    PACKING_VERSION,
    ByteTokenizer,
    CorpusPacker,
    PackedWriter,
    PackingConfig,
    PackingLog,
    SequencePacker,
    is_placeholder,
    parse_stream,
    read_sequence_bytes,
    read_shard,
    stream_name,
    verify_corpus,
)
from ravaan.data.packing import main as packing_main


class FixedTokenizer:
    """One token per character, so a test can count tokens by counting characters."""

    def __init__(self, *, vocab_size: int = 16_384, eos_id: int = 2) -> None:
        self._vocab = vocab_size
        self._eos = eos_id

    tokenizer_id = "test:fixed"

    @property
    def vocab_size(self) -> int:
        return self._vocab

    @property
    def eos_id(self) -> int:
        return self._eos

    def fingerprint(self) -> str:
        return "fixed"

    def encode(self, text: str) -> list[int]:
        return [(ord(c) % (self._vocab - 3)) + 3 for c in text]


def small_config(**kwargs) -> PackingConfig:
    return PackingConfig(**{"sequence_length": 8, "shard_sequences": 4, **kwargs})


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_a_vocabulary_that_does_not_fit_the_dtype_is_refused():
    """An id past the width wraps to a different, entirely valid-looking token."""
    with pytest.raises(ValueError, match="does not fit"):
        PackingConfig(vocab_size=70_000, dtype="uint16")
    PackingConfig(vocab_size=70_000, dtype="uint32")  # fits, so allowed


def test_the_shipped_config_matches_the_code_defaults():
    """Same guard the other stages carry: the file and the dataclass cannot drift apart."""
    shipped = PackingConfig.from_json_file("configs/data/packing.json")
    assert shipped == PackingConfig()


def test_the_shipped_config_matches_the_model_specification():
    """§5 fixes both numbers for both models, both arms and every seed."""
    shipped = PackingConfig.from_json_file("configs/data/packing.json")
    assert shipped.sequence_length == 512
    assert shipped.vocab_size == 16_384


def test_an_unknown_config_key_is_refused():
    with pytest.raises(ValueError, match="unknown packing config keys"):
        PackingConfig.from_dict({"sequence_length": 512, "pad_id": 0})


def test_the_fingerprint_moves_with_a_packing_decision():
    base = PackingConfig()
    assert base.fingerprint() != PackingConfig(cross_document=False).fingerprint()
    assert base.fingerprint() != PackingConfig(sequence_length=1024).fingerprint()


def test_config_round_trips_through_json(tmp_path):
    path = tmp_path / "packing.json"
    PackingConfig(sequence_length=256).to_json_file(path)
    assert PackingConfig.from_json_file(path) == PackingConfig(sequence_length=256)
    assert json.loads(path.read_text(encoding="utf-8"))["packing_version"] == PACKING_VERSION


def test_written_config_has_no_carriage_returns(tmp_path):
    """Session 4's bug, kept fixed: Path.write_text translates \\n to os.linesep by default."""
    path = tmp_path / "packing.json"
    PackingConfig().to_json_file(path)
    assert b"\r" not in path.read_bytes()


# ---------------------------------------------------------------------------
# Packing
# ---------------------------------------------------------------------------


def test_sequences_are_exactly_the_configured_length():
    packer = SequencePacker(small_config(), FixedTokenizer())
    sequences = [s for _ in range(20) for s in packer.add("abcdefgh")]
    assert sequences
    assert all(len(s.tokens) == 8 for s in sequences)


def test_documents_are_joined_by_a_separator():
    packer = SequencePacker(small_config(), FixedTokenizer(eos_id=2))
    sequences = [s for text in ("abc", "def") for s in packer.add(text)]
    # "abc" + EOS + "def" + EOS = 8 tokens = one full sequence
    assert len(sequences) == 1
    assert sequences[0].tokens.count(2) == 2
    assert sequences[0].separators == 2
    assert sequences[0].documents == 2


def test_nothing_is_padded_and_the_tail_is_dropped_and_counted():
    """§4.3 counts tokens processed as data. A pad token costs compute and is not data."""
    packer = SequencePacker(small_config(), FixedTokenizer())
    sequences = list(packer.add("abcdefghij"))  # 10 chars + EOS = 11 tokens
    assert len(sequences) == 1  # 8 written, 3 left over
    packer.finish()
    assert packer.dropped_tokens == 3
    assert all(len(s.tokens) == 8 for s in sequences)


def test_a_document_longer_than_a_sequence_spans_several():
    packer = SequencePacker(small_config(), FixedTokenizer())
    sequences = list(packer.add("a" * 23))  # 23 + EOS = 24 = three sequences exactly
    assert len(sequences) == 3
    assert sum(s.separators for s in sequences) == 1  # only the last chunk carries the EOS


def test_cross_document_off_gives_one_document_per_sequence():
    packer = SequencePacker(small_config(cross_document=False), FixedTokenizer())
    sequences = [s for text in ("abcdefghij", "klm") for s in packer.add(text)]
    assert all(s.documents == 1 for s in sequences)


def test_an_out_of_range_token_is_a_hard_error():
    """Silently wrapping to a valid-looking id is the failure no later stage can detect."""

    class Rogue(FixedTokenizer):
        def encode(self, text: str) -> list[int]:
            return [99_999]

    packer = SequencePacker(small_config(), Rogue())
    with pytest.raises(ValueError, match="outside the configured vocabulary"):
        list(packer.add("a"))


def test_a_tokenizer_larger_than_the_configured_vocabulary_is_refused():
    """§5 fixes the vocabulary. A corpus that quietly used a bigger one is a different design."""
    with pytest.raises(ValueError, match="exceeds the configured"):
        SequencePacker(small_config(vocab_size=256), FixedTokenizer(vocab_size=16_384))


def test_an_eos_outside_the_vocabulary_is_refused():
    with pytest.raises(ValueError, match="outside the tokenizer's vocabulary"):
        SequencePacker(small_config(), FixedTokenizer(vocab_size=16, eos_id=99))


# ---------------------------------------------------------------------------
# Bytes — §8.3's BPB denominator
# ---------------------------------------------------------------------------


def test_attributed_bytes_sum_to_the_documents_own_byte_count():
    """BPB is NLL / bytes. If the attribution leaked, every reported BPB would be wrong."""
    packer = SequencePacker(small_config(), FixedTokenizer())
    text = "ا" * 30  # 2 UTF-8 bytes each
    sequences = list(packer.add(text))
    packer.finish()
    assert sum(s.text_bytes for s in sequences) + packer.dropped_bytes == len(text.encode("utf-8"))


def test_separators_stand_for_no_bytes():
    packer = SequencePacker(PackingConfig(sequence_length=4), FixedTokenizer())
    sequences = list(packer.add("abc"))  # 3 chars + EOS = one full 4-token sequence
    assert len(sequences) == 1
    assert sequences[0].text_bytes == 3
    assert sequences[0].content_tokens == 3


def test_bytes_per_token_differs_between_scripts():
    """Urdu is 2 UTF-8 bytes a character and Roman Urdu is 1, so one ratio cannot serve both."""
    packer = CorpusPacker(small_config(), FixedTokenizer())
    list(packer.add("ا" * 40, "urdu", "validation"))
    list(packer.add("a" * 40, "roman_urdu", "validation"))
    packer.finish()
    assert packer.log.bytes_per_token("urdu") > 1.8
    assert packer.log.bytes_per_token("roman_urdu") < 1.2


# ---------------------------------------------------------------------------
# Streams — populations and arms
# ---------------------------------------------------------------------------


def test_sequences_never_cross_a_population_boundary():
    """§8.3 reports BPB *by script*. A mixed-script sequence has no script to report it under."""
    packer = CorpusPacker(small_config(), FixedTokenizer())
    emitted = list(packer.add("abcd", "urdu", "validation"))
    emitted += list(packer.add("efgh", "roman_urdu", "validation"))
    packer.finish()
    assert {stream for stream, _ in emitted} <= {"urdu/validation", "roman_urdu/validation"}
    assert packer.log.encoded_tokens["urdu/validation"] == 5  # 4 chars + EOS
    assert packer.log.encoded_tokens["roman_urdu/validation"] == 5


def test_an_arm_a_document_is_packed_into_both_arms():
    """Arm A ⊆ arm B in *documents*. They are two training sets, not one stream with a marker."""
    packer = CorpusPacker(small_config(), FixedTokenizer())
    list(packer.add("abcdefgh", "urdu", "train", ("A", "B")))
    packer.finish()
    assert packer.log.documents["urdu/train/A"] == 1
    assert packer.log.documents["urdu/train/B"] == 1


def test_arm_streams_are_packed_independently():
    """Arm A's sequences must not be a prefix of arm B's — that would make it a contiguous block.

    Finding E's defect, arriving one stage after stage 9 spent its whole design avoiding it.
    """
    packer = CorpusPacker(small_config(), FixedTokenizer())
    list(packer.add("a" * 8, "urdu", "train", ("B",)))  # arm B only
    shared = list(packer.add("b" * 8, "urdu", "train", ("A", "B")))
    packer.finish()
    by_stream: dict[str, list] = {}
    for stream, sequence in shared:
        by_stream.setdefault(stream, []).append(sequence)
    # Arm A's sequence starts at the shared document; arm B's is still finishing the one before.
    assert by_stream["urdu/train/A"][0].tokens != by_stream["urdu/train/B"][0].tokens


def test_held_out_is_not_arm_scoped():
    """One validation and one test set shared by both arms — §4.3 compares the A and B curves."""
    packer = CorpusPacker(small_config(), FixedTokenizer())
    list(packer.add("abcdefgh", "urdu", "validation", ("A", "B")))
    packer.finish()
    assert set(packer.log.documents) == {"urdu/validation"}


def test_an_unassigned_document_is_not_packed():
    packer = CorpusPacker(small_config(), FixedTokenizer())
    assert list(packer.add("abcdefgh", "urdu", "unassigned")) == []
    packer.finish()
    assert not packer.log.documents


def test_a_training_document_in_no_arm_is_not_packed():
    """Stage 9 measured and budgeted it and neither cut reached it. Packing it would raise U."""
    packer = CorpusPacker(small_config(), FixedTokenizer())
    assert list(packer.add("abcdefgh", "urdu", "train", ())) == []
    packer.finish()
    assert not packer.log.documents


def test_stream_names_round_trip():
    assert parse_stream(stream_name("urdu", "validation")) == ("urdu", "validation", None)
    assert parse_stream(stream_name("urdu", "train", "A")) == ("urdu", "train", "A")
    with pytest.raises(ValueError, match="not a stream name"):
        parse_stream("urdu")


# ---------------------------------------------------------------------------
# Fertility — the estimate stage 9 has been carrying
# ---------------------------------------------------------------------------


def test_fertility_is_measured_against_encoded_tokens_not_written_ones():
    """The two differ by the dropped tail. A ratio over different sets is Finding O's shape."""
    packer = CorpusPacker(small_config(), FixedTokenizer())
    list(packer.add("a" * 10, "urdu", "validation"))  # 11 tokens encoded, 8 written
    packer.finish()
    assert packer.log.encoded_tokens["urdu/validation"] == 11
    assert packer.log.tokens["urdu/validation"] == 8
    assert packer.log.chars_per_token("urdu") == pytest.approx(10 / 11)


def test_the_separator_share_is_large_on_sentence_length_documents():
    """~5% on Roman-Urdu-Parl rows against ~0.2% on native Urdu — the reason it is in the ratio."""
    sentences = CorpusPacker(small_config(), FixedTokenizer())
    for _ in range(50):
        list(sentences.add("a" * 18, "roman_urdu", "validation"))
    sentences.finish()

    articles = CorpusPacker(small_config(), FixedTokenizer())
    for _ in range(5):
        list(articles.add("a" * 500, "urdu", "validation"))
    articles.finish()

    assert sentences.log.separator_share("roman_urdu") > 0.05
    assert articles.log.separator_share("urdu") < 0.005


def test_a_document_that_tokenizes_to_nothing_does_not_bias_the_fertility():
    """Its characters against zero tokens would inflate chars/token, so bands would come out big."""

    class DropsWhitespace(FixedTokenizer):
        def encode(self, text: str) -> list[int]:
            return super().encode(text.strip())

    packer = CorpusPacker(small_config(), DropsWhitespace())
    list(packer.add("aaaa", "urdu", "validation"))
    list(packer.add("    ", "urdu", "validation"))
    packer.finish()
    assert packer.log.documents["urdu/validation"] == 1
    assert packer.log.empty_documents["urdu/validation"] == 1
    assert packer.log.chars_per_token("urdu") == pytest.approx(4 / 5)


def test_measured_chars_per_token_is_shaped_for_stage_nine():
    packer = CorpusPacker(small_config(), FixedTokenizer())
    list(packer.add("a" * 40, "urdu", "validation"))
    packer.finish()
    from ravaan.data.splits import SplitConfig  # noqa: PLC0415

    measured = packer.log.measured_chars_per_token()
    assert set(measured) == {"urdu"}
    # It is accepted straight into stage 9's config, which is the whole point of the shape.
    SplitConfig(
        population_targets={"urdu": 100},
        chars_per_token={"urdu": measured["urdu"]},
    )


def test_a_sampled_pass_measures_the_same_fertility():
    """Fertility is a per-document ratio, so a sample estimates it honestly — Finding G's test."""
    documents = [f"{'a' * (10 + i % 40)}" for i in range(400)]

    full = CorpusPacker(small_config(), FixedTokenizer())
    for text in documents:
        list(full.add(text, "urdu", "validation"))
    full.finish()

    sampled = CorpusPacker(small_config(), FixedTokenizer(), sample_rate=0.1)
    for text in documents[::10]:
        list(sampled.add(text, "urdu", "validation"))
    sampled.finish()

    assert sampled.log.chars_per_token("urdu") == pytest.approx(
        full.log.chars_per_token("urdu"), rel=0.02
    )


# ---------------------------------------------------------------------------
# The tokenizer boundary
# ---------------------------------------------------------------------------


def test_the_placeholder_says_so_in_its_id():
    assert is_placeholder(ByteTokenizer())
    assert not is_placeholder(FixedTokenizer())


def test_the_writer_refuses_a_placeholder_by_default(tmp_path):
    """Its fertility is a property of UTF-8, not of Urdu, so it cannot produce a freeze."""
    with pytest.raises(ValueError, match="placeholder"):
        PackedWriter(tmp_path, small_config(), ByteTokenizer())
    PackedWriter(tmp_path, small_config(), ByteTokenizer(), allow_placeholder=True)


def test_the_byte_tokenizer_encodes_utf8():
    assert ByteTokenizer().encode("ا") == [216, 167]


# ---------------------------------------------------------------------------
# On disk
# ---------------------------------------------------------------------------


def _write(tmp_path, texts, config=None):
    config = config or small_config()
    tokenizer = FixedTokenizer()
    packer = CorpusPacker(config, tokenizer)
    writer = PackedWriter(tmp_path, config, tokenizer)
    for text in texts:
        for stream, sequence in packer.add(text, "urdu", "validation"):
            writer.add(stream, sequence)
    packer.finish()
    writer.close()
    return packer, writer, config


def test_a_shard_round_trips_through_disk(tmp_path):
    packer, writer, config = _write(tmp_path, ["a" * 40])
    assert writer.shards
    read = read_shard(tmp_path / writer.shards[0].path, config)
    assert all(len(seq) == config.sequence_length for seq in read)
    assert sum(len(seq) for seq in read) == writer.shards[0].tokens


def test_the_byte_sidecar_has_one_entry_per_sequence(tmp_path):
    """§4.5's paired bootstrap resamples sequences, so the byte count has to be per sequence."""
    _, writer, _ = _write(tmp_path, ["a" * 100])
    record = writer.shards[0]
    sidecar = (tmp_path / record.path).with_suffix(".bytes")
    lengths = read_sequence_bytes(sidecar)
    assert len(lengths) == record.sequences
    assert sum(lengths) == record.text_bytes


def test_shards_are_written_little_endian(tmp_path):
    """A corpus written big-endian and read little-endian decodes to valid, different tokens."""
    _, writer, config = _write(tmp_path, ["abcdefgh" * 5])
    raw = (tmp_path / writer.shards[0].path).read_bytes()
    expected = array(config.typecode)
    expected.frombytes(raw)
    assert json.loads(json.dumps(writer.manifest()))["layout"]["byte_order"] == "little"
    assert len(raw) == len(expected) * config.bytes_per_token


def test_the_manifest_names_the_tokenizer(tmp_path):
    """A packed corpus is unreadable without knowing which tokenizer produced the ids."""
    _, writer, _ = _write(tmp_path, ["a" * 40])
    manifest = writer.manifest()
    assert manifest["tokenizer"]["id"] == "test:fixed"
    assert manifest["tokenizer"]["placeholder"] is False
    assert manifest["config_fingerprint"]


def test_every_shard_carries_its_digest(tmp_path):
    import hashlib  # noqa: PLC0415

    _, writer, _ = _write(tmp_path, ["a" * 200])
    for record in writer.shards:
        actual = hashlib.sha256((tmp_path / record.path).read_bytes()).hexdigest()
        assert record.sha256 == actual


def test_a_shard_is_split_at_the_configured_size(tmp_path):
    _, writer, config = _write(tmp_path, ["a" * 400])
    assert len(writer.shards) > 1
    assert all(s.sequences <= config.shard_sequences for s in writer.shards)


def test_no_part_files_survive_a_completed_write(tmp_path):
    _write(tmp_path, ["a" * 200])
    assert not list(tmp_path.rglob("*.part"))


def test_a_truncated_shard_is_refused_rather_than_read_short(tmp_path):
    _, writer, config = _write(tmp_path, ["a" * 200])
    path = tmp_path / writer.shards[0].path
    path.write_bytes(path.read_bytes()[:-4])
    with pytest.raises(ValueError, match="not a multiple"):
        read_shard(path, config)


def test_the_manifest_round_trips_and_writes_lf(tmp_path):
    _, writer, _ = _write(tmp_path, ["a" * 40])
    path = tmp_path / "corpus.json"
    writer.write_manifest(path, PackingLog())
    assert b"\r" not in path.read_bytes()
    assert json.loads(path.read_text(encoding="utf-8"))["packing_version"] == PACKING_VERSION


# ---------------------------------------------------------------------------
# Determinism and resumption
# ---------------------------------------------------------------------------


def test_the_same_documents_produce_byte_identical_shards(tmp_path):
    """§8.1 makes bit-identical determinism an invariant. The corpus is the first thing under it."""
    texts = [f"{'ab' * (i % 17 + 1)}" for i in range(60)]
    _, first, _ = _write(tmp_path / "one", texts)
    _, second, _ = _write(tmp_path / "two", texts)
    assert [s.sha256 for s in first.shards] == [s.sha256 for s in second.shards]


def test_a_resumed_pass_produces_the_same_sequences():
    """Without the carried buffer every subsequent boundary shifts, silently."""
    texts = [f"{'ab' * (i % 11 + 1)}" for i in range(40)]

    whole = CorpusPacker(small_config(), FixedTokenizer())
    expected = [seq.tokens for text in texts for _, seq in whole.add(text, "urdu", "train", ("A",))]

    first = CorpusPacker(small_config(), FixedTokenizer())
    got = [seq.tokens for text in texts[:17] for _, seq in first.add(text, "urdu", "train", ("A",))]
    state = json.loads(json.dumps(first.state()))

    second = CorpusPacker(small_config(), FixedTokenizer())
    second.load_state(state)
    rest = texts[17:]
    got += [seq.tokens for text in rest for _, seq in second.add(text, "urdu", "train", ("A",))]

    assert got == expected


def test_a_checkpoint_from_another_config_is_refused():
    first = CorpusPacker(small_config(), FixedTokenizer())
    list(first.add("abcd", "urdu", "train", ("A",)))
    other = CorpusPacker(small_config(sequence_length=16), FixedTokenizer())
    with pytest.raises(ValueError, match="different packing config"):
        other.load_state(first.state())


def test_a_checkpoint_from_another_tokenizer_is_refused():
    """The buffered partial sequence holds ids from a vocabulary this run does not have."""
    first = CorpusPacker(small_config(), FixedTokenizer())
    list(first.add("abcd", "urdu", "train", ("A",)))
    other = CorpusPacker(small_config(), ByteTokenizer())
    with pytest.raises(ValueError, match="different tokenizer"):
        other.load_state(first.state())


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def test_a_written_corpus_verifies_against_its_manifest(tmp_path):
    _, writer, _ = _write(tmp_path, ["a" * 300])
    writer.write_manifest(tmp_path / "corpus.json")
    result = verify_corpus(tmp_path / "corpus.json")
    assert result["ok"], result["problems"]
    assert result["shards"] == len(writer.shards)
    assert result["tokens"] == sum(s.tokens for s in writer.shards)


def test_verification_catches_a_corrupted_shard(tmp_path):
    _, writer, _ = _write(tmp_path, ["a" * 300])
    writer.write_manifest(tmp_path / "corpus.json")
    path = tmp_path / writer.shards[0].path
    raw = bytearray(path.read_bytes())
    raw[0] ^= 0xFF  # one flipped bit, same length
    path.write_bytes(bytes(raw))
    result = verify_corpus(tmp_path / "corpus.json")
    assert not result["ok"]
    assert any("digest mismatch" in p for p in result["problems"])


def test_verification_catches_a_missing_byte_sidecar(tmp_path):
    """Nothing downstream would notice: the tokens are fine and BPB is simply not computable."""
    _, writer, _ = _write(tmp_path, ["a" * 300])
    writer.write_manifest(tmp_path / "corpus.json")
    (tmp_path / writer.shards[0].path).with_suffix(".bytes").unlink()
    result = verify_corpus(tmp_path / "corpus.json")
    assert not result["ok"]
    assert any("BPB is not computable" in p for p in result["problems"])


def test_verification_catches_a_missing_shard(tmp_path):
    _, writer, _ = _write(tmp_path, ["a" * 300])
    writer.write_manifest(tmp_path / "corpus.json")
    (tmp_path / writer.shards[0].path).unlink()
    result = verify_corpus(tmp_path / "corpus.json")
    assert not result["ok"]
    assert any("missing" in p for p in result["problems"])


def test_the_cli_exits_nonzero_on_a_broken_corpus(tmp_path, capsys):
    _, writer, _ = _write(tmp_path, ["a" * 300])
    writer.write_manifest(tmp_path / "corpus.json")
    assert packing_main([str(tmp_path / "corpus.json")]) == 0
    (tmp_path / writer.shards[0].path).unlink()
    assert packing_main([str(tmp_path / "corpus.json")]) == 1
    assert "FAIL" in capsys.readouterr().out
