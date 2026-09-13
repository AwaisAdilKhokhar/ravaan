"""Ravaan-DIFF's decoder — iterative unmasking of an absorbing-state chain (PRD §8, §4.4).

The reverse of `ravaan.models.diffusion`'s forward process. Training corrupts a sequence by
absorbing positions into `<mask>` with probability *t*; decoding starts from all-mask at *t* = 1
and walks *t* down to 0, committing tokens as it goes. Both of §4.4's inference-only ablations
live here and nowhere else:

* **A3 — denoising steps (8 / 16 / 32 / 64).** ``steps``. The whole reason masked diffusion is
  interesting is that this is a dial: the AR arm has no equivalent, since its step count *is* its
  length. One forward pass per step, so cost is linear in it and independent of sequence length.
* **A4 — unmasking schedule (random vs. confidence-based).** ``schedule``.

**Why both schedules unmask the same number of positions per step.** The linear absorbing schedule
leaves ``L * t`` positions masked at time *t*, so walking *t* from 1 to 0 in ``steps`` equal
decrements fixes how many positions are outstanding after each step; what A4 varies is *which*
ones. Drawing the count as well — one Bernoulli per masked position, which is the exact ancestral
sampler for this chain — would make the two schedules differ in two things at once and the
ablation would not be measuring what it names. The cost of fixing the count is that ``random`` is
a fixed-count approximation to the exact reverse process rather than the process itself, and the
report has to say so: it is the same class of statement as §4.3's "the diffusion arm's number is a
bound", made about the decoder instead of the objective.

**A diffusion decode has to be told how long its answer is.** The canvas is fixed before the first
forward pass; there is no EOS to stop at, because stopping is not a thing this process does. The
AR arm chooses its own length. That asymmetry is real, it is not a defect of either arm, and it
lands on any metric computed against a gold string of known length — see :mod:`ravaan.sampling`.
"""

from __future__ import annotations

from collections.abc import Sequence

import torch
from torch import Tensor, nn

from ravaan.sampling.decoding import Generation, SamplingConfig, build_generator, sample_ids

SCHEDULES = ("random", "confidence")


def unmask_counts(total: int, steps: int) -> list[int]:
    """How many positions each step commits, for ``total`` masked positions over ``steps``.

    ``round(total * t)`` outstanding after each step, differenced. Sums to ``total`` exactly and
    leaves nothing masked at the end for any ``steps >= 1`` — including ``steps > total``, where
    some steps commit nothing and the run is simply wasteful rather than wrong, and
    ``steps < total``, where each step commits several positions at once and they are sampled
    independently of each other. That independence is the whole of what A3 measures.
    """
    if steps < 1:
        raise ValueError(f"steps must be at least 1, got {steps}")
    counts, outstanding = [], total
    for step in range(1, steps + 1):
        target = round(total * (1.0 - step / steps))
        counts.append(outstanding - target)
        outstanding = target
    return counts


