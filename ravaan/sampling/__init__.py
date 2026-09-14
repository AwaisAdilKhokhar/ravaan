"""Decoding: AR sampling and diffusion denoising schedules (ablations A3, A4).

Built in session 22, and the thing G3's second half had been waiting on: the pilot run finished on
2026-09-13 with seven checkpoints per arm on disk and **nothing in the repository able to read a
token out of one**. "20M pilot DIFF produces coherent Urdu after 50 epochs" is not a number, it is
a reader looking at text, and the text did not exist.

Four pieces, and the split follows what is shared rather than what is convenient:

* :mod:`ravaan.sampling.decoding` — logits to tokens. Temperature, top-k, top-p, the ids neither
  arm may emit, and the seeded generator §8.1's determinism invariant rests on. **Both arms**, for
  the same reason both arms share one backbone: a comparison whose decoders disagreed would be
  measuring the decoders.
* :mod:`ravaan.sampling.ar` — left to right until EOS or the context ends.
* :mod:`ravaan.sampling.diffusion` — iterative unmasking, carrying §4.4's A3 (steps) and A4
  (random vs. confidence) as two arguments, plus the ``gumbel`` schedule session 23 added between
  A4's two after both were measured and both failed, in opposite directions.
* :mod:`ravaan.sampling.prompts` — §4.2's five framings, rebuilt for inference. A model trained on
  `<lm>`-prefixed sequences and prompted with bare text is being asked a question it was never
  taught.

**The one asymmetry, stated here because it will otherwise be discovered inside a results table.**
A diffusion decode is handed the width of its answer before its first forward pass; an AR decode
chooses its own and stops at EOS. §4.1 matches the arms on everything it can and cannot match them
on this — it is a property of the factorization, not a defect of either implementation. So every
conditional metric in §8.3 scored against a gold string of known length gives the diffusion arm a
hint the AR arm has to infer, and infill exact-match is where it will be largest.
:attr:`~ravaan.sampling.prompts.Prompt.hinted_length` records the size of the hint, and the report
must carry it next to any number computed from these prompts.
"""

from __future__ import annotations

from collections.abc import Sequence

import torch
from torch import nn

from ravaan.sampling.ar import sample_ar
from ravaan.sampling.checkpoint import LoadedArm, load_arm
from ravaan.sampling.decoding import (
    Generation,
    SamplingConfig,
    build_generator,
    filter_logits,
    restrict,
    sample_ids,
)
from ravaan.sampling.diffusion import SCHEDULES, sample_diffusion, unmask_counts
from ravaan.sampling.prompts import Prompt


def generate(
    model: nn.Module,
    prompt: Prompt,
    *,
    config: SamplingConfig | None = None,
    max_new_tokens: int | None = None,
    steps: int = 32,
    schedule: str = "confidence",
    gumbel: float = 1.0,
    forbid: Sequence[int] = (),
    eos_id: int | None = None,
    generator: torch.Generator | None = None,
) -> Generation:
    """Decode one :class:`~ravaan.sampling.prompts.Prompt` with whichever arm built it.

    The dispatch is on ``prompt.arm`` rather than on the model, so a prompt framed for one arm and
    handed to the other raises here instead of producing a plausible-looking sample of the wrong
    experiment. ``steps``, ``schedule`` and ``gumbel`` are ignored by the AR arm and
    ``max_new_tokens`` by the diffusion one — each is meaningless on the other side, and silently
    accepting both is what lets an ablation sweep a knob that is not connected to anything.
    """
    arm = "ar" if getattr(getattr(model, "config", None), "causal", True) else "diff"
    if arm != prompt.arm:
        raise ValueError(
            f"a {prompt.arm!r} prompt was handed to the {arm!r} model — the framings differ "
            "(§4.1's infilling row is a rearrangement on one side and a hole on the other), so "
            "this would sample a question the model was never trained on"
        )
    if prompt.arm == "ar":
        if max_new_tokens is None:
            raise ValueError("the AR arm needs max_new_tokens — nothing else bounds the decode")
        return sample_ar(
            model,
            [list(prompt.tokens)],
            max_new_tokens=max_new_tokens,
            config=config,
            forbid=forbid,
            eos_id=eos_id,
            generator=generator,
        )
    return sample_diffusion(
        model,
        [list(prompt.tokens)],
        locked=torch.tensor([list(prompt.locked)], dtype=torch.bool),
        steps=steps,
        schedule=schedule,
        gumbel=gumbel,
        config=config,
        forbid=forbid,
        generator=generator,
    )


__all__ = [
    "SCHEDULES",
    "Generation",
    "LoadedArm",
    "Prompt",
    "SamplingConfig",
    "build_generator",
    "filter_logits",
    "generate",
    "load_arm",
    "restrict",
    "sample_ar",
    "sample_diffusion",
    "sample_ids",
    "unmask_counts",
]
