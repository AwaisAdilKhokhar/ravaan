"""Ravaan-DIFF — time-agnostic masked diffusion over §5's backbone (PRD §4.1).

MDLM's absorbing-state formulation, with the timestep embedding deliberately absent. §4.1 chooses
this over DiT-style adaLN conditioning for two reasons and the first one is the experiment's: no
timestep embedding means **no parameters on this side that the AR side does not have**, so §5's
"within 2%" is exactly 0% and `assert_matched` can insist on it. The second is that a
time-agnostic model is simply less to get wrong.

**The objective, and why the weight is 1/t.** Under the linear absorbing schedule a token survives
to time *t* with probability ``1 - t``, so a sequence at time *t* has each position masked
independently with probability *t*. The continuous-time NELBO for this process reduces to::

    E_{t ~ U(0,1)}  (1/t) * sum over masked positions of  -log p(x_i | x_t)

which is what :meth:`RavaanDiffusion.loss` computes. The ``1/t`` is not a heuristic reweighting —
it is the ratio ``alpha'_t / (1 - alpha_t)`` for this schedule, and dropping it would produce a
number that is not a bound on anything.

**This is an upper bound on NLL, not NLL.** §4.3 requires the report to say so in as many words:
the diffusion arm's ELBO is compared against the AR arm's exact likelihood, the comparison is
therefore conservative *against* diffusion, and downstream task metrics — which are directly
comparable — are the tiebreaker. A results table that presents the two as the same quantity is
the error this docstring exists to prevent.

**One masking rate per sequence, not per batch.** Sampling a single *t* for the whole batch would
make the gradient's variance depend on the batch size in a way the ELBO does not account for, and
at §5's context length a batch is a small number of long sequences. Each sequence gets its own.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F  # noqa: N812
from torch import Tensor, nn

from ravaan.models.ar import IGNORE_INDEX, LossOutput
from ravaan.models.backbone import RavaanTransformer
from ravaan.models.config import ModelConfig


class RavaanDiffusion(nn.Module):
    """§5's backbone with bidirectional attention and the MDLM objective.

    ``mask_id`` is §7's ``<mask>`` piece. It is a required argument rather than a default because
    a diffusion model pointed at the wrong absorbing token trains perfectly happily and produces
    a corpus-shaped disaster — there is no downstream symptom, which is the same reason stage 10
    refuses a placeholder tokenizer rather than warning about one.
    """

    def __init__(self, mask_id: int, config: ModelConfig | None = None) -> None:
        super().__init__()
        config = (config or ModelConfig()).as_diffusion()
        if config.causal:
            raise ValueError("Ravaan-DIFF requires bidirectional attention (§4.1)")
        if not 0 <= mask_id < config.vocab_size:
            raise ValueError(
                f"mask_id {mask_id} is outside §5's vocabulary of {config.vocab_size} — the "
                "absorbing state has to be a token the model can embed"
            )
        self.config = config
        self.mask_id = mask_id
        self.backbone = RavaanTransformer(config)

    def forward(self, tokens: Tensor, padding_mask: Tensor | None = None) -> Tensor:
        return self.backbone(tokens, padding_mask)

    def corrupt(
        self,
        tokens: Tensor,
        t: Tensor,
        *,
        keep: Tensor | None = None,
        generator: torch.Generator | None = None,
    ) -> tuple[Tensor, Tensor]:
        """Absorb each position independently with probability ``t``. Returns ``(x_t, masked)``.

        ``keep`` marks positions the task framing conditions on and never masks — §4.1's
        "condition on unmasked source, diffuse the target". Those positions are excluded from the
        loss as well, which is what makes the conditional tasks the *same* tasks the AR arm sees.
        """
        probability = t.view(-1, *([1] * (tokens.ndim - 1))).expand_as(tokens.float())
        draw = torch.rand(tokens.shape, device=tokens.device, generator=generator)
        masked = draw < probability
        if keep is not None:
            masked = masked & ~keep
        return torch.where(masked, torch.full_like(tokens, self.mask_id), tokens), masked

    def loss(
        self,
        tokens: Tensor,
        labels: Tensor | None = None,
        padding_mask: Tensor | None = None,
        *,
        keep: Tensor | None = None,
        generator: torch.Generator | None = None,
        t_min: float = 1e-3,
    ) -> LossOutput:
        """The NELBO above, as a per-token average.

        ``t_min`` keeps the ``1/t`` finite. At t = 0 nothing is masked and the summand is empty,
        so the limit is well defined, but a sampled t of 1e-9 would multiply a single token's
        loss by a billion and blow the run up — this is the standard clamp and it biases the
        bound in the safe direction, making it looser rather than tighter.
        """
        labels = tokens if labels is None else labels
        batch = tokens.shape[0]
        t = torch.rand(batch, device=tokens.device, generator=generator).clamp(min=t_min, max=1.0)

        corrupted, masked = self.corrupt(tokens, t, keep=keep, generator=generator)
        if labels is not tokens:
            masked = masked & (labels != IGNORE_INDEX)

        logits = self.backbone(corrupted, padding_mask)
        per_token = F.cross_entropy(
            logits.float().reshape(-1, logits.shape[-1]),
            labels.reshape(-1),
            ignore_index=IGNORE_INDEX,
            reduction="none",
        ).view_as(labels)

        # Loss on masked positions only. An unmasked position is one the model was *given*; the
        # ELBO does not score it, and scoring it anyway would quietly turn this into a BERT-style
        # objective that no longer bounds a likelihood.
        per_sequence = (per_token * masked).sum(dim=-1)
        weighted = (per_sequence / t).sum()

        counted = masked.sum()
        # The number of positions the bound is spread over is every position the bound *covers*,
        # not the masked subset: the NELBO bounds the likelihood of all of them at once, and
        # dividing by the masked count would report a per-masked-token figure that is not
        # comparable with the AR arm's per-token NLL. §8.3's bits-per-byte depends on this line.
        #
        # Covered means maskable and scored: a position pinned by ``keep`` was *given* to the
        # model, so it is conditioning rather than something the bound says anything about, and a
        # position carrying IGNORE_INDEX was never in the objective. Under §4.2's framings that
        # makes the two arms agree on the denominator — a `<lm>`-marked sequence scores the same
        # 511 content positions in both — which the unframed path does not, where AR necessarily
        # omits the first token it has no context for.
        scoreable = labels != IGNORE_INDEX
        if keep is not None:
            scoreable = scoreable & ~keep
        scored = int(scoreable.sum().item()) or labels.numel()
        nelbo = weighted / scored
        return LossOutput(
            loss=nelbo,
            nats=nelbo,
            tokens=counted,
            scored=torch.as_tensor(scored, device=tokens.device),
        )


__all__ = ["RavaanDiffusion"]
