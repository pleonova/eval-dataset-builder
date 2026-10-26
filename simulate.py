"""Write data/ratings.csv and data/truth.json with planted truth (seed 42).

Run: python simulate.py
"""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from config import CRITERIA, LEVELS

SEED = 42
N_ITEMS = 60
ROUND1_EXPERTS = ["expert_a", "expert_b", "expert_c", "expert_d"]
ROUND2_EXPERTS = ["expert_e", "expert_f"]
JUDGE_RUNS = ["judge_run1", "judge_run2", "judge_run3"]

EXPERT_ACCURACY = 0.80
CONFUSING_CRITERION = "vocabulary"
CONFUSED_LEVELS = (2, 3)            # moderately_complex <-> very_complex
CONFUSED_ACCURACY = 0.50            # on the confusing criterion, for those two levels
SUBJECTIVE_SHARE = 0.15
ROUND2_SKIP_SHARE = 0.50            # split items still waiting for round 2 (Re-rate)
JUDGE_ACCURACY = 0.85
JUDGE_FLIP = 0.08                   # chance a single judge run drifts one level

DATA_DIR = Path(__file__).resolve().parent / "data"


def name(level: int) -> str:
    return LEVELS[level - 1]


def one_off(rng, level: int) -> int:
    if level == 1:
        return 2
    if level == 4:
        return 3
    return level + rng.choice([-1, 1])


def expert_label(rng, true: int, criterion: str) -> int:
    if criterion == CONFUSING_CRITERION and true in CONFUSED_LEVELS:
        if rng.random() < CONFUSED_ACCURACY:
            return true
        return CONFUSED_LEVELS[1] if true == CONFUSED_LEVELS[0] else CONFUSED_LEVELS[0]
    return true if rng.random() < EXPERT_ACCURACY else one_off(rng, true)


def is_split(labels: list[int]) -> bool:
    return Counter(labels).most_common(1)[0][1] < 3


def main() -> None:
    rng = np.random.default_rng(SEED)
    rows = []
    truth = {}
    split_pairs = []

    def add(item_id, criterion, rater_id, level, round_):
        rows.append({"item_id": item_id, "criterion": criterion, "rater_id": rater_id,
                     "label": name(level), "round": round_})

    for i in range(1, N_ITEMS + 1):
        item_id = f"p_{i:03d}"
        truth[item_id] = {}
        for criterion in CRITERIA:
            subjective = rng.random() < SUBJECTIVE_SHARE
            if subjective:
                low = int(rng.integers(1, 4))
                split = [low, low + 1]
                labels = [low, low, low + 1, low + 1]
                rng.shuffle(labels)
                true = None
            else:
                true = int(rng.choice([1, 2, 3, 4], p=[0.2, 0.3, 0.3, 0.2]))
                labels = [expert_label(rng, true, criterion) for _ in ROUND1_EXPERTS]
                split = None

            for rater_id, level in zip(ROUND1_EXPERTS, labels):
                add(item_id, criterion, rater_id, int(level), 1)

            if subjective:
                pick = int(rng.choice(split))
                judge = [pick] * len(JUDGE_RUNS)
            else:
                base = true if rng.random() < JUDGE_ACCURACY else one_off(rng, true)
                judge = [one_off(rng, base) if rng.random() < JUDGE_FLIP else base
                         for _ in JUDGE_RUNS]
            for rater_id, level in zip(JUDGE_RUNS, judge):
                add(item_id, criterion, rater_id, level, 1)

            truth[item_id][criterion] = {
                "true_level": name(true) if true else None,
                "subjective": subjective,
                "split_levels": [name(x) for x in split] if split else None,
                "round2": False,
            }
            if is_split([int(x) for x in labels]):
                split_pairs.append((item_id, criterion, subjective, true, split, set(labels)))

    # Round 2: some split items get 2 new experts; the rest still wait in Re-rate
    n_skip = max(3, round(ROUND2_SKIP_SHARE * len(split_pairs)))
    skip = set(rng.choice(len(split_pairs), size=n_skip, replace=False).tolist())
    # Round 2 siding with the truth only resolves the split if the truth is one side of it
    skip |= {k for k, p in enumerate(split_pairs) if not p[2] and p[3] not in p[5]}
    for k, (item_id, criterion, subjective, true, split, _) in enumerate(split_pairs):
        if k in skip:
            continue
        levels = split if subjective else [true, true]
        for rater_id, level in zip(ROUND2_EXPERTS, levels):
            add(item_id, criterion, rater_id, level, 2)
        truth[item_id][criterion]["round2"] = True

    DATA_DIR.mkdir(exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "ratings.csv", index=False)
    (DATA_DIR / "truth.json").write_text(json.dumps({
        "seed": SEED,
        "levels": LEVELS,
        "confusing_criterion": CONFUSING_CRITERION,
        "items": truth,
    }, indent=2))

    summarize(df, truth)


def summarize(df: pd.DataFrame, truth: dict) -> None:
    r1 = df[df["rater_id"].isin(ROUND1_EXPERTS)]
    agree3 = (r1.groupby(["criterion", "item_id"])["label"]
                .agg(lambda s: s.value_counts().iloc[0] >= 3)
                .groupby("criterion").mean())
    flat = [(c, t) for item in truth.values() for c, t in item.items()]
    print(f"Wrote {len(df)} rows to data/ratings.csv and data/truth.json")
    print("\nShare of items where 3+ round-1 experts agree:")
    for criterion in CRITERIA:
        print(f"  {criterion:22s} {agree3[criterion]:.2f}")
    print(f"\nSubjective pairs: {sum(t['subjective'] for _, t in flat)} of {len(flat)}")
    n_r2 = sum(t["round2"] for _, t in flat)
    n_split = int((r1.groupby(["criterion", "item_id"])["label"]
                     .agg(lambda s: s.value_counts().iloc[0] < 3)).sum())
    print(f"Round-1 split pairs: {n_split}  (with round 2: {n_r2}, left for Re-rate: {n_split - n_r2})")


if __name__ == "__main__":
    main()
