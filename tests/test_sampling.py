"""The decoders, and the two §8.1 invariants they are the only place that can break.

§8.1 lists locked-token preservation and bit-identical determinism under a fixed seed as
engineering invariants — CI, never a results table. Until session 22 neither could be tested,
because nothing could decode. Both are asserted here, on both arms.

The other thing these tests hold is the *agreement* between `ravaan.sampling.prompts` and
`ravaan.training.tasks`. A prompt whose layout drifts from the training framing asks the model a
question it was never taught, and the symptom is bad output rather than an error — so the
framings are compared token for token against what the task generator builds.
"""

from __future__ import annotations

import random

import pytest

torch = pytest.importorskip("torch")
np = pytest.importorskip("numpy")

from ravaan.evaluation.generation import GenerationStats, longest_repeated_run  # noqa: E402
from ravaan.models.ar import RavaanAR  # noqa: E402
from ravaan.models.config import ModelConfig  # noqa: E402
from ravaan.models.diffusion import RavaanDiffusion  # noqa: E402
from ravaan.sampling import generate, prompts  # noqa: E402
from ravaan.sampling.ar import sample_ar  # noqa: E402
from ravaan.sampling.decoding import (  # noqa: E402
    SamplingConfig,
    build_generator,
    filter_logits,
    restrict,
    sample_ids,
)
from ravaan.sampling.diffusion import sample_diffusion, unmask_counts  # noqa: E402
from ravaan.training.tasks import FramingTokens, TaskGenerator  # noqa: E402

TINY = ModelConfig(vocab_size=64, n_layers=2, d_model=32, n_heads=2, d_ffn=88, context_length=32)
MASK = 4

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


def ar_model(seed: int = 0) -> RavaanAR:
    torch.manual_seed(seed)
    return RavaanAR(TINY).eval()


def diff_model(seed: int = 0) -> RavaanDiffusion:
    torch.manual_seed(seed)
    return RavaanDiffusion(MASK, TINY).eval()


# --- the shared half: turning logits into tokens ---------------------------


def test_temperature_zero_is_argmax_and_still_reports_a_real_probability():
    """Greedy must not report certainty — A4's schedule ranks positions by this number.

    A decoder that collapsed the distribution under greedy would make the confidence schedule
    indistinguishable from the random one, and the ablation would report that finding.
    """
    logits = torch.tensor([[0.1, 5.0, 0.2, 4.9]])
    ids, confidence = sample_ids(logits, SamplingConfig(temperature=0.0))
    assert ids.tolist() == [1]
    assert confidence.item() == pytest.approx(logits.softmax(-1)[0, 1].item())
    assert confidence.item() < 1.0


def test_top_k_keeps_exactly_k_candidates():
    logits = torch.tensor([[1.0, 2.0, 3.0, 4.0, 5.0]])
    kept = filter_logits(logits, SamplingConfig(top_k=2))
    assert torch.isfinite(kept).sum().item() == 2
    assert kept[0, 4].isfinite() and kept[0, 3].isfinite()


def test_top_p_always_keeps_the_most_likely_token():
    """A confident distribution under a small top_p must not produce an empty candidate set.

    The shift in `filter_logits` is what makes this true, and it is the one line of the filter
    that a plausible implementation gets wrong — `cumsum >= top_p` empties the set exactly when
    the model is most certain.
    """
    logits = torch.tensor([[10.0, 0.0, 0.0]])
    kept = filter_logits(logits, SamplingConfig(top_p=0.1))
    assert torch.isfinite(kept).sum().item() == 1
    assert kept[0, 0].isfinite()


def test_forbidden_ids_are_never_drawn():
    logits = torch.zeros(1, 8)
    generator = build_generator("cpu", 1)
    for _ in range(50):
        ids, _ = sample_ids(logits, SamplingConfig(), generator=generator, forbid=(3, 4))
        assert ids.item() not in (3, 4)


def test_restrict_does_not_mutate_the_caller():
    logits = torch.zeros(1, 4)
    restrict(logits, (2,))
    assert torch.equal(logits, torch.zeros(1, 4))


