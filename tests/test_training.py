"""The training loop, the packed-corpus loader, and the two things §9 requires before a paid run.

The resume test is the one with money attached. §9's cost controls say "checkpoint every 500 steps
with resume tested before any paid run (spot instances get preempted)", and a resume that is merely
*close* would show as a seam in the loss curve at exactly the compute fractions §4.3 evaluates at —
which is the primary endpoint.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest
import torch

from ravaan.models.ar import RavaanAR
from ravaan.models.config import ModelConfig
from ravaan.models.diffusion import RavaanDiffusion
from ravaan.training.config import CHECKPOINT_FRACTIONS, TrainingConfig
from ravaan.training.data import PackedCorpus, SequenceSampler
from ravaan.training.loop import Trainer
from ravaan.training.tasks import FramingTokens, TaskGenerator

SEQ = 16
VOCAB = 64
TINY = ModelConfig(
    vocab_size=VOCAB, n_layers=2, d_model=32, n_heads=2, d_ffn=88, context_length=SEQ
)


def _corpus(
    root,
    streams=(("urdu/train/A", "urdu", "train", "A", 64),),
    *,
    placeholder=False,
    learnable=False,
):
    """Write a corpus in stage 10's own on-disk format.

    ``learnable`` replaces uniform noise with a deterministic recurrence, for the tests that ask
    whether training *works* rather than whether the plumbing does. Uniform tokens have no
    structure to find, so a loss that fell on them would be measuring memorization of a 1,024-token
    corpus — which the AR arm can do and the diffusion arm's high-variance estimator cannot show.
    """
    shards = []
    rng = np.random.default_rng(0)
    for stream, population, split, arm, count in streams:
        directory = root / stream
        directory.mkdir(parents=True, exist_ok=True)
        name = stream.replace("/", "_") + "_00000"
        if learnable:
            tokens = np.empty((count, SEQ), dtype="<u2")
            tokens[:, 0] = rng.integers(0, VOCAB, size=count)
            for position in range(1, SEQ):
                tokens[:, position] = (tokens[:, position - 1].astype(np.int64) * 7 + 3) % VOCAB
        else:
            tokens = rng.integers(0, VOCAB, size=(count, SEQ)).astype("<u2")
        (directory / f"{name}.bin").write_bytes(tokens.tobytes())
        (directory / f"{name}.bytes").write_bytes(np.full(count, SEQ * 3, dtype="<u4").tobytes())
        shards.append(
            {
                "path": f"{stream}/{name}.bin",
                "stream": stream,
                "population": population,
                "split": split,
                "arm": arm,
                "sequences": count,
                "tokens": count * SEQ,
                "text_bytes": count * SEQ * 3,
                "separators": 0,
                "sha256": hashlib.sha256((directory / f"{name}.bin").read_bytes()).hexdigest(),
            }
        )
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "packing_version": "1",
                "tokenizer": {
                    "id": "placeholder:utf8-bytes" if placeholder else "sentencepiece:t.model",
                    "fingerprint": "dead",
                    "vocab_size": VOCAB,
                    "eos_id": 3,
                    "placeholder": placeholder,
                    "special_tokens": {"<mask>": 4},
                },
                "layout": {"dtype": "uint16", "byte_order": "little", "sequence_length": SEQ},
                "shards": shards,
            }
        ),
        encoding="utf-8",
    )
    return root


def _config(**overrides):
    base = {
        "sequence_length": SEQ,
        "tokens_per_step": 4 * SEQ,
        "tokens_processed": 4 * SEQ * 20,
        "warmup_steps": 2,
        "log_every": 5,
        "checkpoint_every": 10_000,
    }
    return TrainingConfig.from_dict({**TrainingConfig().to_dict(), **base, **overrides})


# --- the loader ------------------------------------------------------------


def test_corpus_reads_stage_10s_format(tmp_path):
    corpus = PackedCorpus(_corpus(tmp_path), split="train", arm="A")
    assert len(corpus) == 64
    assert corpus.tokens == 64 * SEQ
    assert corpus[0].shape == (SEQ,)
    assert corpus.text_bytes(0) == SEQ * 3
    assert corpus.population_of(0) == "urdu"


def test_corpus_refuses_a_placeholder_tokenizer(tmp_path):
    """Stage 10 refuses to *write* one; training refuses to read one. Same reason, both ends."""
    _corpus(tmp_path, placeholder=True)
    with pytest.raises(ValueError, match="placeholder"):
        PackedCorpus(tmp_path, split="train", arm="A")


def test_corpus_filters_split_and_arm(tmp_path):
    """The filter is the thing that stops a run training on its own held-out set."""
    _corpus(
        tmp_path,
        streams=(
            ("urdu/train/A", "urdu", "train", "A", 32),
            ("urdu/validation", "urdu", "validation", None, 8),
        ),
    )
    assert len(PackedCorpus(tmp_path, split="train", arm="A")) == 32
    assert len(PackedCorpus(tmp_path, split="validation", arm=None)) == 8
    with pytest.raises(ValueError, match="no shards"):
        PackedCorpus(tmp_path, split="test", arm="A")


def test_sampler_permutes_each_epoch_and_covers_the_corpus():
    sampler = SequenceSampler(64, 8, seed=3)
    assert sampler.batches_per_epoch == 8
    batches = (x[1] for x in sampler.batches())
    first = np.concatenate([b for _, b in zip(range(8), batches, strict=False)])
    assert sorted(first.tolist()) == list(range(64))
    assert not np.array_equal(sampler.permutation(0), sampler.permutation(1))


def test_sampler_seeks_without_replaying():
    """A resume reconstructs the order from (seed, epoch) rather than re-drawing it."""
    sampler = SequenceSampler(64, 8, seed=3)
    from_start = (x[1] for x in sampler.batches())
    from_eight = (x[1] for x in sampler.batches(8))
    walked = [b.tolist() for _, b in zip(range(12), from_start, strict=False)]
    sought = [b.tolist() for _, b in zip(range(4), from_eight, strict=False)]
    assert walked[8:12] == sought


# --- the schedule ----------------------------------------------------------

def test_checkpoint_fractions_are_the_prd_list():
    assert CHECKPOINT_FRACTIONS == (0.01, 0.02, 0.05, 0.10, 0.25, 0.50, 1.00)


def test_learning_rate_warms_then_decays_to_the_floor():
    config = TrainingConfig(warmup_steps=100)
    assert config.lr_at(0) < config.lr_at(50) < config.lr_at(99)
    assert config.lr_at(99) == pytest.approx(config.peak_lr)
    assert config.lr_at(config.total_steps) == pytest.approx(
        config.peak_lr * config.min_lr_ratio, rel=1e-6
    )


def test_batching_refuses_a_microbatch_that_does_not_divide_the_step():
    """§4.1's 'same tokens processed' is per-step too. A rounded batch is a different run."""
    config = TrainingConfig()
    assert config.resolve_batching(32) == (32, 8)
    with pytest.raises(ValueError, match="does not divide"):
        config.resolve_batching(48)


