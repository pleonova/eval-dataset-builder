"""Sort each item and criterion into Trusted, Re-rate, or No expert consensus."""
import numpy as np
import pandas as pd

from config import (BUCKETS, COST_PER_HOUR, EXTRA_PASSAGES, MINUTES_PER_LABEL, RERATE_EXPERTS, ROUND2_FLAG_SHARE,
                    TRUSTED_FAIR, TRUSTED_GOOD)
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
            "split": pd.Series(round1).value_counts().iloc[0] < 3,
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
        details={"counts": counts.to_dict(), "by_criterion": by_criterion, "items": table, "help": BUCKET_HELP},
    )


def round2_flag(df: pd.DataFrame) -> ModuleResult:
    """Flag criteria where round 1 split on a large share of items, even if round 2 fixed most."""
    table = bucket_table(df)
    if table.empty:
        return ModuleResult("round2_flag", None, "na", "No expert ratings yet.")

    by_criterion = table.assign(trusted=table["bucket"] == "Trusted").groupby("criterion")
    split, n_split, n_items = by_criterion["split"].mean(), by_criterion["split"].sum(), by_criterion.size()
    trusted = by_criterion["trusted"].mean()
    flagged = split[split >= ROUND2_FLAG_SHARE].sort_values(ascending=False)
    rows = [{
        "criterion": c,
        "split": int(n_split[c]),
        "items": int(n_items[c]),
        "share": float(split[c]),
        "trusted": float(trusted[c]),
        "flagged": c in flagged.index,
    } for c in split.sort_values(ascending=False).index]

    if flagged.empty:
        reading = (f"Experts split on the first try on less than {ROUND2_FLAG_SHARE:.0%} of items "
                   f"for every criterion, so the rating instructions read clearly.")
    else:
        top = flagged.index[0]
        name = top.replace("_", " ")
        others = split.drop(flagged.index)
        compare = (f", against {others.min():.0%} to {others.max():.0%} on the other criteria"
                   if len(others) > 1 else "")
        reading = (f"On the {name} criterion, experts split on the first try on {n_split[top]} of {n_items[top]} items "
                   f"({split[top]:.0%}){compare}. A second round settled most of them, so {trusted[top]:.0%} ended up "
                   f"Trusted, but the instructions for rating {name} are likely unclear. Check them in the Rubric tab "
                   f"before the next round.")
    return ModuleResult(
        name="round2_flag",
        value=split.to_dict(),
        status="weak" if len(flagged) else "good",
        reading=reading,
        details={
            "flagged": list(flagged.index),
            "threshold": ROUND2_FLAG_SHARE,
            "rows": rows,
            "headline": (f"Instructions for rating the {flagged.index[0].replace('_', ' ')} criterion are likely unclear"
                         if len(flagged) else "Every criterion reads clearly"),
        },
    )


BUCKET_HELP = {
    "Trusted": (f"At least 3 of 4 experts gave the same level, or {RERATE_EXPERTS} new experts both sided "
                f"with one side of a split."),
    "Re-rate": (f"Experts split (no level got 3 of 4 votes) and nobody has rechecked it yet. "
                f"Next step: {RERATE_EXPERTS} new experts rate it."),
    "No expert consensus": (f"Experts split, and {RERATE_EXPERTS} new experts split the same way or picked a level "
                            f"no first-round expert gave. Likely subjective, so it is shown but not scored."),
}


