"""Ravaan-AR's decoder — left to right, one token at a time (PRD §8).

Deliberately unremarkable, in the same way `ravaan.models.ar` is: causal attention already says
what order the tokens come in, so there is no schedule to choose and §4.4 has no ablation on this
side. The whole module is a loop.

**No KV cache, on purpose.** Caching keys and values would make this 512-step loop roughly O(L)
instead of O(L²) forwards, and it would do it by adding an inference path through
:class:`~ravaan.models.backbone.Attention` that the diffusion arm cannot use and that training
never exercises. §4.1's matched pair is held together by there being exactly one attention
implementation; buying inference speed with a second one, for a project whose entire decoding
workload is a few hundred sequences at a 512-token context, is the wrong trade. If §8.4's human
evaluation ever needs thousands of generations, cache then — and test that the cached path gives
bit-identical logits to this one before believing anything it produces.

**Where the batch has to be square.** Prompts must all be the same length. A ragged batch would
need left-padding, which shifts every RoPE position by a per-row offset — defensible, standard,
and *not* something this project has measured, so a decoder that did it quietly would be putting
an untested positional-encoding variant underneath every generation in the report. Callers with
ragged prompts loop; at this scale that costs nothing worth having a subtlety for.
"""

from __future__ import annotations

from collections.abc import Sequence

import torch
from torch import Tensor, nn

from ravaan.sampling.decoding import Generation, SamplingConfig, build_generator, sample_ids


def _as_prompt(prompt: Tensor | Sequence[Sequence[int]], device: torch.device) -> Tensor:
    if isinstance(prompt, Tensor):
        tokens = prompt.to(device=device, dtype=torch.long)
    else:
        rows = [list(row) for row in prompt]
        widths = {len(row) for row in rows}
        if len(widths) > 1:
            raise ValueError(
                f"sample_ar needs prompts of one length and got {sorted(widths)} — left-padding "
                "would shift RoPE positions per row, which nothing in this project has measured. "
                "Loop over the prompts instead"
            )
        tokens = torch.tensor(rows, dtype=torch.long, device=device)
    if tokens.ndim == 1:
        tokens = tokens.unsqueeze(0)
    if tokens.ndim != 2 or tokens.shape[1] == 0:
        raise ValueError(f"expected a non-empty (batch, length) prompt, got {tuple(tokens.shape)}")
    return tokens


@torch.no_grad()
def sample_ar(
    model: nn.Module,
    prompt: Tensor | Sequence[Sequence[int]],
    *,
    max_new_tokens: int,
    config: SamplingConfig | None = None,
    forbid: Sequence[int] = (),
    eos_id: int | None = None,
    generator: torch.Generator | None = None,
) -> Generation:
    """Continue ``prompt`` by up to ``max_new_tokens``. The prompt is never rewritten.

    ``eos_id`` stops a row. The row keeps being stepped — the batch moves together — but its
    emitted tokens are pinned to EOS and :attr:`Generation.lengths` records where it actually
    ended, so a reader never sees the tail of a finished sentence run on.

    Stops early, for the whole batch, when every row has ended or when the sequence reaches §5's
    context length. ``detail["stop"]`` says which, because "the sample looks truncated" and "the
    model would not stop" are different findings and the difference is not visible in the text.
    """
    config = config or SamplingConfig()
    device = next(model.parameters()).device
    tokens = _as_prompt(prompt, device)
    batch, width = tokens.shape

    context = getattr(model, "config", None)
    limit = getattr(context, "context_length", width + max_new_tokens)
    if width > limit:
        raise ValueError(f"prompt of {width} tokens exceeds §5's context length of {limit}")
    budget = min(max_new_tokens, limit - width)

    generator = generator or build_generator(device, config.seed)
    was_training = model.training
    model.eval()

    locked = torch.zeros((batch, width + budget), dtype=torch.bool, device=device)
    locked[:, :width] = True
    finished = torch.zeros(batch, dtype=torch.bool, device=device)
    lengths = torch.full((batch,), width, dtype=torch.long, device=device)

    forwards = 0
    stop = "budget"
    try:
        for _ in range(budget):
            logits = model(tokens)[:, -1]
            forwards += 1
            ids, _ = sample_ids(logits, config, generator=generator, forbid=forbid)
            if eos_id is not None:
                # A finished row emits EOS forever. Cheaper than masking it out of the forward,
                # and it keeps `tokens` a valid sequence rather than one with holes in it.
                ids = torch.where(finished, torch.full_like(ids, eos_id), ids)
            tokens = torch.cat([tokens, ids.unsqueeze(1)], dim=1)
            lengths = lengths + (~finished).long()
            if eos_id is not None:
                finished = finished | (ids == eos_id)
                if bool(finished.all()):
                    stop = "eos"
                    break
    finally:
        model.train(was_training)

    locked = locked[:, : tokens.shape[1]]
    if tokens.shape[1] >= limit and stop == "budget":
        stop = "context"
    # §8.1: the prompt is a locked span and the decoder only ever appended. Asserted rather than
    # trusted — this is the invariant, and the loop above is where it would be lost.
    given = _as_prompt(prompt, device)
    if not torch.equal(tokens[:, :width], given):
        raise AssertionError("§8.1: the AR decoder overwrote its prompt")

    return Generation(
        tokens=tokens,
        locked=locked,
        lengths=lengths,
        forwards=forwards,
        arm="ar",
        detail={"stop": stop, "max_new_tokens": max_new_tokens, **config.to_dict()},
    )


__all__ = ["sample_ar"]
