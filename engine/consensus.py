"""Majority label per item and criterion, round-1 experts only."""
import pandas as pd

from engine.load import round1_experts


def majority(labels) -> str | None:
    """Most common label, or None when the top count is tied."""
    counts = pd.Series(list(labels)).value_counts()
    if counts.empty or (len(counts) > 1 and counts.iloc[0] == counts.iloc[1]):
        return None
    return counts.index[0]


def consensus(df: pd.DataFrame) -> pd.DataFrame:
    """One row per item and criterion: consensus label, top count, and number of experts."""
    rows = []
    for (item_id, criterion), g in round1_experts(df).groupby(["item_id", "criterion"]):
        counts = g["label"].value_counts()
        rows.append({
            "item_id": item_id,
            "criterion": criterion,
            "label": majority(g["label"]),
            "top_count": int(counts.iloc[0]),
            "n_experts": len(g),
        })
    return pd.DataFrame(rows)
