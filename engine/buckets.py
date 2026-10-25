"""Sort each item and criterion into Trusted, Re-rate, or No expert consensus."""
import pandas as pd

from config import BUCKETS, TRUSTED_FAIR, TRUSTED_GOOD
from engine.consensus import majority
from engine.load import is_expert
from result import ModuleResult


def classify(round1: list[str], round2: list[str]) -> tuple[str, str | None]:
    """Return (bucket, label) for one item and criterion."""
    counts = pd.Series(round1).value_counts()
    if counts.iloc[0] >= 3:
        return "Trusted", counts.index[0]
    if not round2:
        return "Re-rate", None
    # Round 2 sides clearly with one side of the split: the new experts agree,
    # on a label round 1 already gave
    sides = set(counts[counts == counts.iloc[0]].index)
    pick = majority(round2)
    if len(set(round2)) == 1 and pick in sides:
        return "Trusted", pick
    return "No expert consensus", None


def bucket_table(df: pd.DataFrame) -> pd.DataFrame:
    experts = df[is_expert(df)]
    rows = []
    for (item_id, criterion), g in experts.groupby(["item_id", "criterion"]):
        round1 = g.loc[g["round"] == 1, "label"].tolist()
        round2 = g.loc[g["round"] == 2, "label"].tolist()
        if not round1:
            continue
        bucket, label = classify(round1, round2)
        rows.append({
            "item_id": item_id,
            "criterion": criterion,
            "bucket": bucket,
            "label": label,
            "round1": ", ".join(sorted(round1)),
            "round2": ", ".join(sorted(round2)),
        })
    return pd.DataFrame(rows)


def bucket_status(trusted_share: float) -> str:
    if trusted_share >= TRUSTED_GOOD:
        return "good"
    if trusted_share >= TRUSTED_FAIR:
        return "fair"
    return "weak"


def buckets(df: pd.DataFrame) -> ModuleResult:
    table = bucket_table(df)
    if table.empty:
        return ModuleResult("buckets", None, "na", "No expert ratings to sort into buckets.")

    counts = table["bucket"].value_counts().reindex(BUCKETS, fill_value=0)
    shares = {b: float(counts[b] / len(table)) for b in BUCKETS}
    reading = (
        f"{shares['Trusted']:.0%} of labels are safe to tune against. "
        f"{counts['Re-rate']} need 2 more experts, and "
        f"{counts['No expert consensus']} have no expert consensus."
    )
    by_criterion = (table.groupby("criterion")["bucket"].value_counts(normalize=True)
                         .unstack(fill_value=0.0).reindex(columns=BUCKETS, fill_value=0.0))
    return ModuleResult(
        name="buckets",
        value=shares,
        status=bucket_status(shares["Trusted"]),
        reading=reading,
        details={"counts": counts.to_dict(), "by_criterion": by_criterion, "items": table},
    )
