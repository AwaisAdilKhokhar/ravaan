"""Stage 9 — split creation.

The tests that matter here are the structural ones. Stage 9 has no thresholds validated against
read documents the way stages 5, 7 and 8 do; what it has instead are guarantees the PRD states in
prose — arm A is a subsample of arm B, the arms differ in size and nothing else, a document's
split does not depend on read order — and every one of those is either provable from the
construction or false. So they are asserted as properties over generated corpora, not as fixtures.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from ravaan.data.splits import (
    SPLITS_VERSION,
    SplitAssigner,
    SplitConfig,
    SplitPlan,
    assign_splits,
    bucket_of,
    pair_key,
)

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "data" / "splits.json"


# ---------------------------------------------------------------------------
# Corpora
# ---------------------------------------------------------------------------


def make_corpus(
    count: int = 4_000,
    *,
    population: str = "urdu",
    chars: int = 2_000,
    prefix: str = "doc",
    jitter: bool = False,
    seed: int = 0,
) -> list[tuple[str, str, str]]:
    """``(doc_id, text, population)`` triples with predictable sizes."""
    rng = random.Random(seed)
    corpus = []
    for index in range(count):
        size = rng.randint(chars // 2, chars * 2) if jitter else chars
        corpus.append((f"{prefix}:{index}", "ا" * size, population))
    return corpus


def small_config(**overrides) -> SplitConfig:
    """A config whose budgets a few thousand synthetic documents can actually fill."""
    base = {
        "arm_tokens": {"A": 25_000, "B": 100_000},
        "population_targets": {"urdu": 120_000, "roman_urdu": 40_000, "code_switched": 10_000},
        "chars_per_token": {"urdu": 3.5, "roman_urdu": 4.2, "code_switched": 3.8},
        "heldout_sequences": 10,
        "sequence_length": 512,
        "buckets": 10_000,
    }
    base.update(overrides)
    return SplitConfig(**base)


# ---------------------------------------------------------------------------
# The hash
# ---------------------------------------------------------------------------


def test_bucket_is_in_range():
    for index in range(2_000):
        bucket = bucket_of(f"doc:{index}", salt="s", buckets=1_000)
        assert 0 <= bucket < 1_000


def test_bucket_is_deterministic_across_calls():
    first = [bucket_of(f"doc:{i}", salt="s", buckets=997) for i in range(500)]
    second = [bucket_of(f"doc:{i}", salt="s", buckets=997) for i in range(500)]
    assert first == second


def test_bucket_is_uniform_enough_to_budget_with():
    """A skewed hash would make every band boundary wrong in a way nothing downstream detects."""
    buckets = 10
    counts = [0] * buckets
    for index in range(100_000):
        counts[bucket_of(f"doc:{index}", salt="ravaan/split/v1", buckets=buckets)] += 1
    expected = 100_000 / buckets
    assert max(abs(c - expected) for c in counts) < expected * 0.05


def test_salt_changes_the_partition():
    a = [bucket_of(f"doc:{i}", salt="v1", buckets=1_000) for i in range(200)]
    b = [bucket_of(f"doc:{i}", salt="v2", buckets=1_000) for i in range(200)]
    assert a != b


def test_bucket_does_not_track_stage_six_hashes():
    """Split membership must not correlate with a dedup hash, or one stage biases the other."""
    from ravaan.data.dedup import document_key

    pairs = [
        (
            bucket_of(f"doc:{i}", salt="ravaan/split/v1", buckets=2),
            document_key(f"doc:{i}") % 2,
        )
        for i in range(20_000)
    ]
    agreement = sum(1 for split, dedup in pairs if split == dedup) / len(pairs)
    assert 0.45 < agreement < 0.55


# ---------------------------------------------------------------------------
# Pair keying — the splitter must not manufacture contamination
# ---------------------------------------------------------------------------


def test_pair_key_strips_a_column_suffix():
    assert pair_key("roman-urdu-parl:train.csv:0:41#roman") == "roman-urdu-parl:train.csv:0:41"
    assert pair_key("roman-urdu-parl:train.csv:0:41#urdu") == "roman-urdu-parl:train.csv:0:41"


def test_pair_key_leaves_a_plain_id_alone():
    assert pair_key("fineweb2-urd_Arab:abc123") == "fineweb2-urd_Arab:abc123"


def test_pair_key_is_disableable():
    assert pair_key("a#b", "") == "a#b"


def test_both_columns_of_a_row_land_in_the_same_split():
    """The failure this prevents is a Roman side in train and its Urdu side in test."""
    for index in range(1_000):
        row = f"roman-urdu-parl:train.csv:0:{index}"
        roman = bucket_of(f"{row}#roman", salt="ravaan/split/v1", buckets=1_000)
        urdu = bucket_of(f"{row}#urdu", salt="ravaan/split/v1", buckets=1_000)
        assert roman == urdu == bucket_of(row, salt="ravaan/split/v1", buckets=1_000)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_shipped_config_matches_code_defaults():
    """The file the manifest fingerprints and the defaults the code applies must not drift."""
    from_file = SplitConfig.from_json_file(CONFIG_PATH)
    assert from_file == SplitConfig()


def test_shipped_config_declares_its_version():
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assert payload["splits_version"] == SPLITS_VERSION


def test_config_round_trips_through_json(tmp_path):
    config = small_config()
    path = tmp_path / "splits.json"
    config.to_json_file(path)
    assert SplitConfig.from_json_file(path) == config


def test_config_rejects_unknown_keys():
    with pytest.raises(ValueError, match="unknown splits config keys"):
        SplitConfig.from_dict({**SplitConfig().to_dict(), "held_out_share": 0.02})


def test_config_rejects_a_population_without_a_fertility():
    with pytest.raises(ValueError, match="chars_per_token"):
        SplitConfig(
            population_targets={"urdu": 1_000, "klingon": 10},
            chars_per_token={"urdu": 3.5},
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"arm_tokens": {}},
        {"arm_tokens": {"A": 0}},
        {"population_targets": {"urdu": -1}, "chars_per_token": {"urdu": 3.5}},
        {"chars_per_token": {"urdu": 0.0, "roman_urdu": 4.2, "code_switched": 3.8}},
        {"heldout_sequences": -1},
        {"sequence_length": 0},
        {"buckets": 100},
        {"salt": ""},
    ],
)
def test_config_rejects_incoherent_settings(overrides):
    with pytest.raises(ValueError):
        SplitConfig(**overrides)


def test_mixture_is_the_prd_targets_in_proportion():
    mixture = SplitConfig().mixture
    assert mixture["urdu"] == pytest.approx(120 / 170)
    assert mixture["roman_urdu"] == pytest.approx(40 / 170)
    assert mixture["code_switched"] == pytest.approx(10 / 170)
    assert sum(mixture.values()) == pytest.approx(1.0)


def test_arm_names_are_ordered_by_budget():
    assert SplitConfig().arm_names == ("A", "B")


def test_heldout_tokens_follow_the_prd_sequence_count():
    # §6.1's ~5K sequences at §5's context length of 512.
    assert SplitConfig().heldout_tokens == 5_000 * 512


def test_fingerprint_moves_with_a_budget():
    a = SplitConfig()
    b = SplitConfig(arm_tokens={"A": 25_000_000, "B": 120_000_000})
    assert a.fingerprint() != b.fingerprint()


# ---------------------------------------------------------------------------
# Nesting — PRD §6.1's central guarantee
# ---------------------------------------------------------------------------


def test_arm_a_is_a_subset_of_arm_b():
    corpus = make_corpus(6_000, jitter=True)
    assignments, _ = assign_splits(corpus, small_config())
    arm_a = {a.doc_id for a in assignments if "A" in a.arms}
    arm_b = {a.doc_id for a in assignments if "B" in a.arms}
    assert arm_a
    assert arm_a < arm_b


def test_arm_membership_is_monotone_in_the_bucket():
    corpus = make_corpus(6_000, jitter=True)
    assignments, assigner = assign_splits(corpus, small_config())
    cuts = assigner.plan.bands["urdu"].arm_cuts
    assert cuts["A"] < cuts["B"]
    for assignment in assignments:
        if assignment.split != "train":
            continue
        assert ("A" in assignment.arms) == (assignment.bucket < cuts["A"])
        assert ("B" in assignment.arms) == (assignment.bucket < cuts["B"])


def test_arms_carry_the_same_population_mixture():
    """'Differ in size and nothing else' — the shares must match, not just the totals."""
    corpus = (
        make_corpus(4_000, population="urdu", prefix="u", jitter=True, seed=1)
        + make_corpus(4_000, population="roman_urdu", prefix="r", jitter=True, seed=2)
        + make_corpus(4_000, population="code_switched", prefix="c", jitter=True, seed=3)
    )
    _, assigner = assign_splits(corpus, small_config())
    log = assigner.log
    for population in ("urdu", "roman_urdu", "code_switched"):
        share_a = log.tokens(population, log.arm_chars[f"{population}/A"]) / log.arm_tokens("A")
        share_b = log.tokens(population, log.arm_chars[f"{population}/B"]) / log.arm_tokens("B")
        assert share_a == pytest.approx(share_b, abs=0.02)


def test_arm_totals_land_near_their_budgets():
    corpus = make_corpus(40_000, chars=200, jitter=True)
    config = small_config(population_targets={"urdu": 120_000}, chars_per_token={"urdu": 3.5})
    _, assigner = assign_splits(corpus, config)
    for arm, budget in config.arm_tokens.items():
        realized = assigner.log.arm_tokens(arm)
        assert budget * 0.97 <= realized <= budget


def test_an_arm_budget_is_never_overshot():
    """U is what the epoch count divides 9.9B by; overshooting quietly buys fewer epochs."""
    corpus = make_corpus(20_000, chars=500, jitter=True)
    config = small_config(population_targets={"urdu": 120_000}, chars_per_token={"urdu": 3.5})
    _, assigner = assign_splits(corpus, config)
    for arm in config.arm_names:
        assert assigner.log.arm_tokens(arm) <= config.arm_tokens[arm]


# ---------------------------------------------------------------------------
# Order independence
# ---------------------------------------------------------------------------


def test_assignment_does_not_depend_on_read_order():
    corpus = make_corpus(3_000, jitter=True)
    shuffled = list(corpus)
    random.Random(7).shuffle(shuffled)

    first, _ = assign_splits(corpus, small_config())
    second, _ = assign_splits(shuffled, small_config())

    assert {a.doc_id: (a.split, a.arms) for a in first} == {
        a.doc_id: (a.split, a.arms) for a in second
    }


def test_assignment_does_not_depend_on_which_other_documents_were_seen():
    """A per-document verdict, given the bands — so a resumed or partial pass agrees."""
    corpus = make_corpus(3_000, jitter=True)
    _, assigner = assign_splits(corpus, small_config())
    plan = assigner.plan

    lonely = SplitAssigner(small_config()).load_plan(plan)
    for doc_id, text, population in corpus[:200]:
        expected = next(a for a in assign_splits(corpus, small_config())[0] if a.doc_id == doc_id)
        actual = lonely.assign(doc_id, text, population)
        assert (actual.split, actual.arms) == (expected.split, expected.arms)


def test_a_partial_second_phase_agrees_with_a_complete_one():
    corpus = make_corpus(2_000, jitter=True)
    config = small_config()
    full = SplitAssigner(config)
    for doc_id, text, population in corpus:
        full.measure(doc_id, text, population)
    plan = full.seal()

    partial = SplitAssigner(config).load_plan(plan)
    subset = corpus[500:700]
    for doc_id, text, population in subset:
        one = partial.assign(doc_id, text, population)
        other = full.assign(doc_id, text, population)
        assert (one.split, one.arms) == (other.split, other.arms)


# ---------------------------------------------------------------------------
# Bands
# ---------------------------------------------------------------------------


def test_the_three_splits_partition_the_corpus():
    corpus = make_corpus(5_000, jitter=True)
    assignments, _ = assign_splits(corpus, small_config())
    by_split = {"train": set(), "validation": set(), "test": set()}
    for assignment in assignments:
        by_split[assignment.split].add(assignment.doc_id)
    assert set().union(*by_split.values()) == {doc_id for doc_id, _, _ in corpus}
    assert not by_split["train"] & by_split["validation"]
    assert not by_split["train"] & by_split["test"]
    assert not by_split["validation"] & by_split["test"]


def test_held_out_sets_are_disjoint_from_every_arm():
    corpus = make_corpus(5_000, jitter=True)
    assignments, _ = assign_splits(corpus, small_config())
    for assignment in assignments:
        if assignment.split in ("validation", "test"):
            assert assignment.arms == ()


def test_both_held_out_sets_are_non_empty_and_similar_in_size():
    corpus = make_corpus(8_000, chars=400, jitter=True)
    _, assigner = assign_splits(corpus, small_config())
    band = assigner.plan.bands["urdu"]
    assert band.chars_validation > 0
    assert band.chars_test > 0
    assert band.chars_validation == pytest.approx(band.chars_test, rel=0.15)


def test_held_out_sets_are_shared_by_both_arms():
    """One validation set for every arm, model and seed — §4.3's curves must share an x and a y."""
    corpus = make_corpus(5_000, jitter=True)
    _, assigner = assign_splits(corpus, small_config())
    band = assigner.plan.bands["urdu"]
    # The bands are solved once per population, not per arm; there is structurally only one.
    assert band.validation_from < band.test_from <= band.buckets
    assert max(band.arm_cuts.values()) <= band.train_to