def test_forbidding_a_token_the_nucleus_would_have_held_alone():
    """Forbid must be applied before top-p, not after.

    The other order empties the candidate set exactly when the model is certain about a token the
    decoder may not emit — all `-inf`, a NaN through softmax, and on CUDA a device-side assert
    inside `multinomial` that names `input[0] != 0` and nothing else. Found by forbidding `</s>`
    on a diffusion canvas, which is the one place it happens in practice.
    """
    logits = torch.tensor([[10.0, 0.0, 0.1]])
    ids, confidence = sample_ids(
        logits, SamplingConfig(top_p=0.5, seed=0), generator=build_generator("cpu", 0), forbid=(0,)
    )
    assert ids.item() in (1, 2)
    assert torch.isfinite(confidence).all()
    assert confidence.item() > 0


# --- §8.1: determinism -----------------------------------------------------


def test_ar_is_bit_identical_under_one_seed():
    model = ar_model()
    prompt = [[9, 11, 12]]
    first = sample_ar(model, prompt, max_new_tokens=12, config=SamplingConfig(seed=7))
    second = sample_ar(model, prompt, max_new_tokens=12, config=SamplingConfig(seed=7))
    assert torch.equal(first.tokens, second.tokens)


def test_ar_seeds_actually_change_the_sample():
    """Determinism is only worth asserting if the sampler is not simply deterministic."""
    model = ar_model()
    prompt = [[9, 11, 12]]
    a = sample_ar(model, prompt, max_new_tokens=20, config=SamplingConfig(seed=1))
    b = sample_ar(model, prompt, max_new_tokens=20, config=SamplingConfig(seed=2))
    assert not torch.equal(a.tokens, b.tokens)


@pytest.mark.parametrize("schedule", ["random", "confidence", "gumbel"])
def test_diffusion_is_bit_identical_under_one_seed(schedule):
    model = diff_model()
    canvas = torch.full((2, 16), MASK)
    canvas[:, 0] = 9
    first = sample_diffusion(
        model, canvas, steps=8, schedule=schedule, config=SamplingConfig(seed=3)
    )
    second = sample_diffusion(
        model, canvas, steps=8, schedule=schedule, config=SamplingConfig(seed=3)
    )
    assert torch.equal(first.tokens, second.tokens)


def test_sampling_does_not_disturb_global_rng():
    """A generation taken mid-run must not move the training trajectory (§8.1's determinism)."""
    model = ar_model()
    torch.manual_seed(99)
    before = torch.rand(4)
    torch.manual_seed(99)
    sample_ar(model, [[9]], max_new_tokens=8, config=SamplingConfig(seed=5))
    after = torch.rand(4)
    assert torch.equal(before, after)


# --- §8.1: locked-token preservation ---------------------------------------


def test_ar_never_rewrites_its_prompt():
    model = ar_model()
    prompt = torch.tensor([[9, 21, 22, 23]])
    out = sample_ar(model, prompt, max_new_tokens=10)
    assert torch.equal(out.tokens[:, :4], prompt)
    assert out.locked[:, :4].all() and not out.locked[:, 4:].any()


@pytest.mark.parametrize("schedule", ["random", "confidence", "gumbel"])
def test_diffusion_never_writes_a_locked_position(schedule):
    model = diff_model()
    canvas = torch.arange(16).unsqueeze(0) % 60 + 16
    locked = torch.zeros(1, 16, dtype=torch.bool)
    locked[:, :4] = True
    locked[:, 12:] = True
    out = sample_diffusion(model, canvas, locked=locked, steps=6, schedule=schedule)
    assert torch.equal(out.tokens[locked], canvas[locked])
    assert (out.tokens[~locked] != MASK).all()


def test_diffusion_fills_every_masked_position_at_any_step_count():
    """A3 sweeps 8/16/32/64 over a canvas of 16. Both sides of `steps == masked` must terminate."""
    model = diff_model()
    canvas = torch.full((1, 16), MASK)
    canvas[:, 0] = 9
    for steps in (1, 2, 8, 16, 32, 64):
        out = sample_diffusion(model, canvas, steps=steps)
        assert (out.tokens != MASK).all(), steps
        assert out.forwards <= steps


def test_unmask_counts_sum_to_the_total_and_finish():
    for total in (0, 1, 7, 15, 512):
        for steps in (1, 3, 8, 64):
            counts = unmask_counts(total, steps)
            assert len(counts) == steps
            assert sum(counts) == total
            assert all(c >= 0 for c in counts)


