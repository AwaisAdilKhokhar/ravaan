"""§5's specification and §4.1's matched pair, asserted rather than described.

The tests that matter here are not "does the model run" — they are the two claims the experiment
rests on and that nothing else checks: that the arms have identical parameter counts, and that the
only structural difference between them is the attention mask.
"""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from ravaan.models.ar import IGNORE_INDEX, RavaanAR  # noqa: E402
from ravaan.models.backbone import RavaanTransformer  # noqa: E402
from ravaan.models.config import (  # noqa: E402
    LADDER,
    ModelConfig,
    assert_matched,
    parameter_count,
)
from ravaan.models.diffusion import RavaanDiffusion  # noqa: E402

TINY = ModelConfig(vocab_size=64, n_layers=2, d_model=32, n_heads=2, d_ffn=88, context_length=16)


# --- §5: the specification ------------------------------------------------


def test_default_config_is_the_prd_table():
    """§5's table, to the number. 70M total, ≈59.5M non-embedding."""
    counts = parameter_count(ModelConfig())
    assert counts["total"] == 69_975_680
    assert counts["non_embedding"] == 59_489_920
    assert 0.99 <= counts["non_embedding"] / 59.5e6 <= 1.01


@pytest.mark.parametrize("name", list(LADDER))
def test_counted_parameters_match_the_built_model(name):
    """The arithmetic in `config.py` and the tensors `backbone.py` allocates are the same number.

    Without this the cheap count is a second, quietly diverging opinion — and it is the one the
    gate reads before anything is rented.
    """
    config = LADDER[name]
    built = sum(p.numel() for p in RavaanTransformer(config).parameters())
    assert built == parameter_count(config)["total"]


@pytest.mark.parametrize("name", list(LADDER))
def test_arms_are_exactly_matched(name):
    """§4.1's central requirement, and §5's CI assertion. Exactly equal, not within 2%."""
    config = LADDER[name]
    assert_matched(config.as_ar(), config.as_diffusion())
    ar = sum(p.numel() for p in RavaanAR(config).parameters())
    diff = sum(p.numel() for p in RavaanDiffusion(4, config).parameters())
    assert ar == diff == parameter_count(config)["total"]


def test_assert_matched_refuses_a_near_miss():
    """Inside 2% but not equal is a bug report, not a pass — see the message it raises."""
    with pytest.raises(AssertionError, match="exactly equal"):
        assert_matched(ModelConfig(), ModelConfig(d_ffn=1_730))


def test_tied_embeddings_are_actually_tied():
    model = RavaanTransformer(TINY)
    assert model.head is None
    untied = RavaanTransformer(ModelConfig(**{**TINY.to_dict(), "tie_embeddings": False}))
    assert untied.head is not None
    assert (
        parameter_count(untied.config)["total"] - parameter_count(TINY)["total"]
        == TINY.vocab_size * TINY.d_model
    )


def test_head_dim_must_divide_and_be_even():
    with pytest.raises(ValueError, match="not divisible"):
        ModelConfig(d_model=640, n_heads=7)


# --- §4.1: the one difference ---------------------------------------------


def test_causality_is_the_only_difference():
    """A token's AR output must not move when a *later* token changes; the diffusion one must.

    This is the property §4.1 is actually claiming, tested on behaviour rather than on a flag.
    """
    torch.manual_seed(0)
    tokens = torch.randint(0, TINY.vocab_size, (1, TINY.context_length))
    changed = tokens.clone()
    changed[0, -1] = (changed[0, -1] + 1) % TINY.vocab_size

    causal = RavaanTransformer(TINY.as_ar()).eval()
    with torch.no_grad():
        assert torch.allclose(causal(tokens)[0, 0], causal(changed)[0, 0], atol=1e-6)

    bidirectional = RavaanTransformer(TINY.as_diffusion()).eval()
    with torch.no_grad():
        assert not torch.allclose(
            bidirectional(tokens)[0, 0], bidirectional(changed)[0, 0], atol=1e-5
        )