def verdict(df: pd.DataFrame, ai: ModuleResult | None = None) -> ModuleResult:
    """One recommendation for the Overview page: go or no go on the labels to tune against.

    Re-rate comes first: tuning on Trusted labels alone would lean toward the easier passages. Go only when
    nothing is left to re-rate and the Trusted share reaches TRUSTED_GOOD.
    `ai` (from `engine.ai_checks.stand_in`) only adds whether the AI matches experts on Trusted labels."""
    result = buckets(df)
    if result.value is None:
        return result
    counts = result.details["counts"]
    flagged = round2_flag(df).details["flagged"]
    trusted, rerate, total = counts["Trusted"], counts["Re-rate"], sum(counts.values())

    hours = rerate * RERATE_EXPERTS * MINUTES_PER_LABEL / 60
    rerate_cost = f"{hours:.1f} expert hours · ${hours * COST_PER_HOUR:,.0f}"
    no_consensus = counts["No expert consensus"]
    risk = risk_help = ""
    cost_help = (f"{rerate} labels × {RERATE_EXPERTS} new experts × {MINUTES_PER_LABEL} minutes each = "
                 f"{hours:.1f} hours, at ${COST_PER_HOUR} per hour. Example rates.")

    if rerate:
        action = f"Re-rate {rerate} labels"
        cost = rerate_cost
        reading = (f"Experts split on these and nobody has rechecked them. "
                   f"Add {RERATE_EXPERTS} new experts on each.")
        risk = ("Tuning now only on agreed labels could bias the AI toward easier items "
                "and make it unreliable on harder ones.")
        risk_help = ("Experts disagree on the harder items. Until we check whether they truly disagree "
                     "or just need more ratings, those items can't be used to tune or check the AI.")
        status = "fair"
    elif result.value["Trusted"] >= TRUSTED_GOOD:
        action, cost = f"Tune on the {trusted} Trusted labels", ""
        reading = ("Experts agree on these, and the AI matches them as well as experts match each other."
                   if ai is not None and ai.value else "Experts agree on these.")
        if no_consensus:
            risk = (f"On the {no_consensus} No expert consensus labels there is no agreed answer, "
                    f"so the AI can't be checked there.")
        status = "good"
    elif flagged:
        name = flagged[0].replace("_", " ")
        action, cost = f"Clarify the {name} rubric", ""
        reading = f"Experts often split on the {name} criterion before a second round settled it."
        status = "fair"
    else:
        action, cost = "Need more ratings", ""
        reading = "Too few labels are Trusted to check the AI against yet."
        status = "weak"
    return ModuleResult(
        name="verdict",
        value=action,
        status=status,
        reading=reading,
        details={"action": action, "cost": cost, "cost_help": cost_help if cost else "", "risk": risk, "risk_help": risk_help, "counts": counts, "total": total},
    )


def trusted_range(df: pd.DataFrame) -> ModuleResult:
    """Trusted share with a 95% range grouped by passage, today and with more passages rated."""
    table = bucket_table(df)
    if table.empty:
        return ModuleResult("trusted_range", None, "na", "No expert ratings yet.")

    per_passage = (table["bucket"] == "Trusted").groupby(table["item_id"]).mean()
    share, sd, n = float(per_passage.mean()), float(per_passage.std(ddof=1)), len(per_passage)
    rows = []
    for extra in [0] + EXTRA_PASSAGES:
        margin = float(1.96 * sd / np.sqrt(n + extra))
        rows.append({
            "label": "Today" if extra == 0 else f"+{extra} items",
            "passages": n + extra,
            "low": max(0.0, share - margin),
            "high": min(1.0, share + margin),
            "margin": margin,
        })
    today, last = rows[0], rows[-1]
    unsafe = 1 - today["low"]
    warning = f"so up to about 1 in {round(1 / unsafe)} labels might not be correct." if unsafe else ""
    trusted = int((table["bucket"] == "Trusted").sum())
    reading = (f"{share:.0%} of the whole dataset is Trusted ({trusted} of all {len(table)} labels). "
               f"Across the whole dataset, the true share could be anywhere from "
               f"{today['low']:.0%} to {today['high']:.0%}" + (f", {warning} " if warning else ". ")
               + f"Two things narrow it: rating more items (another {EXTRA_PASSAGES[-1]} narrows it to "
               f"{last['low']:.0%} to {last['high']:.0%}), or more agreement between experts on each item, "
               f"for example from clearer rating instructions.")
    return ModuleResult(
        name="trusted_range",
        value=share,
        status="na",
        reading=reading,
        details={"rows": rows, "share": share, "unsafe": unsafe, "warning": warning,
                 "help": ("A 95% range for the Trusted share across the whole dataset: the true share most likely "
                          "falls inside it. It is worked out item by item, so it narrows as more items are rated "
                          "or as experts agree more often on each item.")},
    )