def test_gumbel_zero_is_the_confidence_schedule_exactly():
    """The family has to contain its own limit, or `gumbel` is a fourth thing rather than a knob.

    `log` is monotone, so adding zero noise to `log p` leaves the ranking `confidence` produces —
    which makes A4's confidence arm reachable from this schedule rather than merely similar to it.
    Asserted at both temperatures because greedy takes a different branch in `sample_ids`.
    """
    model = diff_model()
    canvas = torch.full((1, 24), MASK)
    canvas[:, 0] = 9
    for temperature in (1.0, 0.0):
        config = SamplingConfig(temperature=temperature, top_p=0.95, seed=11)
        strict = sample_diffusion(model, canvas, steps=6, schedule="confidence", config=config)
        limit = sample_diffusion(
            model, canvas, steps=6, schedule="gumbel", gumbel=0.0, config=config
        )
        assert torch.equal(strict.tokens, limit.tokens), temperature


def test_gumbel_noise_changes_the_order_and_is_recorded():
    model = diff_model()
    canvas = torch.full((1, 24), MASK)
    canvas[:, 0] = 9
    config = SamplingConfig(seed=11)
    strict = sample_diffusion(model, canvas, steps=6, schedule="confidence", config=config)
    noisy = sample_diffusion(model, canvas, steps=6, schedule="gumbel", gumbel=3.0, config=config)
    assert not torch.equal(strict.tokens, noisy.tokens)
    # An ablation row that does not carry the knob cannot be read back.
    assert noisy.detail["gumbel"] == 3.0
    assert strict.detail["gumbel"] is None


def test_diffusion_refuses_a_schedule_it_does_not_have():
    with pytest.raises(ValueError, match="schedule must be"):
        sample_diffusion(diff_model(), torch.full((1, 8), MASK), schedule="entropy")


def test_diffusion_refuses_a_model_without_an_absorbing_state():
    """A `RavaanAR` handed to the denoiser would decode happily and mean nothing."""
    with pytest.raises(ValueError, match="absorbing state"):
        sample_diffusion(ar_model(), torch.full((1, 8), MASK))


# --- stopping, budgets and the context wall --------------------------------


def test_ar_stops_at_eos_and_records_the_length():
    model = ar_model()
    # Force EOS by forbidding everything else: the decoder must then stop on the first token.
    forbid = tuple(i for i in range(TINY.vocab_size) if i != 3)
    out = sample_ar(model, [[9, 12]], max_new_tokens=10, eos_id=3, forbid=forbid)
    assert out.detail["stop"] == "eos"
    assert out.lengths.tolist() == [3]
    assert out.rows() == [[9, 12, 3]]


def test_ar_stops_at_the_context_length():
    model = ar_model()
    prompt = [[9] * (TINY.context_length - 4)]
    out = sample_ar(model, prompt, max_new_tokens=100)
    assert out.tokens.shape[1] == TINY.context_length
    assert out.detail["stop"] == "context"


def test_ar_refuses_a_prompt_longer_than_the_context():
    with pytest.raises(ValueError, match="context length"):
        sample_ar(ar_model(), [[9] * (TINY.context_length + 1)], max_new_tokens=1)


def test_ar_refuses_a_ragged_batch():
    with pytest.raises(ValueError, match="one length"):
        sample_ar(ar_model(), [[9, 1, 2], [9, 1]], max_new_tokens=4)


def test_written_returns_only_the_generated_half():
    model = ar_model()
    out = sample_ar(model, [[9, 21, 22]], max_new_tokens=5)
    assert out.written()[0] == out.rows()[0][3:]


# --- §4.2's framings, pinned against the trainer ---------------------------


def codec_double():
    """A character codec, because the trainer's own corruptions go through it.

    An earlier version of this double parsed integers out of the decoded text, which works until
    `corrupt_restore` inserts a zero-width character into it — the tasks contract says a round
    trip need not be the identity, and a double that assumed one was testing itself.
    """

    class Codec:
        def encode(self, text):
            return [ord(c) % 40 + 20 for c in text]

        def decode(self, ids):
            return "".join(chr(int(i)) for i in ids)

    return Codec()


def trainer_row(arm: str, task: str, clean: list[int], seed: str = "0:0:0"):
    """One framed row, straight out of the training generator, for comparison."""
    generator = TaskGenerator(
        codec_double(), FRAMING, arm=arm, sequence_length=len(clean), seed=0
    )
    built = generator._frame(task, clean, random.Random(seed))
    assert built is not None
    return built


def test_lm_prompt_matches_the_training_framing():
    clean = list(range(20, 36))
    tokens, _, _, _ = trainer_row("ar", "lm", clean)
    built = prompts.lm(FRAMING, "ar", prefix=clean[:6])
    assert list(built.tokens) == tokens[:7]
    assert all(built.locked)


