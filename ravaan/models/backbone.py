"""The shared transformer — PRD §5, and the half of §4.1 that both arms hold in common.

One module, one class, one flag. `RavaanTransformer(config)` is the AR model when
``config.causal`` and the diffusion model when it is not, and there is no second implementation to
drift from the first. That is not tidiness: §4.1's claim is that the two models "differ in exactly
one thing: the factorization", and the cheapest way to make a claim like that true is to leave
only one place where it could be false.

What the arms share, structurally rather than by convention:

* the same ``forward``, returning logits over §5's 16,384 vocabulary;
* the same RoPE tables, RMSNorm, SwiGLU FFN and tied embeddings;
* the same parameter tensors, in the same order, so a seed produces the same initialization.

What differs, in one line of one method: whether `scaled_dot_product_attention` is called with
``is_causal=True``. Everything else about the objectives lives in the two loss modules, where it
belongs — the backbone does not know which experiment it is in.

**Why RoPE for a bidirectional model.** MDLM's attention is bidirectional, but the positions are
still ordered and the model still needs to know that token 5 precedes token 6. RoPE is applied to
queries and keys identically in both arms, so the positional information is the same information;
only the mask changes.

Precision is §5's BF16, and it is applied by the training loop through autocast rather than by
casting parameters here — the master weights stay fp32, which is what makes the optimizer's
updates meaningful at this scale.
"""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F  # noqa: N812
from torch import Tensor, nn

from ravaan.models.config import ModelConfig


class RMSNorm(nn.Module):
    """§5's normalization. Scale only, no bias — the usual formulation.

    Computed in fp32 regardless of the autocast dtype. The reduction is a mean of squares over
    640 values, and in bf16 that loses enough mantissa to matter for a norm every layer applies
    twice; casting back at the end costs nothing the profiler can find.
    """

    def __init__(self, dim: int, eps: float = 1e-5) -> None:
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: Tensor) -> Tensor:
        dtype = x.dtype
        x = x.float()
        x = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return (x * self.weight.float()).to(dtype)


class RotaryEmbedding(nn.Module):
    """RoPE tables, built once and cached as buffers.

    Not persistent: they are a deterministic function of ``head_dim``, ``theta`` and the context
    length, so writing them into every checkpoint would put 512 x 64 floats in each of the seven
    checkpoints §4.3 takes per run, six runs over, to save recomputing a sine.
    """

    def __init__(self, head_dim: int, max_positions: int, theta: float) -> None:
        super().__init__()
        inverse = 1.0 / (theta ** (torch.arange(0, head_dim, 2, dtype=torch.float32) / head_dim))
        positions = torch.arange(max_positions, dtype=torch.float32)
        angles = torch.outer(positions, inverse)
        self.register_buffer("cos", angles.cos(), persistent=False)
        self.register_buffer("sin", angles.sin(), persistent=False)

    def forward(self, x: Tensor, offset: int = 0) -> Tensor:
        """``x`` is ``(batch, heads, positions, head_dim)``."""
        length = x.shape[-2]
        cos = self.cos[offset : offset + length].to(x.dtype)
        sin = self.sin[offset : offset + length].to(x.dtype)
        first, second = x.float().chunk(2, dim=-1)
        cos, sin = cos.float(), sin.float()
        rotated = torch.cat(
            (first * cos - second * sin, second * cos + first * sin), dim=-1
        )
        return rotated.to(x.dtype)


class Attention(nn.Module):
    """Multi-head attention over §5's 10 heads of dim 64, through PyTorch SDPA.

    **This is where the two arms differ and nowhere else.** `is_causal` comes from the config, so
    the diffusion arm sees the whole sequence and the AR arm sees a prefix, with the same weights,
    the same RoPE and the same kernel.
    """

    def __init__(self, config: ModelConfig, rotary: RotaryEmbedding) -> None:
        super().__init__()
        self.n_heads = config.n_heads
        self.head_dim = config.head_dim
        self.causal = config.causal
        self.dropout = config.dropout
        self.rotary = rotary
        self.qkv = nn.Linear(config.d_model, 3 * config.d_model, bias=False)
        self.out = nn.Linear(config.d_model, config.d_model, bias=False)

    def forward(self, x: Tensor, padding_mask: Tensor | None = None) -> Tensor:
        batch, length, _ = x.shape
        qkv = self.qkv(x).view(batch, length, 3, self.n_heads, self.head_dim)
        query, key, value = qkv.permute(2, 0, 3, 1, 4)
        query = self.rotary(query)
        key = self.rotary(key)

        attn_mask = None
        if padding_mask is not None:
            # `(batch, 1, 1, length)` — broadcast over heads and query positions. Combined with
            # `is_causal` by SDPA's own rules would be wrong (it ignores the mask when
            # `is_causal` is set), so a causal run with padding builds the mask explicitly.
            attn_mask = padding_mask[:, None, None, :].to(torch.bool)
            if self.causal:
                causal = torch.ones(length, length, dtype=torch.bool, device=x.device).tril()
                attn_mask = attn_mask & causal

        out = F.scaled_dot_product_attention(
            query,
            key,
            value,
            attn_mask=attn_mask,
            dropout_p=self.dropout if self.training else 0.0,
            is_causal=self.causal and attn_mask is None,
        )
        out = out.transpose(1, 2).reshape(batch, length, -1)
        return self.out(out)