@torch.no_grad()
def sample_diffusion(
    model: nn.Module,
    tokens: Tensor | Sequence[Sequence[int]],
    *,
    steps: int = 32,
    schedule: str = "confidence",
    locked: Tensor | None = None,
    config: SamplingConfig | None = None,
    forbid: Sequence[int] = (),
    generator: torch.Generator | None = None,
) -> Generation:
    """Denoise ``tokens`` into a complete sequence. Positions holding `<mask>` are the ones filled.

    ``locked`` overrides that: True marks a position the decoder is given and must not touch, and
    everything else is re-absorbed to `<mask>` before the first step, so a caller can hand in a
    clean sequence plus a span to regenerate rather than having to mask it itself.

    The model's own `<mask>` is added to ``forbid`` whether the caller passed it or not. That is
    not a convenience: writing the absorbing state back is not a decode, so a schedule that
    "committed" one would silently return a canvas with holes in it — which is exactly what the
    first run of this function did, and what the terminating assertion below now catches. The AR
    decoder has no equivalent because it has no absorbing state; `<mask>` is forbidden there for
    the weaker reason that it was never a target, and that is the caller's to pass.

    Returns the same :class:`~ravaan.sampling.decoding.Generation` the AR decoder does, so a
    caller that reads both arms does not branch on which one it asked.
    """
    if schedule not in SCHEDULES:
        raise ValueError(f"schedule must be one of {SCHEDULES}, got {schedule!r}")
    mask_id = getattr(model, "mask_id", None)
    if mask_id is None:
        raise ValueError(
            "sample_diffusion needs the model's absorbing state — pass a RavaanDiffusion, not a "
            "bare backbone. A decoder pointed at the wrong mask id produces fluent nonsense with "
            "no symptom, which is why `RavaanDiffusion` takes it as a required argument too"
        )

    config = config or SamplingConfig()
    device = next(model.parameters()).device
    if not isinstance(tokens, Tensor):
        tokens = torch.tensor([list(row) for row in tokens], dtype=torch.long)
    tokens = tokens.to(device=device, dtype=torch.long)
    if tokens.ndim == 1:
        tokens = tokens.unsqueeze(0)
    if tokens.ndim != 2 or tokens.shape[1] == 0:
        raise ValueError(f"expected a non-empty (batch, length) canvas, got {tuple(tokens.shape)}")
    tokens = tokens.clone()

    limit = getattr(getattr(model, "config", None), "context_length", tokens.shape[1])
    if tokens.shape[1] > limit:
        raise ValueError(
            f"canvas of {tokens.shape[1]} tokens exceeds §5's context length of {limit}"
        )

    if locked is None:
        locked = tokens != mask_id
    else:
        locked = locked.to(device=device, dtype=torch.bool)
        if locked.shape != tokens.shape:
            raise ValueError(f"locked {tuple(locked.shape)} does not match {tuple(tokens.shape)}")
        tokens = torch.where(locked, tokens, torch.full_like(tokens, mask_id))
    given = tokens.clone()

    forbid = tuple(dict.fromkeys((*(int(i) for i in forbid), int(mask_id))))

    generator = generator or build_generator(device, config.seed)
    was_training = model.training
    model.eval()

    masked = ~locked
    per_row = masked.sum(dim=-1)
    # One schedule for the batch, sized by the widest row. A row with fewer masked positions
    # finishes early and its later steps commit nothing; the alternative — a per-row step count —
    # would mean two rows in one batch were decoded under different A3 settings.
    schedule_counts = unmask_counts(int(per_row.max().item()), steps)
    positions = (
        torch.arange(tokens.shape[1], device=device)
        .unsqueeze(0)
        .expand_as(tokens)
        .contiguous()
    )

    forwards = 0
    try:
        for take in schedule_counts:
            if take <= 0 or not bool(masked.any()):
                continue
            logits = model(tokens)
            forwards += 1
            ids, confidence = sample_ids(logits, config, generator=generator, forbid=forbid)

            if schedule == "confidence":
                score = confidence.masked_fill(~masked, float("-inf"))
            else:
                draw = torch.rand(tokens.shape, device=device, generator=generator)
                score = draw.masked_fill(~masked, float("-inf"))

            order = score.argsort(dim=-1, descending=True)
            rank = torch.empty_like(order)
            rank.scatter_(1, order, positions)
            # `take` is the batch-wide quota; a row with fewer masked positions left commits only
            # what it has, which `& masked` enforces.
            commit = (rank < take) & masked
            tokens = torch.where(commit, ids, tokens)
            masked = masked & ~commit
    finally:
        model.train(was_training)

    # §8.1's two invariants, asserted rather than described. The first is the one §4.1 calls
    # architectural — "you simply don't unmask those positions" — and this loop is where it would
    # be lost; the second is what `forbid` exists for, and a mask left standing is a position the
    # decoder silently declined to decode.
    if not torch.equal(tokens[locked], given[locked]):
        raise AssertionError("§8.1: the diffusion decoder overwrote a locked position")
    left = int((tokens == mask_id).sum().item())
    if left:
        raise AssertionError(
            f"§8.1: {left} positions are still `<mask>` after {steps} steps — the schedule did "
            "not cover the canvas, or the decoder was allowed to emit the absorbing state"
        )

    lengths = torch.full((tokens.shape[0],), tokens.shape[1], dtype=torch.long, device=device)
    return Generation(
        tokens=tokens,
        locked=locked,
        lengths=lengths,
        forwards=forwards,
        arm="diff",
        detail={
            "steps": steps,
            "schedule": schedule,
            "masked_positions": int(per_row.max().item()),
            **config.to_dict(),
        },
    )


__all__ = ["SCHEDULES", "sample_diffusion", "unmask_counts"]
