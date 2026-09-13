"""Logits to tokens — the half of decoding both arms share (PRD §8, §4.4).

Neither arm's decoder is allowed to have its own opinion about temperature, top-k or top-p. §4.1's
claim is that the two models differ in exactly one thing, and a comparison whose *inference* paths
disagreed about how a distribution becomes a token would be measuring the decoders as much as the
models — the same argument that put one backbone behind both arms puts one sampler under both of
them. `ravaan.sampling.ar` and `ravaan.sampling.diffusion` differ in which positions they write and
in what order; what happens at a position, once its logits exist, happens here.

**What the decoders may never emit.** `<mask>` is an absorbing state: a diffusion step that writes
it back has not decoded that position, and the AR arm never saw it as a target at all, so its
logit is whatever an untrained embedding row happens to give. `<pad>` is the tail of §4.2's pair
framings and carries :data:`~ravaan.models.ar.IGNORE_INDEX` in the labels, so it is never a target
either. Both are refused by default rather than left to the model, because the failure mode of not
refusing them — a position stuck masked forever, or a sequence that decodes to nothing — reads as
"the model is bad" rather than as "the decoder emitted a token no objective ever scored".

**Determinism is §8.1's invariant, not a convenience.** Every draw goes through an explicit
:class:`torch.Generator` and a run is reproducible from ``SamplingConfig.seed`` alone. Nothing here
touches global RNG state, so a sampling call in the middle of a training run cannot move the
trajectory.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

import torch
from torch import Tensor

#: Temperature at or below this is treated as greedy. Not exactly zero, because a caller that
#: computes a temperature — an annealing schedule, say — should reach argmax at the bottom of its
#: range rather than a division that overflows to inf and turns a tie into a NaN.
GREEDY_BELOW = 1e-5


@dataclass(frozen=True, slots=True)
class SamplingConfig:
    """How a distribution becomes a token. Shared by both arms; §4.4's A3/A4 knobs are not here.

    Steps and unmasking schedule are arguments to
    :func:`~ravaan.sampling.diffusion.sample_diffusion` rather than fields of this config, so an
    ablation that sweeps them is visibly a sweep at the call site, and a config built for the AR
    arm cannot silently carry a diffusion setting it will never use.
    """

    temperature: float = 1.0
    #: 0 disables. Applied before top-p, which is the usual order and the only one where the two
    #: compose predictably: top-k bounds the candidate set, top-p then trims it by mass.
    top_k: int = 0
    top_p: float = 1.0
    seed: int = 0

    def __post_init__(self) -> None:
        if self.temperature < 0:
            raise ValueError(f"temperature must be non-negative, got {self.temperature}")
        if self.top_k < 0:
            raise ValueError(f"top_k must be non-negative (0 disables), got {self.top_k}")
        if not 0 < self.top_p <= 1:
            raise ValueError(f"top_p must be in (0, 1], got {self.top_p}")

    @property
    def greedy(self) -> bool:
        return self.temperature <= GREEDY_BELOW

    def to_dict(self) -> dict:
        return {
            "temperature": self.temperature,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "seed": self.seed,
        }


@dataclass(frozen=True, slots=True)
class Generation:
    """What a decoder returns: the sequence, and what of it the decoder actually wrote.

    ``locked`` is §8.1's invariant in data form — True at every position the decoder was given and
    is forbidden to touch. Both decoders assert it against the tokens they return rather than
    documenting it, because locked-token preservation is the one thing v1 reported as a result
    that is really an architectural property (§8.1), and a property is worth an assertion.

    ``lengths`` is how many tokens each row *means*, which is not ``tokens.shape[1]``: the AR
    decoder stops a row at EOS and keeps stepping for the rest of the batch, and a reader that
    ignores this gets the tail of a finished sentence repeated.
    """

    tokens: Tensor
    locked: Tensor
    lengths: Tensor
    forwards: int
    arm: str
    detail: dict = field(default_factory=dict)

    def rows(self) -> list[list[int]]:
        """Each row trimmed to its own length. The form a tokenizer wants."""
        return [
            self.tokens[i, : int(self.lengths[i])].tolist() for i in range(self.tokens.shape[0])
        ]

    def written(self) -> list[list[int]]:
        """Only the positions the decoder wrote — the generation, without what it was given."""
        out = []
        for i in range(self.tokens.shape[0]):
            limit = int(self.lengths[i])
            free = ~self.locked[i, :limit]
            out.append(self.tokens[i, :limit][free].tolist())
        return out


def restrict(logits: Tensor, forbid: Iterable[int]) -> Tensor:
    """Push every id in ``forbid`` below all the others. Returns a new tensor."""
    ids = [int(i) for i in forbid]
    if not ids:
        return logits
    index = torch.tensor(ids, device=logits.device, dtype=torch.long)
    return logits.index_fill(-1, index, float("-inf"))


def filter_logits(logits: Tensor, config: SamplingConfig) -> Tensor:
    """Temperature, then top-k, then top-p. ``(..., vocab)`` in, ``(..., vocab)`` out.

    Greedy is handled by :func:`sample_ids` rather than by dividing by a tiny temperature — see
    :data:`GREEDY_BELOW`.
    """
    out = logits.float()
    if not config.greedy:
        out = out / config.temperature

    if config.top_k:
        k = min(config.top_k, out.shape[-1])
        floor = out.topk(k, dim=-1).values[..., -1:]
        out = out.masked_fill(out < floor, float("-inf"))

    if config.top_p < 1.0:
        ordered, index = out.sort(dim=-1, descending=True)
        probabilities = ordered.softmax(dim=-1)
        # Drop a token when the mass *before* it has already reached top_p, so the most likely
        # token always survives even when it alone exceeds the threshold. The subtraction is what
        # makes that true; a plain `cumsum >= top_p` would empty the candidate set at low top_p on
        # a confident distribution, which is precisely where sampling matters least and breaks
        # most loudly.
        drop = probabilities.cumsum(dim=-1) - probabilities >= config.top_p
        out = out.masked_fill(drop.scatter(-1, index, drop), float("-inf"))
    return out


def sample_ids(
    logits: Tensor,
    config: SamplingConfig,
    *,
    generator: torch.Generator | None = None,
    forbid: Sequence[int] = (),
) -> tuple[Tensor, Tensor]:
    """``(ids, confidence)`` for a ``(..., vocab)`` block of logits.

    ``confidence`` is the post-filter probability of the id that was actually chosen, not the
    maximum — §4.4's confidence-based schedule commits the tokens it is most sure of, and what it
    commits is the sample. Under greedy decoding the two coincide; under top-p they do not, and
    ranking by the maximum would let a position whose confident candidate the sampler *declined*
    jump the queue.

    **Greedy does not report 1.0.** The temperature division is skipped rather than taken to zero
    (see :data:`GREEDY_BELOW`), so the probability returned is the model's own for that token. It
    has to be: A4's confidence schedule ranks positions against each other, and a decoder that
    reported certainty everywhere would degrade that schedule to whatever order `argsort` happens
    to produce — which would then be compared against `random` and found to be the same thing.

    **Forbidding happens before filtering, and the order is load-bearing.** Filtering first and
    striking the forbidden ids afterwards leaves an all-`-inf` row wherever top-k or top-p had
    already narrowed the candidates down to forbidden ones — a NaN, and on CUDA a device-side
    assertion inside `multinomial` rather than an error naming the cause. Striking first means the
    nucleus is chosen from tokens the decoder is allowed to emit, which is also what the caller
    asking for top-p 0.95 meant: 95% of the mass it is *choosing between*.
    """
    filtered = filter_logits(restrict(logits, forbid), config)
    probabilities = filtered.softmax(dim=-1)
    if config.greedy:
        ids = probabilities.argmax(dim=-1)
    else:
        flat = probabilities.reshape(-1, probabilities.shape[-1])
        ids = torch.multinomial(flat, num_samples=1, generator=generator).view(
            probabilities.shape[:-1]
        )
    confidence = probabilities.gather(-1, ids.unsqueeze(-1)).squeeze(-1)
    return ids, confidence


def build_generator(device: torch.device | str, seed: int) -> torch.Generator:
    """A generator on ``device``, seeded. The only randomness either decoder is allowed."""
    return torch.Generator(device=torch.device(device)).manual_seed(int(seed))


__all__ = [
    "GREEDY_BELOW",
    "Generation",
    "SamplingConfig",
    "build_generator",
    "filter_logits",
    "restrict",
    "sample_ids",
]