def test_resizing_the_held_out_budget_leaves_the_arms_untouched():
    """Bands grow down from the top, arms grow up from zero — the two cannot interfere."""
    corpus = make_corpus(6_000, jitter=True)
    small, _ = assign_splits(corpus, small_config(heldout_sequences=10))
    large, _ = assign_splits(corpus, small_config(heldout_sequences=25))

    arms_small = {a.doc_id: a.arms for a in small}
    arms_large = {a.doc_id: a.arms for a in large}
    assert arms_small == arms_large
    # ...and the held-out sets really did change, or the test proves nothing.
    assert {a.doc_id for a in small if a.split == "test"} < {
        a.doc_id for a in large if a.split == "test"
    }


def test_bands_are_integers():
    """No float boundary, so no repeat of stage 8's array('f') rounding a threshold up."""
    _, assigner = assign_splits(make_corpus(2_000), small_config())
    band = assigner.plan.bands["urdu"]
    assert isinstance(band.test_from, int)
    assert isinstance(band.validation_from, int)
    assert all(isinstance(cut, int) for cut in band.arm_cuts.values())


# ---------------------------------------------------------------------------
# Unmet budgets — Gate G1's fallback ladder
# ---------------------------------------------------------------------------


def test_a_pool_too_small_for_an_arm_reports_it_rather_than_silently_truncating():
    corpus = make_corpus(50, chars=100)  # 5,000 characters against a 120,000-token target
    _, assigner = assign_splits(corpus, small_config())
    assert "B" in assigner.plan.bands["urdu"].unmet_arms


