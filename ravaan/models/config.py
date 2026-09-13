"""The model specification, and the arithmetic that checks it — PRD §5.

§5 gives a table of numbers and one instruction about them: *"Exact parameter counts must be
computed programmatically and asserted equal within 2% across configs in CI."* This module is the
first half of that. :func:`parameter_count` computes the count from a config without building the
model, so the assertion is cheap enough to run in a test rather than in a training job.

**Both arms use one config, and that is the whole point of §4.1.** The AR and diffusion models
differ in `causal` and in nothing else — same depth, same width, same vocabulary, same tied
embeddings. Time-agnostic MDLM (§4.1) is what makes that possible: a DiT-style timestep embedding
would add parameters to one arm only, and "within 2%" would become a thing to argue about rather
than a thing that is trivially true. Here the counts are *identical*, and
:func:`assert_matched` says so rather than allowing the 2%.

The fallback ladder in §5 — 70M → 40M → 25M — is here as data rather than as a comment, because
G2 ("shrink the model, never the epoch count") is a decision someone makes under time pressure
and it should be one function call.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

# §5's vocabulary, and stage 10's dtype ceiling. `ravaan.data.packing.PackingConfig` carries the
# same number for the corpus side; `tests/` asserts they agree.
VOCAB_SIZE = 16_384


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """PRD §5, as a value. Defaults are the 70M row of the table."""

    vocab_size: int = VOCAB_SIZE
    n_layers: int = 12
    d_model: int = 640
    n_heads: int = 10
    d_ffn: int = 1_728
    context_length: int = 512

    # §5: RoPE, RMSNorm, tied embeddings. Present as fields because a config that could not
    # express "untied" could not be used to measure what tying is worth.
    rope_theta: float = 10_000.0
    rms_norm_eps: float = 1e-5
    tie_embeddings: bool = True

    # §4.1's single difference. Everything above this line is shared by construction.
    causal: bool = True

    dropout: float = 0.0

    def __post_init__(self) -> None:
        if self.d_model % self.n_heads:
            raise ValueError(
                f"d_model {self.d_model} is not divisible by n_heads {self.n_heads} — §5 fixes "
                "head dim at 64 and a config that cannot reach it is not §5's model"
            )
        if self.head_dim % 2:
            raise ValueError(f"RoPE needs an even head dim, got {self.head_dim}")

    @property
    def head_dim(self) -> int:
        return self.d_model // self.n_heads

    def as_ar(self) -> ModelConfig:
        return replace(self, causal=True)

    def as_diffusion(self) -> ModelConfig:
        """Bidirectional attention. The *only* field §4.1 lets the two arms disagree on."""
        return replace(self, causal=False)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ModelConfig:
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown model config fields: {sorted(unknown)}")
        return cls(**data)


# §5's fallback ladder. G2's lever, and the one it is allowed to pull: "shrink the model, never
# the epoch count — the epoch count is the experiment."
LADDER: dict[str, ModelConfig] = {
    "70M": ModelConfig(),
    "40M": ModelConfig(n_layers=10, d_model=512, n_heads=8, d_ffn=1_376),
    "25M": ModelConfig(n_layers=8, d_model=384, n_heads=6, d_ffn=1_024),
}


def parameter_count(config: ModelConfig) -> dict[str, int]:
    """Every parameter the model will allocate, by group, without allocating any.

    Kept separate from the module that builds the model on purpose. A count taken by summing
    ``p.numel()`` over a built model answers "what did I build"; §5 asks "does what I am about to
    build match the specification", which is a question you want answered before a paid instance
    is running. `tests/` checks the two agree, which is what makes this one trustworthy.
    """
    d = config.d_model
    per_layer_attention = 4 * d * d  # q, k, v, out — no biases (§5's RMSNorm/SwiGLU stack)
    per_layer_ffn = 3 * d * config.d_ffn  # SwiGLU: gate and up in, one down out
    per_layer_norms = 2 * d  # pre-attention and pre-FFN RMSNorm, scale only
    per_layer = per_layer_attention + per_layer_ffn + per_layer_norms

    embedding = config.vocab_size * d
    output = 0 if config.tie_embeddings else config.vocab_size * d

    groups = {
        "embedding": embedding,
        "blocks": per_layer * config.n_layers,
        "final_norm": d,
        "output": output,
    }
    groups["non_embedding"] = groups["blocks"] + groups["final_norm"]
    groups["total"] = embedding + groups["blocks"] + groups["final_norm"] + output
    return groups


def assert_matched(*configs: ModelConfig, tolerance: float = 0.02) -> int:
    """§5's CI assertion. Returns the shared total so a caller can log it.

    ``tolerance`` is §5's 2%, but the configs this project actually compares should come out
    *exactly* equal — time-agnostic MDLM adds nothing to either side. A pair that merely lands
    inside 2% means something was added to one arm, and the message says to go look.
    """
    if len(configs) < 2:
        raise ValueError("assert_matched compares two or more configs")
    counts = [parameter_count(c)["total"] for c in configs]
    low, high = min(counts), max(counts)
    if high - low > tolerance * high:
        raise AssertionError(
            f"§5 requires parameter counts within {tolerance:.0%} across configs; got "
            f"{low:,} … {high:,} ({(high - low) / high:.2%})"
        )
    if low != high:
        raise AssertionError(
            f"configs differ by {high - low:,} parameters ({(high - low) / high:.3%}). Inside "
            "§5's 2%, but §4.1's arms should be exactly equal — time-agnostic MDLM adds no "
            "parameters, so something was added to one arm. Find it rather than widening this"
        )
    return low
