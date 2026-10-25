import pytest

from engine.ai_checks import expert_kappas, judge_vs_experts, self_consistency
from engine.load import load_ratings


@pytest.fixture(scope="module")
def ratings():
    return load_ratings()


def test_expert_range_is_one_kappa_per_round1_expert(ratings):
    kappas = expert_kappas(ratings)
    assert set(kappas) == {"expert_a", "expert_b", "expert_c", "expert_d"}
    assert all(0.5 < k < 1 for k in kappas.values())


def test_judge_kappa_reaches_expert_range(ratings):
    result = judge_vs_experts(ratings)
    low, high = result.details["expert_range"]
    assert low <= result.details["ceiling"] <= high
    # Planted judge is about 85% right on Trusted items, so it should reach the human bar
    assert low <= result.value < 1
    assert result.status == "good"


def test_self_consistency_reflects_planted_flips(ratings):
    # Each run drifts with 8% chance, so all 3 agree on roughly 0.92^3 of non-subjective items
    assert 0.70 <= self_consistency(ratings).value <= 0.95