def test_a_sufficient_pool_reports_no_unmet_arm():
    corpus = make_corpus(40_000, chars=200, jitter=True)
    config = small_config(population_targets={"urdu": 120_000}, chars_per_token={"urdu": 3.5})
    _, assigner = assign_splits(corpus, config)
    assert assigner.plan.bands["urdu"].unmet_arms == ()


def test_a_pool_below_the_heldout_budget_says_so_rather_than_eating_the_corpus():
    """Found on a 2,482-document probe: every document landed in test and only the arms complained.

    The bands are solved from the top, so a starved held-out budget consumes the train pool and
    every arm reports unmet for a reason that is not its own. The upstream cause has to be named
    or the diagnosis reads as "the corpus is too small for the arms" when it is not.
    """
    corpus = make_corpus(100, chars=200)
    _, assigner = assign_splits(corpus, small_config(heldout_sequences=1_000))
    band = assigner.plan.bands["urdu"]
    assert band.unmet_heldout == ("validation", "test")
    assert assigner.to_dict()["unmet_heldout"]["urdu"] == ["validation", "test"]


def test_a_sufficient_pool_reports_no_unmet_heldout():
    corpus = make_corpus(40_000, chars=200, jitter=True)
    config = small_config(population_targets={"urdu": 120_000}, chars_per_token={"urdu": 3.5})
    _, assigner = assign_splits(corpus, config)
    assert assigner.plan.bands["urdu"].unmet_heldout == ()


