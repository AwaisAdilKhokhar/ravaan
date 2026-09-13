"""§4.2's task mixture and its two framings (PRD §4.1, §4.2, §4.5).

The test this file exists for is :func:`test_conditional_framings_are_identical_across_arms`. §4.1
claims the two models see "the same training tasks" and differ in exactly one thing; for the three
conditional objectives that claim is checkable at the level of the tensor, and if it ever stops
being true the experiment is measuring the data pipeline instead of the factorization.

The mixture tests are the second load-bearing group. §4.2 froze its shares "before Stage C and not
tuned afterwards", and two of the five tasks can only be built from native-script text — so the
question of whether the realized mixture is §4.2's, or §4.2's bent by the population mixture, is a
question about whether the run implements the preregistered design.

A character codec stands in for §7's tokenizer so the suite does not need the `[tokenizer]` extra.
One test at the bottom runs the real one when it is on disk.
"""

from __future__ import annotations

import string
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
import torch

from ravaan.data.corruption import CorruptionConfig
from ravaan.models.ar import IGNORE_INDEX, RavaanAR
from ravaan.models.config import ModelConfig
from ravaan.models.diffusion import RavaanDiffusion
from ravaan.training.tasks import (
    TASK_SHARES,
    FramingTokens,
    TaskGenerator,
    build_tasks,
)

CLEAN = (
    "یہ ایک اردو جملہ ہے۔ کتاب پڑھنا اچھا ہے، بھائی۔ پاکستان میں 2024 کے دوران اضافہ ہوا۔ "
    "درگاہ بندہ نواز کے صفحہ پر ہمارے مقررہ وقت کا حساب لکھا ہے اور ہم نے اسے دیکھا۔ "
    "لڑکی نے کہا کہ گھر جانا ہے، پھر وہ چلی گئی اور دروازہ بند کر دیا گیا تھا۔"
)

# Ids 0–15 are §7's framing pieces, so the alphabet starts at 16 and a token is one character.
ALPHABET = sorted(set(CLEAN + string.ascii_lowercase + string.digits + " .,?-()"))
OFFSET = 16
VOCAB = OFFSET + len(ALPHABET)
SEQ = 128

FRAMING = FramingTokens(
    pad=0,
    sep=5,
    fim_prefix=6,
    fim_suffix=7,
    fim_middle=8,
    lm=9,
    infill=10,
    translit=11,
    restore=12,
    codeswitch=13,
    ur=14,
    rom=15,
)


class CharCodec:
    """One character, one token. An exact inverse, which §7's tokenizer is not required to be."""

    def encode(self, text: str) -> list[int]:
        index = {char: OFFSET + i for i, char in enumerate(ALPHABET)}
        return [index[char] for char in text if char in index]

    def decode(self, ids) -> str:
        return "".join(ALPHABET[i - OFFSET] for i in ids if OFFSET <= i < VOCAB)


CODEC = CharCodec()