def test_infill_ar_prompt_is_the_fim_rearrangement():
    """`<infill> <fim_prefix> … <fim_suffix> … <fim_middle>` — the answer follows."""
    built = prompts.infill(FRAMING, "ar", prefix=[20, 21, 22], suffix=[30, 31], span=4)
    assert list(built.tokens) == [10, 6, 20, 21, 22, 7, 30, 31, 8]
    assert all(built.locked)
    assert built.hinted_length is None  # the AR arm is not told how long the middle is


def test_infill_diff_prompt_leaves_the_hole_in_place():
    built = prompts.infill(
        FRAMING, "diff", prefix=[20, 21], suffix=[30, 31], span=3, mask_id=MASK
    )
    assert list(built.tokens) == [10, 20, 21, MASK, MASK, MASK, 30, 31]
    assert list(built.locked) == [True, True, True, False, False, False, True, True]
    assert built.hinted_length == 3


def test_pair_framing_matches_the_trainer_token_for_token():
    """The layout §4.2 trains and the layout §8 prompts are the same object, or nothing holds.

    Includes the part that reads like a slip — `restore` repeats its task token in the source
    slot. See `ravaan.sampling.prompts.restore`.
    """
    source = [40, 41, 42]
    built = prompts.restore(FRAMING, "ar", source=source)
    assert list(built.tokens) == [12, 12, 40, 41, 42, 5, 14]

    clean = list(range(20, 36))
    tokens, labels, keep, pad = trainer_row("ar", "restore", clean)
    start = tokens.index(FRAMING.sep)
    assert tokens[0] == FRAMING.restore and tokens[1] == FRAMING.restore
    assert tokens[start + 1] == FRAMING.ur
    # The trainer scores from just after the target marker; the prompt ends there.
    assert labels[start + 2] != -100


def test_transliteration_markers_follow_the_direction():
    forward = prompts.transliterate(FRAMING, "ar", source=[40, 41], direction="ur2rom")
    back = prompts.transliterate(FRAMING, "ar", source=[40, 41], direction="rom2ur")
    assert list(forward.tokens) == [11, 14, 40, 41, 5, 15]
    assert list(back.tokens) == [11, 15, 40, 41, 5, 14]


def test_diffusion_pair_prompt_must_be_told_the_answer_length():
    with pytest.raises(ValueError, match="target length"):
        prompts.codeswitch(FRAMING, "diff", source=[40, 41], mask_id=MASK)


def test_diff_prompt_needs_a_mask_id():
    with pytest.raises(ValueError, match="mask_id"):
        prompts.lm(FRAMING, "diff", length=8)


def test_generate_refuses_a_prompt_framed_for_the_other_arm():
    built = prompts.infill(FRAMING, "ar", prefix=[20], suffix=[30], span=2)
    with pytest.raises(ValueError, match="was handed to"):
        generate(diff_model(), built, steps=4)


def test_generate_dispatches_on_the_prompt():
    ar = generate(ar_model(), prompts.lm(FRAMING, "ar", prefix=[20]), max_new_tokens=6)
    assert ar.arm == "ar" and ar.tokens.shape == (1, 8)

    canvas = prompts.lm(FRAMING, "diff", prefix=[20], length=12, mask_id=MASK)
    diff = generate(diff_model(), canvas, steps=4)
    assert diff.arm == "diff" and diff.tokens.shape == (1, 12)
    assert diff.detail["steps"] == 4


# --- §8.3's generation metrics ---------------------------------------------


def test_script_consistency_reads_the_script_it_was_asked_for():
    stats = GenerationStats.of("اردو زبان", script="arabic")
    assert stats.script_consistency == pytest.approx(1.0)
    assert GenerationStats.of("urdu zaban", script="arabic").script_consistency == 0.0


def test_repetition_catches_a_loop_that_distinct_1_misses():
    looped = " ".join(["الف بے جیم دال"] * 8)
    stats = GenerationStats.of(looped)
    assert stats.distinct[1] == pytest.approx(4 / 32)
    assert stats.repetition > 0.8
    assert stats.longest_repeat >= 28


def test_longest_repeated_run_on_text_without_repeats():
    assert longest_repeated_run(["a", "b", "c", "d", "e"]) == 0


def test_stats_of_empty_text_do_not_divide_by_zero():
    stats = GenerationStats.of("")
    assert stats.words == 0 and stats.distinct[4] == 0.0 and stats.longest_repeat == 0