def test_gate_g1_reports_the_prd_fallback_ladder():
    log = SplitAssigner(SplitConfig()).log
    log.chars["urdu/train"] = int(120e6 * 3.5)
    assert log.gate_g1()["verdict"] == "pass"
    log.chars["urdu/train"] = int(50e6 * 3.5)
    assert log.gate_g1()["verdict"] == "arm_a_only"
    log.chars["urdu/train"] = int(5e6 * 3.5)
    assert log.gate_g1()["verdict"] == "stop"


# ---------------------------------------------------------------------------
# Populations
# ---------------------------------------------------------------------------


def test_an_unbudgeted_label_is_counted_not_assigned():
    corpus = make_corpus(500, population="english", prefix="e")
    assignments, assigner = assign_splits(corpus, small_config())
    assert all(a.split == "unassigned" for a in assignments)
    assert all(a.arms == () for a in assignments)
    assert assigner.log.unassigned == 500
    assert assigner.log.unassigned_labels["english"] == 500


def test_populations_are_budgeted_independently():
    """A large native pool must not fill a small code-switched budget."""
    corpus = make_corpus(8_000, population="urdu", prefix="u", jitter=True) + make_corpus(
        40, population="code_switched", prefix="c", chars=100
    )
    _, assigner = assign_splits(corpus, small_config())
    assert assigner.plan.bands["urdu"].unmet_arms == ()
    assert "B" in assigner.plan.bands["code_switched"].unmet_arms