class SwiGLU(nn.Module):
    """§5's FFN at d_ffn = 1,728. Gate and up projections fused into one matmul."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.up = nn.Linear(config.d_model, 2 * config.d_ffn, bias=False)
        self.down = nn.Linear(config.d_ffn, config.d_model, bias=False)

    def forward(self, x: Tensor) -> Tensor:
        gate, value = self.up(x).chunk(2, dim=-1)
        return self.down(F.silu(gate) * value)


class Block(nn.Module):
    """Pre-norm transformer block. Residual stream in, residual stream out."""

    def __init__(self, config: ModelConfig, rotary: RotaryEmbedding) -> None:
        super().__init__()
        self.norm_attention = RMSNorm(config.d_model, config.rms_norm_eps)
        self.attention = Attention(config, rotary)
        self.norm_ffn = RMSNorm(config.d_model, config.rms_norm_eps)
        self.ffn = SwiGLU(config)

    def forward(self, x: Tensor, padding_mask: Tensor | None = None) -> Tensor:
        x = x + self.attention(self.norm_attention(x), padding_mask)
        return x + self.ffn(self.norm_ffn(x))


class RavaanTransformer(nn.Module):
    """§5's model. AR or diffusion depending on one boolean in the config.

    The initialization is the reference paper's, taken untuned — preregistration §6 commits to
    that and to *saying* it likely favours AR. Normal(0, 0.02) on every weight, with the residual
    output projections scaled by 1/sqrt(2 * n_layers) so the residual stream's variance does not
    grow with depth.
    """

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.config = config
        self.embedding = nn.Embedding(config.vocab_size, config.d_model)
        self.rotary = RotaryEmbedding(config.head_dim, config.context_length, config.rope_theta)
        self.blocks = nn.ModuleList(Block(config, self.rotary) for _ in range(config.n_layers))
        self.norm = RMSNorm(config.d_model, config.rms_norm_eps)
        if config.tie_embeddings:
            self.head = None  # §5: tied. The embedding matrix *is* the output projection.
        else:
            self.head = nn.Linear(config.d_model, config.vocab_size, bias=False)

        self.apply(self._init)
        # Depth-scaled residual projections, applied after the uniform init so it is visibly a
        # correction to it rather than a second initialization scheme.
        scale = 1.0 / math.sqrt(2 * config.n_layers)
        for block in self.blocks:
            torch.nn.init.normal_(block.attention.out.weight, mean=0.0, std=0.02 * scale)
            torch.nn.init.normal_(block.ffn.down.weight, mean=0.0, std=0.02 * scale)

    @staticmethod
    def _init(module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, tokens: Tensor, padding_mask: Tensor | None = None) -> Tensor:
        """``(batch, length)`` of ids in, ``(batch, length, vocab)`` of logits out.

        ``padding_mask`` is True at positions to attend to. Stage 10 packs without padding
        (§6.3.10 drops the tail rather than padding it), so the training path passes ``None`` and
        this exists for evaluation, where a batch of held-out sequences legitimately ragged.
        """
        length = tokens.shape[-1]
        if length > self.config.context_length:
            raise ValueError(
                f"sequence of {length} exceeds §5's context length of "
                f"{self.config.context_length}; RoPE tables are built to that length"
            )
        x = self.embedding(tokens)
        for block in self.blocks:
            x = block(x, padding_mask)
        x = self.norm(x)
        if self.head is not None:
            return self.head(x)
        return F.linear(x, self.embedding.weight)

    def parameter_groups(self) -> tuple[list[nn.Parameter], list[nn.Parameter]]:
        """``(decay, no_decay)``. Norms and embeddings are not weight-decayed.

        Split here rather than in the training loop because it is a property of the architecture:
        which tensors are matmul weights is something this module knows and an optimizer factory
        would have to rediscover by name matching.
        """
        decay, no_decay = [], []
        for name, param in self.named_parameters():
            if not param.requires_grad:
                continue
            (no_decay if param.ndim < 2 or "embedding" in name else decay).append(param)
        return decay, no_decay
