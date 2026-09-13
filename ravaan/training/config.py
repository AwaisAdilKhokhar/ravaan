"""Training configuration — PRD §4.3, §9, and preregistration §6.

**Every number here is a commitment, not a default.** Preregistration §6 says it in as many
words: *"hyperparameters are chosen once, from the reference paper's configuration, and are not
tuned for either model … No hyperparameter sweep will be run for either arm."* So the useful
property of this module is not that the values are good, it is that they are **fixed, shared by
both arms, and attributed** — which is why every one of them carries its source in
:data:`PROVENANCE` rather than in a git blame.

progress.md's carried-forward note asks for exactly this and asks for it *now*: "Record the source
when the training config is written in Week 6 — not retroactively."

⚠️ **One thing is owed before a paid run.** The values below follow Muennighoff et al.'s
data-constrained scaling setup as the reference paper adopts it, at the conventional Chinchilla
settings for a model this size. The *shape* is certainly right — AdamW, cosine to 10%, linear
warmup, grad clip 1.0, decoupled decay off norms and embeddings — and `weight_decay`, `betas` and
`grad_clip` are that literature's near-universal values. **`peak_lr`, `warmup_steps` and
`tokens_per_step` should be checked against the reference paper's table and pinned before Stage C**,
and :data:`PROVENANCE` marks which those are. That check is a reading task, not a sweep; doing it
after a run has started would be tuning, which §6 forbids.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

# §4.3: "Checkpoint at 1, 2, 5, 10, 25, 50, 100% of tokens processed — identical fractions for
# both models and both arms, so the curves share a compute x-axis. Evaluate every checkpoint."
CHECKPOINT_FRACTIONS: tuple[float, ...] = (0.01, 0.02, 0.05, 0.10, 0.25, 0.50, 1.00)

PROVENANCE: dict[str, str] = {
    "peak_lr": "⚠️ Chinchilla convention at this scale; CONFIRM against the reference paper",
    "min_lr_ratio": "Chinchilla/GPT-3 convention: cosine decays to 10% of peak",
    "warmup_steps": "⚠️ conventional ~1% of total steps; CONFIRM against the reference paper",
    "tokens_per_step": "⚠️ conventional for ~70M params; CONFIRM against the reference paper",
    "betas": "AdamW (0.9, 0.95) — Muennighoff et al. / Chinchilla / GPT-3, universal at this scale",
    "weight_decay": "0.1, decoupled, not applied to norms or embeddings — same lineage",
    "grad_clip": "1.0 — same lineage",
    "eps": "1e-8 — AdamW default",
    "precision": "PRD §5: BF16 compute, fp32 master weights",
    "tokens_processed": "PRD §4.3: 9.9e9 for arm A, and identical across both arms and all seeds",
    "checkpoint_every": "PRD §9 cost control: 'checkpoint every 500 steps with resume tested "
    "before any paid run (spot instances get preempted)'",
}


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """One config, both arms. §4.1 requires they share every field in this class."""

    # --- §4.3's budget ----------------------------------------------------
    tokens_processed: float = 9.9e9
    sequence_length: int = 512

    # Tokens per optimizer step, split between the microbatch and accumulation by the *host*
    # rather than by this config: a 4090 and a Kaggle T4 fit different microbatches, and §4.1
    # requires the optimizer see the same batch either way. `resolve_batching` does that split.
    tokens_per_step: int = 131_072  # 256 sequences x 512

    # --- optimizer, per preregistration §6 --------------------------------
    peak_lr: float = 6e-4
    min_lr_ratio: float = 0.1
    warmup_steps: int = 750
    betas: tuple[float, float] = (0.9, 0.95)
    weight_decay: float = 0.1
    eps: float = 1e-8
    grad_clip: float = 1.0

    # --- §5's precision ---------------------------------------------------
    precision: str = "bf16"

    # --- §9's cost controls -----------------------------------------------
    checkpoint_every: int = 500
    checkpoint_fractions: tuple[float, ...] = CHECKPOINT_FRACTIONS

    log_every: int = 10
    seed: int = 0

    # Recorded, never read by the loop: §4.2 freezes the corruption generator's version and seed
    # so a rerun reproduces the same tasks from the same clean text.
    task_generator_version: str = "1"

    metadata: dict = field(default_factory=dict)

    @property
    def total_steps(self) -> int:
        return int(self.tokens_processed // self.tokens_per_step)

    def lr_at(self, step: int) -> float:
        """Linear warmup then cosine decay to ``min_lr_ratio`` of peak. Both arms, every seed."""
        import math  # noqa: PLC0415

        if step < self.warmup_steps:
            return self.peak_lr * (step + 1) / self.warmup_steps
        span = max(self.total_steps - self.warmup_steps, 1)
        progress = min((step - self.warmup_steps) / span, 1.0)
        floor = self.peak_lr * self.min_lr_ratio
        return floor + (self.peak_lr - floor) * 0.5 * (1 + math.cos(math.pi * progress))

    def checkpoint_steps(self) -> dict[int, float]:
        """``{step: fraction}`` for §4.3's seven evaluation points."""
        return {max(1, int(self.total_steps * f)): f for f in self.checkpoint_fractions}

    def resolve_batching(self, microbatch: int) -> tuple[int, int]:
        """``(microbatch, accumulation)`` for a host that fits ``microbatch`` sequences.

        Refuses a microbatch that does not divide the step, rather than rounding. §4.1's "same
        number of tokens processed" is a *per-step* property too — a run that silently used 240
        sequences a step where another used 256 is not the same run, and the difference would be
        invisible in every artifact except the loss curve.
        """
        per_step = self.tokens_per_step // self.sequence_length
        if microbatch <= 0 or per_step % microbatch:
            raise ValueError(
                f"microbatch {microbatch} does not divide the {per_step} sequences in a step; "
                f"pick a divisor of {per_step} so both arms take the same optimizer step"
            )
        return microbatch, per_step // microbatch

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> TrainingConfig:
        data = dict(data)
        for key in ("betas", "checkpoint_fractions"):
            if key in data:
                data[key] = tuple(data[key])
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown training config fields: {sorted(unknown)}")
        return cls(**data)


__all__ = ["CHECKPOINT_FRACTIONS", "PROVENANCE", "TrainingConfig"]