def test_source_breakdown_is_recorded():
    config = small_config()
    assigner = SplitAssigner(config)
    corpus = make_corpus(2_000, jitter=True)
    for doc_id, text, population in corpus:
        assigner.measure(doc_id, text, population)
    assigner.seal()
    for doc_id, text, population in corpus:
        assigner.assign(doc_id, text, population, source="urdu-wikipedia")
    assert sum(assigner.log.by_source.values()) == 2_000
    assert assigner.log.by_source["urdu-wikipedia/train"] > 0


# ---------------------------------------------------------------------------
# Sampling — Finding G's softened form
# ---------------------------------------------------------------------------


def test_a_sampled_pass_solves_to_the_same_boundaries():
    """A split assignment is per-document, so a sample estimates the quantile honestly."""
    corpus = make_corpus(40_000, chars=200, jitter=True)
    config = small_config(population_targets={"urdu": 120_000}, chars_per_token={"urdu": 3.5})

    full = SplitAssigner(config)
    for doc_id, text, population in corpus:
        full.measure(doc_id, text, population)
    full_plan = full.seal()

    rate = 0.25
    sampled = SplitAssigner(config, sample_rate=rate)
    for doc_id, text, population in corpus:
        # Sample on a salt of its own, exactly as ShardReader does.
        if bucket_of(doc_id, salt="sample", buckets=1_000) < rate * 1_000:
            sampled.measure(doc_id, text, population)
    sampled_plan = sampled.seal()

    for arm in config.arm_names:
        a = full_plan.bands["urdu"].arm_cuts[arm]
        b = sampled_plan.bands["urdu"].arm_cuts[arm]
        assert abs(a - b) / a < 0.05