# --- the loop --------------------------------------------------------------


@pytest.mark.parametrize("arm", ["ar", "diff"])
def test_training_reduces_loss(tmp_path, arm):
    """Both objectives learn a learnable corpus — compared over windows, not endpoints.

    The diffusion arm's per-step loss is a *stochastic* estimate: one masking rate *t* is drawn
    per sequence and the summand is weighted by 1/t, so a four-sequence batch swings by several
    nats between neighbouring steps with no bearing on the model. Comparing single steps would
    test the draw. Comparing the mean of the first third against the last third tests training,
    which is what this is for.

    **It also takes more steps than the AR arm to show the same trend**, which is the property
    worth carrying into a real run: at 300 steps of four sequences the diffusion trend is inside
    the noise and at 1,200 it is not, across every learning rate from 3e-4 to 3e-3. A curve that
    looks flat early is not yet evidence of anything — G4 reads arm A's separation at 50% of
    tokens processed for related reasons.
    """
    corpus = PackedCorpus(
        _corpus(tmp_path / "c", learnable=True), split="train", arm="A"
    )
    torch.manual_seed(0)
    model = RavaanAR(TINY) if arm == "ar" else RavaanDiffusion(4, TINY)
    config = _config(peak_lr=3e-3, tokens_processed=4 * SEQ * 1_200, log_every=25)
    seen: list[float] = []
    trainer = Trainer(model, corpus, config, out_dir=tmp_path / arm, device="cpu", microbatch=4)
    trainer.train(on_log=lambda record: seen.append(record["loss"]))

    window = max(len(seen) // 3, 1)
    early = sum(seen[:window]) / window
    late = sum(seen[-window:]) / window
    assert late < early, f"{arm}: mean loss {early:.3f} -> {late:.3f} over {len(seen)} logs"


@pytest.mark.parametrize("arm", ["ar", "diff"])
def test_resume_is_exact(tmp_path, arm):
    """§9's precondition for spending money. Not 'close' — equal."""
    corpus = PackedCorpus(_corpus(tmp_path / "c"), split="train", arm="A")
    config = _config()

    torch.manual_seed(0)
    model = RavaanAR(TINY) if arm == "ar" else RavaanDiffusion(4, TINY)
    trainer = Trainer(model, corpus, config, out_dir=tmp_path / "a", device="cpu", microbatch=4)
    trainer.train(max_steps=6)
    checkpoint = trainer.save(tmp_path / "ck.pt")
    uninterrupted = trainer.train(max_steps=10)

    torch.manual_seed(999)  # a different seed, to prove the state came from the checkpoint
    fresh = RavaanAR(TINY) if arm == "ar" else RavaanDiffusion(4, TINY)
    resumed = Trainer(fresh, corpus, config, out_dir=tmp_path / "b", device="cpu", microbatch=4)
    resumed.load(checkpoint)
    assert resumed.state.step == 6
    resumed.train(max_steps=10)

    assert resumed.state.step == uninterrupted.step
    for (name, a), (_, b) in zip(model.named_parameters(), fresh.named_parameters(), strict=True):
        assert torch.equal(a, b), f"{name} diverged across a resume"


def test_kept_checkpoints_land_on_the_prd_fractions(tmp_path):
    corpus = PackedCorpus(_corpus(tmp_path / "c"), split="train", arm="A")
    config = _config(tokens_processed=4 * SEQ * 100)
    assert config.total_steps == 100
    assert set(config.checkpoint_steps()) == {1, 2, 5, 10, 25, 50, 100}

    torch.manual_seed(0)
    trainer = Trainer(
        RavaanAR(TINY), corpus, config, out_dir=tmp_path / "run", device="cpu", microbatch=4
    )
    trainer.train(max_steps=10)
    written = sorted(p.name for p in (tmp_path / "run").glob("*_f*.pt"))
    assert written == ["run_fp01.pt", "run_fp02.pt", "run_fp05.pt", "run_fp1.pt"]


def test_evaluate_reports_bits_per_byte_by_population(tmp_path):
    """§8.3 reports BPB by script; the aggregate alone would move with the mixture."""
    root = _corpus(
        tmp_path / "c",
        streams=(
            ("urdu/train/A", "urdu", "train", "A", 32),
            ("urdu/validation", "urdu", "validation", None, 8),
            ("roman_urdu/validation", "roman_urdu", "validation", None, 8),
        ),
    )
    corpus = PackedCorpus(root, split="train", arm="A")
    held_out = PackedCorpus(root, split="validation", arm=None)
    torch.manual_seed(0)
    trainer = Trainer(
        RavaanAR(TINY), corpus, _config(), out_dir=tmp_path / "run", device="cpu", microbatch=4
    )
    report = trainer.evaluate(held_out)
    assert set(report) == {"all", "urdu", "roman_urdu"}
    for entry in report.values():
        assert entry["bits_per_byte"] > 0
        assert entry["bits_per_token"] == pytest.approx(
            entry["nats_per_token"] / np.log(2), rel=1e-6
        )


def test_evaluate_seeds_the_diffusion_draw_and_leaves_the_denominators_alone(tmp_path):
    """Finding BA, both halves: the ELBO moves with the draw, and only the numerator does.

    Ravaan-DIFF's loss samples a masking rate and a mask per sequence, so `evaluate` returns a
    Monte Carlo estimate. Two things have to hold before averaging K draws is the right repair.
    A named generator must make a draw *reproducible* — otherwise K draws cannot be recorded as
    what they were — and two different seeds must actually *differ*, or the estimator's spread
    would be coming from somewhere this test does not know about. And `scored_tokens` must not
    move across draws: the mean of K bits-per-byte figures equals the bits-per-byte of the mean
    nats only while the denominator is constant, which is the identity `scripts/elbo.py` rests
    on. `scored` is `labels != IGNORE_INDEX`, which the mask does not touch — asserted here so
    a change to the objective that coupled them fails loudly rather than biasing an average.
    """
    root = _corpus(
        tmp_path / "c",
        streams=(
            ("urdu/train/A", "urdu", "train", "A", 32),
            ("urdu/validation", "urdu", "validation", None, 8),
        ),
    )
    corpus = PackedCorpus(root, split="train", arm="A")
    held_out = PackedCorpus(root, split="validation", arm=None)
    torch.manual_seed(0)
    trainer = Trainer(
        RavaanDiffusion(4, TINY), corpus, _config(), out_dir=tmp_path / "run",
        device="cpu", microbatch=4,
    )

    first = trainer.evaluate(held_out, generator=torch.Generator().manual_seed(1000))
    again = trainer.evaluate(held_out, generator=torch.Generator().manual_seed(1000))
    other = trainer.evaluate(held_out, generator=torch.Generator().manual_seed(1001))

    assert first["urdu"]["bits_per_byte"] == pytest.approx(
        again["urdu"]["bits_per_byte"], rel=1e-12
    ), "a named seed did not reproduce its own draw"
    assert first["urdu"]["bits_per_byte"] != other["urdu"]["bits_per_byte"], (
        "two seeds gave the same ELBO — the generator is not reaching the masking draw"
    )
    for report in (again, other):
        for name, entry in report.items():
            assert entry["scored_tokens"] == first[name]["scored_tokens"], (
                f"{name}'s denominator moved with the draw; averaging bpb would be invalid"
            )


def test_evaluate_without_a_generator_is_unchanged(tmp_path):
    """The default path is the one both core runs used, and it stays the global-RNG one.

    Session 33 added the `generator` argument; had it also changed what `generator=None` does,
    every committed `evaluation.json` would have stopped being reproducible by the code that
    wrote it. Ravaan-AR is the arm that can state this exactly, because its NLL has no draw in
    it at all.
    """
    root = _corpus(tmp_path / "c", streams=(
        ("urdu/train/A", "urdu", "train", "A", 32),
        ("urdu/validation", "urdu", "validation", None, 8),
    ))
    corpus = PackedCorpus(root, split="train", arm="A")
    held_out = PackedCorpus(root, split="validation", arm=None)
    torch.manual_seed(0)
    trainer = Trainer(
        RavaanAR(TINY), corpus, _config(), out_dir=tmp_path / "run", device="cpu", microbatch=4
    )
    assert trainer.evaluate(held_out) == trainer.evaluate(held_out)


# --- §4.2's task generator, through the loop -------------------------------

_ALPHABET = sorted(set("یہ ایک اردو جملہ ہے۔ کتاب پڑھنا اچھا بھائی 2024") | set("abcdefghijklmnop"))


class _CharCodec:
    """One character, one token — §7's tokenizer's shape without the `[tokenizer]` extra.

    Ids below 16 are §7's framing pieces and decode to nothing, which is also what a packed
    corpus's EOS separators do.
    """

    def encode(self, text):
        index = {char: 16 + i for i, char in enumerate(_ALPHABET)}
        return [index[char] for char in text if char in index]

    def decode(self, ids):
        return "".join(_ALPHABET[i - 16] for i in ids if 16 <= i < 16 + len(_ALPHABET))


def _tasks(arm, seed=0):
    framing = FramingTokens(
        pad=0, sep=5, fim_prefix=6, fim_suffix=7, fim_middle=8, lm=9, infill=10,
        translit=11, restore=12, codeswitch=13, ur=14, rom=15,
    )
    return TaskGenerator(_CharCodec(), framing, arm=arm, sequence_length=SEQ, seed=seed)


@pytest.mark.parametrize("arm", ["ar", "diff"])
def test_loop_trains_through_the_task_generator(tmp_path, arm):
    """The loop calls `model.loss(**batch.loss_kwargs())` and does not branch on the arm."""
    corpus = PackedCorpus(_corpus(tmp_path / "c", learnable=True), split="train", arm="A")
    torch.manual_seed(0)
    model = RavaanAR(TINY) if arm == "ar" else RavaanDiffusion(4, TINY)
    generator = _tasks(arm)
    trainer = Trainer(
        model, corpus, _config(), out_dir=tmp_path / "run", device="cpu",
        microbatch=4, tasks=generator,
    )
    records = []
    trainer.train(max_steps=10, on_log=records.append)

    assert generator.counts["sequences"] == 10 * 4  # accumulation x microbatch, every step
    assert records and "tasks" in records[-1]
    assert sum(records[-1]["tasks"].values()) == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("arm", ["ar", "diff"])
def test_resume_is_exact_with_tasks(tmp_path, arm):
    """§9's resume precondition, with §4.2's mixture in the path.

    The tasks are a function of (seed, step) rather than of a counter the generator advances, so a
    resumed run has to draw the same objectives for the same batches. If it did not, the curve
    would get a seam at every preemption that looked exactly like a mis-restored optimizer.
    """
    corpus = PackedCorpus(_corpus(tmp_path / "c", learnable=True), split="train", arm="A")
    config = _config()

    torch.manual_seed(0)
    model = RavaanAR(TINY) if arm == "ar" else RavaanDiffusion(4, TINY)
    trainer = Trainer(
        model, corpus, config, out_dir=tmp_path / "a", device="cpu",
        microbatch=4, tasks=_tasks(arm),
    )
    trainer.train(max_steps=6)
    checkpoint = trainer.save(tmp_path / "ck.pt")
    uninterrupted = trainer.train(max_steps=10)

    torch.manual_seed(999)
    fresh = RavaanAR(TINY) if arm == "ar" else RavaanDiffusion(4, TINY)
    resumed = Trainer(
        fresh, corpus, config, out_dir=tmp_path / "b", device="cpu",
        microbatch=4, tasks=_tasks(arm),
    )
    resumed.load(checkpoint)
    resumed.train(max_steps=10)

    assert resumed.state.step == uninterrupted.step
    for (name, a), (_, b) in zip(model.named_parameters(), fresh.named_parameters(), strict=True):
        assert torch.equal(a, b), f"{name} diverged across a resume with tasks"
