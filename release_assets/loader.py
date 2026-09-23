"""Load a released Ravaan model from `config.json` + `model.safetensors`.

The training checkpoints this repository was built from are pickles holding an optimizer, an RNG
state and a step count. A released model is none of that: it is weights, the model shape, and the
tokenizer record the corpus was packed under. This module is the cold-start path for that.

**The tokenizer record is not metadata, it is part of the model.** `<mask>` and §7's twelve
framing pieces are read from `config.json`, which carries the corpus manifest's own record. A
sampler pointed at a different `<mask>` than the model trained under produces confident, fluent,
wrong output with no symptom anywhere — so nothing here accepts an override for it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import torch
from safetensors.torch import load_file
from torch import nn

from ravaan_infer.framing import FramingTokens
from ravaan_infer.models.ar import RavaanAR
from ravaan_infer.models.config import ModelConfig
from ravaan_infer.models.diffusion import RavaanDiffusion


@dataclass(frozen=True)
class ReleasedModel:
    """A released arm, ready to decode, plus everything a prompt builder needs to address it."""

    model: nn.Module
    arm: str
    mask_id: int
    framing: FramingTokens
    eos_id: int
    config: ModelConfig
    tokenizer_path: Path
    release: dict

    @property
    def forbidden(self) -> tuple[int, ...]:
        """`<mask>` and `<pad>` — neither is ever a legitimate thing to emit."""
        return (self.mask_id, self.framing.pad)

    def describe(self) -> str:
        r = self.release
        return (
            f"{r.get('name')} — {self.arm.upper()} arm, {r.get('epochs')} epochs over "
            f"{r.get('unique_tokens', 0):,} unique tokens, held-out Urdu bpb "
            f"{r.get('validation_urdu_bpb')}"
        )


def load(path: str | Path = ".", *, device: str | torch.device = "cpu") -> ReleasedModel:
    """Build the arm this release holds and load its weights.

    ``path`` is the repository directory — the one holding ``config.json``, whether that is a
    local clone or a ``snapshot_download``.
    """
    path = Path(path)
    cfg_path = path / "config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"{cfg_path} not found — point `load` at the directory holding config.json"
        )
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    model_config = ModelConfig.from_dict(cfg["model"])
    tokenizer = cfg["tokenizer"]
    special = tokenizer.get("special_tokens") or {}
    if "<mask>" not in special:
        raise ValueError(
            "config.json names no `<mask>` piece. §7 put the absorbing state inside the 16,384 so "
            "both arms embed one vocabulary; a config without it describes a different model"
        )
    mask_id = int(special["<mask>"])
    framing = FramingTokens.from_manifest(tokenizer)

    arm = "ar" if model_config.causal else "diff"
    model = RavaanAR(model_config) if arm == "ar" else RavaanDiffusion(mask_id, model_config)
    model.load_state_dict(load_file(path / "model.safetensors"))
    model.to(torch.device(device)).eval()

    tok = path / "tokenizer" / "ravaan-16k.model"
    if not tok.exists():
        raise FileNotFoundError(f"{tok} not found — the release is incomplete")

    return ReleasedModel(
        model=model,
        arm=arm,
        mask_id=mask_id,
        framing=framing,
        eos_id=int((tokenizer.get("control_ids") or {}).get("eos", 3)),
        config=model_config,
        tokenizer_path=tok,
        release=cfg.get("release", {}),
    )


__all__ = ["ReleasedModel", "load"]
