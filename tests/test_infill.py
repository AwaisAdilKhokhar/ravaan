"""§8.3's infill metrics, and the preregistered rule they are scored under.

Preregistration §8 fixes the AR arm's truncation rule *before any result exists*, which is only
worth something if the implementation is the rule. So the tests here are mostly about the rule:
that it cuts the arm it names, that it refuses the arm it does not, and that the diagnostic which
reports the metric without it is genuinely without it.

`ravaan.training.tasks.rebalance_shares` is tested alongside because it exists for the same
experiment — open question 5 — and it has the same property worth pinning: it changes exactly one
thing, and it raises rather than quietly renormalizing when asked for a mixture §4.2 cannot hold.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from ravaan.evaluation.infill import (  # noqa: E402
    TRUNCATION_RULE,
    InfillItem,
    InfillScore,
    token_f1,
    truncate_to_gold,
)
from ravaan.training.tasks import TASK_SHARES, rebalance_shares  # noqa: E402

# --- the preregistered rule -------------------------------------------------


def test_ar_generation_is_cut_to_the_gold_length():
    assert truncate_to_gold([1, 2, 3, 4, 5, 6], [1, 2, 3], arm="ar") == [1, 2, 3]


def test_a_short_ar_generation_is_left_alone():
    """The rule is a cut, not a pad. A model that stopped early is scored on what it wrote."""
    assert truncate_to_gold([1, 2], [1, 2, 3], arm="ar") == [1, 2]


def test_the_diffusion_arm_is_not_truncated_because_it_is_already_the_right_width():
    assert truncate_to_gold([7, 8, 9], [1, 2, 3], arm="diff") == [7, 8, 9]


def test_a_mis_sized_diffusion_canvas_raises_instead_of_being_trimmed():
    """Trimming would hide a prompt built at the wrong width, which is a bug and not a length."""
    with pytest.raises(ValueError, match="fixed-width canvas"):
        truncate_to_gold([7, 8], [1, 2, 3], arm="diff")


def test_the_rule_is_named_in_the_score_so_a_table_can_say_what_it_scored_under():
    item = InfillItem.of(arm="ar", gold=[1, 2], generated=[1, 2])
    assert InfillScore.of([item]).truncation_rule == TRUNCATION_RULE


# --- what the rule does to the numbers --------------------------------------


def test_truncation_can_turn_a_miss_into_an_exact_match_and_both_are_reported():
    """§4.2's FIM framing has no terminator, so the AR arm overruns. That is Finding AQ, and the
    point of reporting both is that the report can say how much the rule is doing."""
    item = InfillItem.of(arm="ar", gold=[1, 2, 3], generated=[1, 2, 3, 4, 5, 6])
    assert item.exact is True
    assert item.exact_untruncated is False
    assert item.truncated is True


def test_an_exactly_sized_generation_is_not_counted_as_truncated():
    item = InfillItem.of(arm="ar", gold=[1, 2, 3], generated=[1, 2, 3])
    assert item.truncated is False
    assert item.exact is item.exact_untruncated is True


def test_token_f1_is_a_multiset_overlap_not_a_set_one():
    """A gold span that says a token twice is half-answered by a prediction that says it once."""
    assert token_f1([5], [5, 5]) == pytest.approx(2 / 3)
    assert token_f1([5, 5], [5, 5]) == 1.0


def test_token_f1_of_a_disjoint_prediction_is_zero():
    assert token_f1([1, 2], [3, 4]) == 0.0


def test_token_f1_rewards_the_right_tokens_in_the_wrong_order():
    """Exact-match is the order-sensitive endpoint; F1 is the partial-credit one, and a table
    carrying only one of them cannot tell 'wrong content' from 'right content, wrong order'."""
    item = InfillItem.of(arm="ar", gold=[1, 2, 3], generated=[3, 2, 1])
    assert item.exact is False
    assert item.f1 == 1.0


def test_empty_gold_and_empty_prediction_agree():
    assert token_f1([], []) == 1.0
    assert token_f1([1], []) == 0.0


# --- the aggregate ----------------------------------------------------------


def test_score_aggregates_rates_over_items():
    items = [
        InfillItem.of(arm="ar", gold=[1, 2], generated=[1, 2]),
        InfillItem.of(arm="ar", gold=[1, 2], generated=[9, 9, 9, 9]),
    ]
    score = InfillScore.of(items)
    assert score.items == 2
    assert score.exact_match == pytest.approx(0.5)
    assert score.truncated == pytest.approx(0.5)
    assert score.mean_gold_length == pytest.approx(2.0)
    assert score.mean_generated_length == pytest.approx(3.0)


def test_locked_preservation_is_reported_rather_than_assumed():
    """§8.1 asserts it inside the decoders; §8.3 asks for it as a number, and a caller that builds
    prompts by hand can still break it."""
    items = [
        InfillItem.of(arm="diff", gold=[1], generated=[1], locked_preserved=True),
        InfillItem.of(arm="diff", gold=[1], generated=[2], locked_preserved=False),
    ]
    assert InfillScore.of(items).locked_preserved == pytest.approx(0.5)


def test_scoring_nothing_raises_rather_than_returning_a_zero():
    with pytest.raises(ValueError, match="no items"):
        InfillScore.of([])


# --- open question 5's lever ------------------------------------------------


def test_rebalance_moves_one_share_and_takes_the_residual_from_lm_alone():
    shares = rebalance_shares({"infill": 0.50})
    assert shares["infill"] == pytest.approx(0.50)
    assert shares["lm"] == pytest.approx(0.25)
    for task in ("translit", "restore", "codeswitch"):
        assert shares[task] == pytest.approx(TASK_SHARES[task])
    assert sum(shares.values()) == pytest.approx(1.0)


def test_rebalance_preserves_the_task_order_apportionment_depends_on():
    assert tuple(rebalance_shares({"infill": 0.5})) == tuple(TASK_SHARES)


def test_rebalance_of_nothing_is_the_frozen_table():
    assert rebalance_shares({}) == TASK_SHARES


def test_a_mixture_that_does_not_fit_raises_rather_than_renormalizing():
    with pytest.raises(ValueError, match="leaves 'lm'"):
        rebalance_shares({"infill": 0.90, "translit": 0.30})


def test_pinning_lm_requires_the_shares_to_sum_to_one_on_their_own():
    with pytest.raises(ValueError, match="absorb the residual"):
        rebalance_shares({"lm": 0.20})
    assert rebalance_shares(
        {"lm": 0.25, "infill": 0.50, "translit": 0.10, "restore": 0.08, "codeswitch": 0.07}
    )["lm"] == pytest.approx(0.25)


def test_an_unknown_task_name_raises():
    with pytest.raises(ValueError, match="no task named"):
        rebalance_shares({"fim": 0.5})
