"""Ravaan-AR — next-token prediction over §5's backbone (PRD §4.1).

The plain half of the matched pair, and deliberately unremarkable: causal attention, shift by one,
cross-entropy. Everything interesting about this arm is in what it is *not* missing — §4.1's FIM
row is the fix for v1's central flaw, and it lives in the task generator rather than here, because
FIM is a rearrangement of the sequence and not a change to the objective. This module would not
know an infilling batch from a plain one, which is the point: A2 ("AR without FIM") is then a
change to the data mixture and not to the model, so the ablation measures what it says it does.

Returns exact NLL. §4.3 requires this be reported next to the diffusion arm's ELBO with the bound
stated explicitly — the comparison is conservative in diffusion's disfavour, and the report must
say so rather than letting the reader assume the two numbers are the same kind of number.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn.functional as F  # noqa: N812
from torch import Tensor, nn

from ravaan.models.backbone import RavaanTransformer
from ravaan.models.config import ModelConfig

# Stage 10 packs without padding, so a label of -100 only appears where a task framing says
# "predict nothing here" — the source half of a transliteration pair, for instance.
IGNORE_INDEX = -100


@dataclass(frozen=True, slots=True)
class LossOutput:
    """What both arms return, so the training loop does not branch on the objective.

    ``loss`` is what gets a backward pass. ``nats`` is the per-token quantity the curves are
    drawn from — for AR the exact NLL, for diffusion the ELBO — and ``tokens`` is what it was
    averaged over, so a distributed or gradient-accumulated run can re-weight correctly instead
    of averaging averages.

    ``scored`` is the denominator ``nats`` was divided by, and the two arms do not agree on it:
    AR's ``tokens`` *is* its denominator, while the diffusion arm counts masked positions in
    ``tokens`` and divides by every position the bound covers. §8.3's bits-per-byte needs the
    denominator, not the count — ``nats * scored`` is the sequence total for either arm, and
    multiplying by the raw sequence length instead over-states AR's total by ``L/(L-1)`` on plain
    text and by far more than that on §4.2's conditional framings, where most of the sequence is
    a source the model was handed.
    """

    loss: Tensor
    nats: Tensor
    tokens: Tensor
    scored: Tensor

    @property
    def bits_per_token(self) -> Tensor:
        return self.nats / torch.log(torch.tensor(2.0, device=self.nats.device))


class RavaanAR(nn.Module):
    """§5's backbone with causal attention and a next-token objective."""

    def __init__(self, config: ModelConfig | None = None) -> None:
        super().__init__()
        config = (config or ModelConfig()).as_ar()
        if not config.causal:
            raise ValueError("Ravaan-AR requires causal attention (§4.1)")
        self.config = config
        self.backbone = RavaanTransformer(config)

    def forward(self, tokens: Tensor, padding_mask: Tensor | None = None) -> Tensor:
        return self.backbone(tokens, padding_mask)

    def loss(
        self,
        tokens: Tensor,
        labels: Tensor | None = None,
        padding_mask: Tensor | None = None,
    ) -> LossOutput:
        """Shift-by-one cross-entropy.

        ``labels`` defaults to ``tokens`` — the plain-LM case. A task framing that wants the loss
        on part of the sequence only (§4.1's "loss on target" for transliteration) passes labels
        with :data:`IGNORE_INDEX` everywhere the model is being conditioned rather than tested.
        """
        labels = tokens if labels is None else labels
        logits = self.backbone(tokens, padding_mask)
        predicted = logits[:, :-1].reshape(-1, logits.shape[-1])
        target = labels[:, 1:].reshape(-1)

        total = F.cross_entropy(
            predicted.float(), target, ignore_index=IGNORE_INDEX, reduction="sum"
        )
        counted = (target != IGNORE_INDEX).sum()
        # A batch can legitimately be all-ignore under a task framing that conditions on
        # everything; returning a NaN there would poison the running average rather than
        # contributing nothing to it.
        safe = counted.clamp(min=1)
        return LossOutput(loss=total / safe, nats=total / safe, tokens=counted, scored=counted)


__all__ = ["IGNORE_INDEX", "LossOutput", "RavaanAR"]