def test_the_two_arms_initialize_identically_from_a_seed():
    """§4.1 shares the seeds. Same seed, same tensors — the mask is not a parameter."""
    torch.manual_seed(7)
    ar = RavaanAR(TINY)
    torch.manual_seed(7)
    diff = RavaanDiffusion(4, TINY)
    for (name_a, a), (name_b, b) in zip(
        ar.backbone.named_parameters(), diff.backbone.named_parameters(), strict=True
    ):
        assert name_a == name_b
        assert torch.equal(a, b), name_a


def test_diffusion_refuses_a_mask_outside_the_vocabulary():
    with pytest.raises(ValueError, match="absorbing state"):
        RavaanDiffusion(TINY.vocab_size, TINY)


def test_sequence_longer_than_context_is_refused():
    model = RavaanTransformer(TINY)
    with pytest.raises(ValueError, match="context length"):
        model(torch.zeros(1, TINY.context_length + 1, dtype=torch.long))


# --- the objectives --------------------------------------------------------


def test_untrained_loss_is_uniform_entropy():
    """Both arms start at ln(V) — anything else means the head or the init is wrong."""
    torch.manual_seed(0)
    tokens = torch.randint(0, TINY.vocab_size, (4, TINY.context_length))
    uniform = torch.log(torch.tensor(float(TINY.vocab_size)))
    assert RavaanAR(TINY).loss(tokens).loss.item() == pytest.approx(uniform, rel=0.1)
    # The ELBO's 1/t weighting makes it a looser bound, so it sits at or above ln(V) — never far
    # below, which would mean the weight was dropped.
    diff = RavaanDiffusion(4, TINY).loss(tokens).loss.item()
    assert uniform * 0.9 <= diff <= uniform * 1.6


def test_ar_ignores_masked_labels():
    """§4.1's 'loss on target': a conditioned prefix contributes no gradient and no count."""
    torch.manual_seed(0)
    tokens = torch.randint(0, TINY.vocab_size, (2, TINY.context_length))
    labels = tokens.clone()
    labels[:, : TINY.context_length // 2] = IGNORE_INDEX
    out = RavaanAR(TINY).loss(tokens, labels)
    assert int(out.tokens) == labels[:, 1:].ne(IGNORE_INDEX).sum()


def test_diffusion_keeps_conditioned_positions_unmasked():
    """§4.1's 'condition on unmasked source, diffuse the target'."""
    torch.manual_seed(0)
    model = RavaanDiffusion(4, TINY)
    tokens = torch.randint(5, TINY.vocab_size, (3, TINY.context_length))
    keep = torch.zeros_like(tokens, dtype=torch.bool)
    keep[:, : TINY.context_length // 2] = True
    corrupted, masked = model.corrupt(tokens, torch.ones(3), keep=keep)
    assert not masked[keep].any()
    assert torch.equal(corrupted[keep], tokens[keep])
    # t = 1 absorbs everything it is allowed to
    assert masked[~keep].all()


def test_diffusion_loss_scores_only_masked_positions():
    """The ELBO does not score a token the model was handed. Scoring it would silently turn this
    into a BERT objective that bounds nothing."""
    torch.manual_seed(0)
    model = RavaanDiffusion(4, TINY)
    tokens = torch.randint(5, TINY.vocab_size, (2, TINY.context_length))
    keep = torch.ones_like(tokens, dtype=torch.bool)
    out = model.loss(tokens, keep=keep)
    assert int(out.tokens) == 0
    assert out.loss.item() == pytest.approx(0.0)


def test_both_arms_produce_gradients_for_every_parameter():
    torch.manual_seed(0)
    tokens = torch.randint(5, TINY.vocab_size, (2, TINY.context_length))
    for model in (RavaanAR(TINY), RavaanDiffusion(4, TINY)):
        model.loss(tokens).loss.backward()
        missing = [n for n, p in model.named_parameters() if p.grad is None]
        assert not missing, f"{type(model).__name__} left {missing} without gradient"