def test_gate_g1_scales_a_sampled_pass_to_the_full_corpus():
    """Measured: a 5% FineWeb2 pass read 52.7M tokens and returned arm_a_only for a ~1.05B shard.

    An unscaled gate verdict means two different things depending on how the pass was invoked,
    which is Findings O and P's defect arriving at the one number in this stage that is a project
    decision rather than a statistic.
    """
    log = SplitAssigner(SplitConfig(), sample_rate=0.05).log
    log.chars["urdu/train"] = int(52_000_000 * 3.5)  # ~52M tokens measured at 5%
    gate = log.gate_g1()
    assert gate["clean_tokens_measured"] == pytest.approx(52_000_000, rel=0.01)
    assert gate["clean_tokens_estimated"] == pytest.approx(52_000_000 * 20, rel=0.01)
    assert gate["verdict"] == "pass"
    assert gate["scaled_by"] == pytest.approx(20.0)


def test_gate_g1_does_not_scale_an_unsampled_pass():
    log = SplitAssigner(SplitConfig()).log
    log.chars["urdu/train"] = int(52_000_000 * 3.5)
    gate = log.gate_g1()
    assert gate["clean_tokens_estimated"] == gate["clean_tokens_measured"]
    assert gate["verdict"] == "arm_a_only"


def test_a_sampled_arm_target_is_reported_at_the_rate_it_was_solved_at():
    corpus = make_corpus(4_000, jitter=True)
    assigner = SplitAssigner(small_config(), sample_rate=0.05)
    for doc_id, text, population in corpus:
        assigner.measure(doc_id, text, population)
    assigner.seal()
    for doc_id, text, population in corpus:
        assigner.assign(doc_id, text, population)
    arms = assigner.to_dict()["populations"]["urdu"]["arms"]["B"]
    assert arms["target_tokens_this_pass"] == pytest.approx(arms["target_tokens"] * 0.05, rel=0.01)


def test_sample_rate_is_recorded_on_the_plan():
    assigner = SplitAssigner(small_config(), sample_rate=0.05)
    assigner.seal()
    assert assigner.plan.sample_rate == 0.05
    assert assigner.to_dict()["sample_rate"] == 0.05


def test_sample_rate_of_one_is_not_a_sample():
    assert SplitAssigner(small_config(), sample_rate=1.0).sample_rate is None


@pytest.mark.parametrize("rate", [0.0, -0.1, 1.5])
def test_sample_rate_is_validated(rate):
    with pytest.raises(ValueError, match="sample_rate"):
        SplitAssigner(small_config(), sample_rate=rate)


# ---------------------------------------------------------------------------
# The plan, and the Week 5 re-solve
# ---------------------------------------------------------------------------


def test_plan_round_trips_through_json(tmp_path):
    _, assigner = assign_splits(make_corpus(3_000, jitter=True), small_config())
    path = tmp_path / "plan.json"
    assigner.plan.to_json_file(path)
    restored = SplitPlan.from_json_file(path)
    assert restored.config == assigner.plan.config
    assert restored.bands == assigner.plan.bands
    assert restored.histogram == assigner.plan.histogram


def test_a_corrected_fertility_re_solves_without_a_corpus_pass():
    """The whole reason stage 9 can run a week before the tokenizer exists."""
    corpus = make_corpus(20_000, chars=300, jitter=True)
    config = small_config(population_targets={"urdu": 120_000}, chars_per_token={"urdu": 3.5})
    _, assigner = assign_splits(corpus, config)

    corrected = SplitConfig.from_dict({**config.to_dict(), "chars_per_token": {"urdu": 4.5}})
    resolved = assigner.plan.resolve(corrected)

    # More characters per token means the same token budget needs more characters, so the cuts move
    # outward — and the arms stay nested through the change.
    assert resolved.bands["urdu"].arm_cuts["A"] > assigner.plan.bands["urdu"].arm_cuts["A"]
    assert resolved.bands["urdu"].arm_cuts["A"] < resolved.bands["urdu"].arm_cuts["B"]


