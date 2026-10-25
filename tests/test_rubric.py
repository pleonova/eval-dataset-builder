import json

import pytest

from rubric.analyze import check_rule, load_dry_run, rubric

ITEMS = [f"pc_{i:02d}" for i in range(1, 11)]
MODELS = ["model_a", "model_b"]
STEADY = ["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex",
          "slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex",
          "moderately_complex", "very_complex"]


def ratings(criterion: str, label_for) -> list[dict]:
    return [{"model": m, "provider": m, "run": run, "item_id": item, "criterion": criterion,
             "label": label_for(m, run, i), "clause": ""}
            for m in MODELS for run in (1, 2, 3) for i, item in enumerate(ITEMS)]


def steady(model, run, i):
    return STEADY[i]


def confused(model, run, i):
    """Moderately vs very complex on most passages: the models disagree and model_b flips."""
    if STEADY[i] not in ("moderately_complex", "very_complex") and i % 3:
        return STEADY[i]
    if model == "model_a":
        return "moderately_complex"
    return "very_complex" if run != 2 else "moderately_complex"


@pytest.fixture
def dry_run(tmp_path):
    path = tmp_path / "dry_run.json"
    path.write_text(json.dumps({"ratings": ratings("vocabulary", confused) + ratings("sentence_structure", steady)}))
    return path


def test_steady_rule_is_clear(dry_run):
    df = load_dry_run(dry_run)
    rule = check_rule("sentence_structure", df[df["criterion"] == "sentence_structure"])
    assert rule["clear"]
    assert rule["alpha"] == pytest.approx(1.0)
    assert rule["flipped"] == 0
    assert rule["showed"] == "Agreed, and gave the same answer every run"
    assert rule["fix"] == "None"


def test_confusing_rule_names_the_levels(dry_run):
    df = load_dry_run(dry_run)
    rule = check_rule("vocabulary", df[df["criterion"] == "vocabulary"])
    assert not rule["clear"]
    assert rule["confused"] == ("moderately_complex", "very_complex")
    assert "moderately complex and very complex" in rule["fix"]


def test_verdict_counts_unclear_rules(dry_run):
    result = rubric(dry_run)
    assert result.status == "weak"
    assert result.value == {"vocabulary": False, "sentence_structure": True}
    assert result.details["headline"] == "Not ready: fix 1 of 2 rules before experts rate"
    assert not result.details["ready"]


def test_missing_dry_run_is_a_placeholder(tmp_path):
    result = rubric(tmp_path / "missing.json")
    assert result.status == "na"
    assert result.reading.startswith("Coming next")


def test_savings_line_matches_spec(dry_run):
    assert rubric(dry_run).details["savings"] == (
        "One expert round is 30 passages × 3 experts × 6 minutes = 9 hours ($540 at $60/hour). "
        "3 revision rounds cost $1,620, and a pre-checked rubric needs one.")
