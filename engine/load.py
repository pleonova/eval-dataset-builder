"""Read and validate the long ratings CSV."""
from pathlib import Path

import pandas as pd

from config import CRITERIA, LEVELS

RATINGS_PATH = Path(__file__).resolve().parent.parent / "data" / "ratings.csv"
COLUMNS = ["item_id", "criterion", "rater_id", "label", "round"]


def load_ratings(path: Path | str = RATINGS_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"label": "string"})
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"ratings file is missing columns: {missing}")

    # Blank or missing ratings are dropped, never filled
    df["label"] = df["label"].str.strip()
    df = df[df["label"].notna() & (df["label"] != "")].copy()

    bad_labels = set(df["label"]) - set(LEVELS)
    if bad_labels:
        raise ValueError(f"unknown labels: {sorted(bad_labels)}")
    bad_criteria = set(df["criterion"]) - set(CRITERIA)
    if bad_criteria:
        raise ValueError(f"unknown criteria: {sorted(bad_criteria)}")

    df["label"] = df["label"].astype(str)
    df["round"] = df["round"].astype(int)
    df["score"] = df["label"].map({level: i + 1 for i, level in enumerate(LEVELS)})
    return df.reset_index(drop=True)


def is_expert(df: pd.DataFrame) -> pd.Series:
    return df["rater_id"].str.startswith("expert_")


def is_judge(df: pd.DataFrame) -> pd.Series:
    return df["rater_id"].str.startswith("judge_run")


def round1_experts(df: pd.DataFrame) -> pd.DataFrame:
    return df[is_expert(df) & (df["round"] == 1)]