def test_re_solving_a_plan_written_without_its_histogram_is_refused():
    """Caught while trimming committed artifacts: it returned every band at zero, and looked fine.

    Plans get their histogram stripped when superseded, so this is a real path, and the failure it
    produces is a complete plausible plan describing an empty corpus.
    """
    _, assigner = assign_splits(make_corpus(2_000, jitter=True), small_config())
    stripped = SplitPlan.from_dict(assigner.plan.to_dict(include_histogram=False))
    assert stripped.bands == assigner.plan.bands  # the measured bands still round-trip
    with pytest.raises(ValueError, match="carries no histogram"):
        stripped.resolve()


def test_re_solving_at_a_different_bucket_count_is_refused():
    _, assigner = assign_splits(make_corpus(1_000), small_config())
    with pytest.raises(ValueError, match="cannot re-solve"):
        assigner.plan.resolve(small_config(buckets=20_000))


def test_plan_can_be_written_without_its_histogram(tmp_path):
    _, assigner = assign_splits(make_corpus(1_000), small_config())
    path = tmp_path / "plan.json"
    assigner.plan.to_json_file(path, include_histogram=False)
    assert "histogram" not in json.loads(path.read_text(encoding="utf-8"))


def test_a_plan_from_a_different_config_is_refused():
    _, assigner = assign_splits(make_corpus(1_000), small_config())
    other = SplitAssigner(small_config(salt="ravaan/split/v2"))
    with pytest.raises(ValueError, match="refusing to assign into a different partition"):
        other.load_plan(assigner.plan)


# ---------------------------------------------------------------------------
# Phase discipline
# ---------------------------------------------------------------------------


def test_assign_before_seal_is_an_error():
    assigner = SplitAssigner(small_config())
    with pytest.raises(RuntimeError, match="before seal"):
        assigner.assign("doc:1", "text", "urdu")


def test_measure_after_seal_is_an_error():
    assigner = SplitAssigner(small_config())
    assigner.seal()
    with pytest.raises(RuntimeError, match="after seal"):
        assigner.measure("doc:1", "text", "urdu")


def test_seal_is_idempotent():
    assigner = SplitAssigner(small_config())
    assigner.measure("doc:1", "ا" * 100, "urdu")
    first = assigner.seal()
    assert assigner.seal() is first


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def test_report_carries_characters_and_estimated_tokens():
    _, assigner = assign_splits(make_corpus(3_000, jitter=True), small_config())
    payload = assigner.to_dict()
    urdu = payload["populations"]["urdu"]
    assert urdu["splits"]["train"]["chars"] > 0
    assert urdu["splits"]["train"]["tokens_estimated"] == round(
        urdu["splits"]["train"]["chars"] / 3.5
    )
    assert urdu["chars_per_word_measured"] > 0


def test_report_names_the_config_it_was_produced_under():
    _, assigner = assign_splits(make_corpus(500), small_config())
    payload = assigner.to_dict()
    assert payload["config_fingerprint"] == small_config().fingerprint()
    assert payload["splits_version"] == SPLITS_VERSION


def test_report_lists_unmet_arms():
    _, assigner = assign_splits(make_corpus(50, chars=100), small_config())
    assert "B" in assigner.to_dict()["unmet_arms"]["urdu"]


def test_arm_tokens_sum_the_populations():
    corpus = make_corpus(3_000, population="urdu", prefix="u", jitter=True, seed=1) + make_corpus(
        3_000, population="roman_urdu", prefix="r", jitter=True, seed=2
    )
    _, assigner = assign_splits(corpus, small_config())
    log = assigner.log
    expected = sum(
        log.tokens(population, log.arm_chars.get(f"{population}/A", 0))
        for population in ("urdu", "roman_urdu", "code_switched")
    )
    assert log.arm_tokens("A") == pytest.approx(expected)
