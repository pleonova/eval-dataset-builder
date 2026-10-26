import json
from pathlib import Path

import pytest

from engine.alpha import expert_alpha
from engine.buckets import buckets, classify
from engine.consensus import majority
from engine.load import load_ratings

TRUTH = json.loads((Path(__file__).resolve().parent.parent / "data" / "truth.json").read_text())["items"]


@pytest.fixture(scope="module")
def ratings():
    return load_ratings()


@pytest.fixture(scope="module")
def table(ratings):
    return buckets(ratings).details["items"]


def planted(row, key):
    return TRUTH[row["item_id"]][row["criterion"]][key]


def test_majority_tie_has_no_label():
    assert majority(["a", "a", "b", "b"]) is None
    assert majority(["a", "a", "b", "c"]) == "a"


@pytest.mark.parametrize("round1, round2, expected", [
    (["a", "a", "a", "b"], [], ("Trusted", "a")),
    (["a", "a", "b", "b"], [], ("Re-rate", None)),
    (["a", "a", "b", "b"], ["b", "b"], ("Trusted", "b")),
    (["a", "a", "b", "b"], ["a", "b"], ("No expert consensus", None)),
    (["a", "a", "b", "b"], ["c", "c"], ("No expert consensus", None)),
])
def test_classify_rules(round1, round2, expected):
    assert classify(round1, round2) == expected


def test_every_pair_is_bucketed(table):
    assert len(table) == 60 * 3


def test_no_consensus_is_the_planted_subjective_slice(table):
    no_consensus = table[table["bucket"] == "No expert consensus"]
    expected = table[table.apply(lambda r: planted(r, "subjective") and planted(r, "round2"), axis=1)]
    assert set(zip(no_consensus.item_id, no_consensus.criterion)) == set(zip(expected.item_id, expected.criterion))


def test_rerate_items_have_no_round2(table):
    rerate = table[table["bucket"] == "Re-rate"]
    # Most round-1 splits are still waiting for round 2, so Re-rate is a large slice
    assert 25 <= len(rerate) <= 55
    assert not rerate.apply(lambda r: planted(r, "round2"), axis=1).any()


def test_shares_near_planted_truth(ratings):
    shares = buckets(ratings).value
    # Subjective items only show as No expert consensus once round 2 splits too; the rest wait in Re-rate
    subjective = sum(t["subjective"] and t["round2"] for item in TRUTH.values() for t in item.values()) / 180
    assert abs(shares["No expert consensus"] - subjective) <= 0.05
    assert 0.60 <= shares["Trusted"] <= 0.80


def test_trusted_labels_mostly_match_truth(table):
    trusted = table[table["bucket"] == "Trusted"]
    right = trusted.apply(lambda r: r["label"] == planted(r, "true_level"), axis=1)
    assert right.mean() >= 0.85


def test_vocabulary_has_lowest_alpha(ratings):
    result = expert_alpha(ratings)
    by_criterion = result.details["by_criterion"]
    assert result.details["weakest"] == "vocabulary"
    assert by_criterion["vocabulary"]["status"] == "weak"
    assert 0 < result.value < 1