def _sequences(count: int, population: str = "urdu") -> tuple[np.ndarray, list[str]]:
    """``count`` packed sequences of real Urdu, tiled to the sequence length."""
    body = CODEC.encode(CLEAN)
    rows = []
    for row in range(count):
        offset = (row * 17) % len(body)
        rolled = body[offset:] + body[:offset]
        rows.append((rolled * (SEQ // len(rolled) + 1))[:SEQ])
    return np.array(rows, dtype=np.int64), [population] * count


def _generator(arm: str, **kwargs) -> TaskGenerator:
    return TaskGenerator(CODEC, FRAMING, arm=arm, sequence_length=SEQ, seed=0, **kwargs)


# ---------------------------------------------------------------------------
# §4.1 — the arms see the same tasks
# ---------------------------------------------------------------------------


def test_conditional_framings_are_identical_across_arms():
    """§4.1's "same training tasks", at the level of the tensor.

    Transliteration, restoration and code-switch normalization must produce byte-identical token
    layouts for both arms. What differs is what happens to the target half — AR predicts it with
    the source out of the loss, DIFF diffuses it with the source pinned — and that difference is
    the factorization, which is the one thing §4.1 allows to differ.
    """
    sequences, populations = _sequences(24)
    ar = _generator("ar").build(sequences, populations, step=0)
    diff = _generator("diff").build(sequences, populations, step=0)

    assert ar.tasks == diff.tasks
    pairs = ("translit", "restore", "codeswitch")
    conditional = [i for i, task in enumerate(ar.tasks) if task in pairs]
    assert conditional, "the fixture should produce conditional tasks"
    for row in conditional:
        assert torch.equal(ar.tokens[row], diff.tokens[row])
        assert torch.equal(ar.labels[row], diff.labels[row])


def test_ar_scores_the_target_half_only():
    """§4.1's "loss on target": the source is conditioning, not something to predict."""
    sequences, populations = _sequences(24)
    batch = _generator("ar").build(sequences, populations, step=0)
    for row, task in enumerate(batch.tasks):
        if task not in ("translit", "restore", "codeswitch"):
            continue
        tokens = batch.tokens[row].tolist()
        separator = tokens.index(FRAMING.sep)
        scored = batch.labels[row] != IGNORE_INDEX
        assert not scored[: separator + 2].any(), "the source half must not be scored"
        assert scored[separator + 2].item(), "the target half must be"


def test_diff_pins_the_source_and_diffuses_the_target():
    """§4.1's "condition on unmasked source, diffuse the target"."""
    sequences, populations = _sequences(24)
    batch = _generator("diff").build(sequences, populations, step=0)
    assert batch.keep is not None
    for row, task in enumerate(batch.tasks):
        if task not in ("translit", "restore", "codeswitch"):
            continue
        tokens = batch.tokens[row].tolist()
        separator = tokens.index(FRAMING.sep)
        assert batch.keep[row][: separator + 2].all(), "the source half must never be masked"
        assert not batch.keep[row][separator + 2].item(), "the target half must be maskable"


def test_ar_gets_no_keep_and_diff_does():
    """The AR arm conditions through `labels`; handing it a `keep` would be a second answer."""
    sequences, populations = _sequences(8)
    assert _generator("ar").build(sequences, populations).keep is None
    assert _generator("diff").build(sequences, populations).keep is not None
    assert "keep" not in _generator("ar").build(sequences, populations).loss_kwargs()


def test_infill_gives_ar_a_fim_reordering():
    """§4.1's FIM row — the fix for v1's central flaw, and the reason A2 is a data change."""
    sequences, populations = _sequences(40)
    batch = _generator("ar").build(sequences, populations, step=1)
    rows = [i for i, task in enumerate(batch.tasks) if task == "infill"]
    assert rows
    for row in rows:
        tokens = batch.tokens[row].tolist()
        assert tokens[0] == FRAMING.infill
        assert tokens[1] == FRAMING.fim_prefix
        assert tokens.index(FRAMING.fim_suffix) < tokens.index(FRAMING.fim_middle)
        # Everything is scored, as published FIM is: the reordering is the task.
        assert (batch.labels[row] != IGNORE_INDEX).all()


def test_infill_gives_diff_a_masked_middle_in_place():
    """No reordering — the diffusion arm conditions on a suffix by not masking it."""
    sequences, populations = _sequences(40)
    batch = _generator("diff").build(sequences, populations, step=1)
    rows = [i for i, task in enumerate(batch.tasks) if task == "infill"]
    assert rows
    for row in rows:
        tokens = batch.tokens[row].tolist()
        assert tokens[0] == FRAMING.infill
        assert FRAMING.fim_prefix not in tokens
        maskable = (~batch.keep[row]).nonzero().flatten().tolist()
        # One contiguous span, with a prefix and a suffix on either side of it.
        assert maskable == list(range(maskable[0], maskable[-1] + 1))
        assert maskable[0] > 1 and maskable[-1] < SEQ - 1
        scored = (batch.labels[row] != IGNORE_INDEX).nonzero().flatten().tolist()
        assert scored == maskable


# ---------------------------------------------------------------------------
# §4.2 — the mixture
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("microbatch", [4, 8, 32])
def test_realized_mixture_converges_on_the_frozen_shares(microbatch):
    """§4.2's shares are a preregistered hypothesis; the run has to actually build them.

    **Parametrized on the microbatch because that is where the first implementation broke.**
    Largest-remainder apportionment with a fixed tie-break gives every batch of a given size the
    same answer, so at a microbatch of 4 it produced three plain-LM sequences and one infilling
    sequence and *none* of §4.2's other three objectives, at any number of steps. A constant bias
    does not average out, which is why this asserts at the batch sizes a host actually fits rather
    than at the one that happens to round well.
    """
    generator = _generator("diff")
    sequences, populations = _sequences(microbatch)
    for step in range(2048 // microbatch):
        generator.build(sequences, populations, step=step)
    realized = generator.realized_shares()
    for task, share in TASK_SHARES.items():
        assert realized[task] == pytest.approx(share, abs=0.025)


def test_constrained_tasks_never_land_on_an_ineligible_population():
    """Transliteration has no native original to be the answer for a Roman-Urdu sequence."""
    native, _ = _sequences(20)
    populations = ["urdu"] * 10 + ["roman_urdu"] * 10
    batch = _generator("diff").build(native, populations, step=0)
    for row, task in enumerate(batch.tasks):
        if task in ("translit", "codeswitch"):
            assert populations[row] == "urdu"


def test_a_shortfall_is_counted_rather_than_absorbed():
    """A batch that cannot supply a frozen share is a fact about the run, not a silent fallback."""
    sequences, _ = _sequences(32)
    generator = _generator("diff")
    generator.build(sequences, ["roman_urdu"] * 32, step=0)
    assert generator.counts["shortfall/translit"] > 0
    assert generator.counts["shortfall/codeswitch"] > 0
    assert generator.counts["translit"] == 0


def test_apportionment_places_every_sequence():
    generator = _generator("ar")
    for size in (1, 2, 7, 8, 13, 64, 256):
        sequences, populations = _sequences(size)
        batch = generator.build(sequences, populations, step=size)
        assert len(batch.tasks) == size
        assert set(batch.tasks) <= set(TASK_SHARES)


# ---------------------------------------------------------------------------
# The invariants the training loop depends on
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("arm", ["ar", "diff"])
def test_every_framed_sequence_is_exactly_the_sequence_length(arm):
    """§4.3 budgets in tokens processed: a short sequence makes the budget mean two things."""
    sequences, populations = _sequences(32)
    batch = _generator(arm).build(sequences, populations, step=3)
    assert batch.tokens.shape == (32, SEQ)
    assert batch.labels.shape == (32, SEQ)
    assert batch.tokens.min() >= 0
    assert batch.tokens.max() < VOCAB


@pytest.mark.parametrize("arm", ["ar", "diff"])
def test_padding_is_out_of_attention_and_out_of_the_loss(arm):
    sequences, populations = _sequences(32)
    generator = _generator(arm)
    batch = generator.build(sequences, populations, step=5)
    if batch.padding_mask is None:
        pytest.skip("this batch happened to fit exactly")
    padding = ~batch.padding_mask
    assert (batch.tokens[padding] == FRAMING.pad).all()
    assert (batch.labels[padding] == IGNORE_INDEX).all()
    if batch.keep is not None:
        assert batch.keep[padding].all()
    assert generator.counts["pad_tokens"] == int(padding.sum())


@pytest.mark.parametrize("arm", ["ar", "diff"])
def test_build_is_a_function_of_seed_and_step(arm):
    """§9's resume reconstructs the batch order from a step count, so the *tasks* have to be a
    function of it too — otherwise the curve gets a seam at every preemption."""
    sequences, populations = _sequences(16)
    first = _generator(arm).build(sequences, populations, step=11)
    again = _generator(arm).build(sequences, populations, step=11)
    other = _generator(arm).build(sequences, populations, step=12)
    assert torch.equal(first.tokens, again.tokens)
    assert torch.equal(first.labels, again.labels)
    assert first.tasks == again.tasks
    assert not torch.equal(first.tokens, other.tokens)


def test_generator_records_its_version_and_seed():
    """§4.2: "with the generator version and seed recorded"."""
    recorded = _generator("diff", corruption=CorruptionConfig(ocr_lossy_share=0.25)).to_dict()
    assert recorded["seed"] == 0
    assert recorded["shares"] == TASK_SHARES
    assert recorded["corruption"]["ocr_lossy_share"] == 0.25
    assert recorded["corruption_fingerprint"] != CorruptionConfig().fingerprint()


def test_shares_must_sum_to_one():
    with pytest.raises(ValueError, match="must sum to 1"):
        _generator("ar", shares={"lm": 0.5, "infill": 0.2})


def test_framing_tokens_refuses_a_partial_manifest():
    """§7 put all twelve inside the 16,384 so both arms embed one vocabulary. Inventing an id
    here would undo that with no downstream symptom."""
    with pytest.raises(ValueError, match="<translit>"):
        FramingTokens.from_manifest({"special_tokens": {"<sep>": 5, "<fim_prefix>": 6}})


# ---------------------------------------------------------------------------
# Through the models
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("arm", ["ar", "diff"])
def test_both_arms_take_a_framed_batch_and_produce_gradients(arm):
    config = ModelConfig(
        vocab_size=VOCAB, n_layers=2, d_model=32, n_heads=2, d_ffn=88, context_length=SEQ
    )
    torch.manual_seed(0)
    model = RavaanAR(config) if arm == "ar" else RavaanDiffusion(4, config)
    sequences, populations = _sequences(8)
    batch = _generator(arm).build(sequences, populations, step=0)
    out = model.loss(**batch.loss_kwargs())
    assert torch.isfinite(out.loss)
    assert int(out.scored) > 0
    out.loss.backward()
    assert not [name for name, p in model.named_parameters() if p.grad is None]


def test_scored_is_the_denominator_nats_was_divided_by():
    """§8.3's bits-per-byte multiplies a per-token average back up, so it needs the denominator
    and not the sequence length — which under a conditional framing is most of a sequence out."""
    config = ModelConfig(
        vocab_size=VOCAB, n_layers=2, d_model=32, n_heads=2, d_ffn=88, context_length=SEQ
    )
    torch.manual_seed(0)
    sequences, populations = _sequences(8)
    batch = _generator("ar").build(sequences, populations, step=0)
    out = RavaanAR(config).loss(**batch.loss_kwargs())
    assert int(out.scored) == int((batch.labels[:, 1:] != IGNORE_INDEX).sum())
    assert int(out.scored) < batch.tokens.numel()


# ---------------------------------------------------------------------------
# §7's real tokenizer, when it is on disk
# ---------------------------------------------------------------------------

TOKENIZER = Path("data/tokenizer/ravaan-16k.model")


@pytest.mark.skipif(not TOKENIZER.exists(), reason="§7's tokenizer is not in this checkout")
def test_the_real_tokenizer_round_trips_through_the_framing():
    """The corruptions are text transforms, so the codec has to go both ways on real Urdu."""
    from ravaan.training.tasks import SentencePieceCodec  # noqa: PLC0415

    codec = SentencePieceCodec(str(TOKENIZER))
    ids = codec.encode(CLEAN)
    assert codec.decode(ids).replace(" ", "") == CLEAN.replace(" ", "")

    framing = FramingTokens(
        pad=0, sep=5, fim_prefix=6, fim_suffix=7, fim_middle=8, lm=9, infill=10,
        translit=11, restore=12, codeswitch=13, ur=14, rom=15,
    )
    generator = TaskGenerator(codec, framing, arm="diff", sequence_length=512, seed=0)
    sequences = np.array([(ids * (512 // len(ids) + 1))[:512] for _ in range(8)], dtype=np.int64)
    batch = generator.build(sequences, ["urdu"] * 8, step=0)
    assert batch.tokens.shape == (8, 512)
    assert isinstance(batch.counts, Counter)


# ---------------------------------------------------------------------------
# build_tasks — the guards that stop a run from quietly training the wrong thing.
#
# These had no test at all while the function lived in `scripts/train.py`, which is the coverage
# gap progress.md names: every stage's *library* is tested to pinned hash values and the drivers
# that compose them had nothing. Session 21 is what that costs — kernel 10 never called this and
# trained the bare objective for it, invisibly, because `Trainer(tasks=None)` is a valid call.
# ---------------------------------------------------------------------------


class _Corpus:
    """Just the surface `build_tasks` reads: a corpus is its tokenizer manifest here."""

    def __init__(self, manifest):
        self.tokenizer = manifest


class _Config:
    sequence_length = 64
    seed = 0


def _manifest(fingerprint="deadbeefdeadbeef"):
    return {
        "id": "sentencepiece:ravaan-16k.model",
        "fingerprint": fingerprint,
        "special_tokens": {
            "<mask>": 4, "<sep>": 5, "<fim_prefix>": 6, "<fim_suffix>": 7, "<fim_middle>": 8,
            "<lm>": 9, "<infill>": 10, "<translit>": 11, "<restore>": 12, "<codeswitch>": 13,
            "<ur>": 14, "<rom>": 15,
        },
        "control_ids": {"pad": 0, "unk": 1, "bos": 2, "eos": 3},
    }


def test_build_tasks_refuses_a_missing_tokenizer(tmp_path):
    """No tokenizer means no way back to text, and the bare objective is not the experiment."""
    with pytest.raises(FileNotFoundError) as excinfo:
        build_tasks("ar", _Corpus(_manifest()), _Config(), tmp_path / "absent.model")
    # The message has to say what is missing and why, not just that a path does not exist —
    # the operator's next move is to pass a tokenizer, not to wonder what wanted one.
    assert "not there" in str(excinfo.value)
    assert "§4.1" in str(excinfo.value)


def test_build_tasks_refuses_a_tokenizer_the_corpus_was_not_packed_with(tmp_path, monkeypatch):
    """A fingerprint mismatch would mix two vocabularies inside one sequence, silently."""
    model = tmp_path / "other.model"
    model.write_bytes(b"not a real sentencepiece model")

    class _Stub:
        def __init__(self, path):
            self.tokenizer = self

        def fingerprint(self):
            return "0123456789abcdef"

    monkeypatch.setattr("ravaan.training.tasks.SentencePieceCodec", _Stub)
    with pytest.raises(ValueError) as excinfo:
        build_tasks("ar", _Corpus(_manifest("deadbeefdeadbeef")), _Config(), model)
    assert "0123456789abcdef" in str(excinfo.value)
    assert "deadbeefdeadbeef" in str(excinfo.value)


def test_build_tasks_returns_a_generator_when_the_fingerprint_matches(tmp_path, monkeypatch):
    """The happy path, so the guards above are not passing for the wrong reason."""
    model = tmp_path / "ravaan-16k.model"
    model.write_bytes(b"not a real sentencepiece model")

    class _Stub:
        def __init__(self, path):
            self.tokenizer = self

        def fingerprint(self):
            return "deadbeefdeadbeef"

    monkeypatch.setattr("ravaan.training.tasks.SentencePieceCodec", _Stub)
    tasks = build_tasks("diff", _Corpus(_manifest()), _Config(), model)
    assert isinstance(tasks, TaskGenerator)
    assert tasks.arm == "diff"
    # §4.2's table, unmodified — a generator built through this path is the experiment's mixture.
    assert tasks.shares == TASK_SHARES
