"""Rebuilding a trained arm from a checkpoint, without a trainer (PRD §8, §8.1).

:meth:`~ravaan.training.loop.Trainer.load` restores a run — model, optimizer, RNG, step count —
because that is what resuming needs. Reading a checkpoint needs less and needs it from a cold
start: no corpus, no optimizer, no batch size. This is that path.

**Everything comes off the checkpoint.** ``model_config`` says which rung of §5's ladder and, in
``causal``, which arm; ``tokenizer`` is the corpus manifest's own record, so the mask id and the
twelve framing pieces are the ones the corpus was packed with rather than the ones a driver
happened to have on disk. A sampler pointed at a different `<mask>` than the model trained under
produces confident, fluent, wrong output with no symptom anywhere — the same failure
:class:`~ravaan.models.diffusion.RavaanDiffusion` takes a required argument to avoid, and the
reason nothing here accepts an override.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn

from ravaan.models.ar import RavaanAR
from ravaan.models.config import ModelConfig
from ravaan.models.diffusion import RavaanDiffusion
from ravaan.training.tasks import FramingTokens


@dataclass(frozen=True, slots=True)
class LoadedArm:
    """A trained arm, ready to decode, and everything a prompt builder needs to address it."""

    model: nn.Module
    arm: str
    mask_id: int
    framing: FramingTokens
    eos_id: int
    tokenizer: dict
    model_config: ModelConfig
    state: dict
    fraction: float | None
    path: Path

    @property
    def forbidden(self) -> tuple[int, ...]:
        """`<mask>` and `<pad>` — see :mod:`ravaan.sampling.decoding` for why each."""
        return (self.mask_id, self.framing.pad)

    def describe(self) -> str:
        step = self.state.get("step", 0)
        tokens = self.state.get("tokens", 0)
        fraction = "?" if self.fraction is None else f"{self.fraction:g}"
        return (
            f"{self.arm.upper()} from {self.path.name} — fraction {fraction}, step {step:,}, "
            f"{tokens:,} tokens, {self.model_config.n_layers}L/{self.model_config.d_model}d, "
            f"tokenizer {self.tokenizer.get('fingerprint')}"
        )


def load_arm(path: str | Path, *, device: str | torch.device = "cpu") -> LoadedArm:
    """Build the arm this checkpoint holds and load its weights. No optimizer, no corpus."""
    path = Path(path)
    payload = torch.load(path, map_location=torch.device(device), weights_only=False)
    for key in ("model", "model_config", "tokenizer"):
        if key not in payload:
            raise ValueError(
                f"{path} has no {key!r} — checkpoints written before session 19 predate §5's "
                "model and cannot be sampled from"
            )

    config = ModelConfig.from_dict(payload["model_config"])
    tokenizer = payload["tokenizer"]
    special = tokenizer.get("special_tokens") or {}
    if "<mask>" not in special:
        raise ValueError(
            f"{path}'s manifest names no `<mask>` piece. §7 put the absorbing state inside the "
            "16,384 so both arms embed one vocabulary; a checkpoint without it was packed by "
            "something else"
        )
    mask_id = int(special["<mask>"])
    framing = FramingTokens.from_manifest(tokenizer)

    arm = "ar" if config.causal else "diff"
    model = RavaanAR(config) if arm == "ar" else RavaanDiffusion(mask_id, config)
    model.load_state_dict(payload["model"])
    model.to(torch.device(device)).eval()

    return LoadedArm(
        model=model,
        arm=arm,
        mask_id=mask_id,
        framing=framing,
        eos_id=int((tokenizer.get("control_ids") or {}).get("eos", tokenizer.get("eos_id", 3))),
        tokenizer=tokenizer,
        model_config=config,
        state=dict(payload.get("state") or {}),
        fraction=payload.get("fraction"),
        path=path,
    )


__all__ = ["LoadedArm", "load_arm"]
