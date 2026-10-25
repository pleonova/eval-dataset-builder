"""Sort each item and criterion into Trusted, Re-rate, or No expert consensus."""
import numpy as np
import pandas as pd

from config import (BUCKETS, CRITERIA, COST_PER_HOUR, EXTRA_PASSAGES, MINUTES_PER_LABEL, RERATE_EXPERTS, ROUND2_FLAG_SHARE,
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
        details={"counts": counts.to_dict(), "by_criterion": by_criterion, "items": table, "help": BUCKET_HELP,
                 "label_help": label_help(table)},
    )


def label_help(table: pd.DataFrame) -> str:
    """Hover text for "labels": one concrete item, then the totals."""
    names = [c.replace("_", " ") for c in CRITERIA if c in set(table["criterion"])]
    listed = ", ".join(names[:-1]) + f", and {names[-1]}" if len(names) > 1 else names[0]
    n_items = table["item_id"].nunique()
    return (f"One label is the level experts gave one item on one criterion. Each item is rated on {listed}, "
            f"so it gets {len(names)} labels. {n_items} items × {len(names)} criteria = {len(table)} labels.")


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
        reading = (f"Experts split on less than {ROUND2_FLAG_SHARE:.0%} of items for every criterion, "
                   f"so the rating instructions read clearly.")
    else:
        top = flagged.index[0]
        name = top.replace("_", " ")
        reading = f"Experts split on {split[top]:.0%} of {name} items. Fix the wording before more items are rated."
    return ModuleResult(
        name="round2_flag",
        value=split.to_dict(),
        status="weak" if len(flagged) else "good",
        reading=reading,
        details={
            "flagged": list(flagged.index),
            "threshold": ROUND2_FLAG_SHARE,
            "help": {
                "criterion": "One thing experts rate the text on, like vocabulary or sentence structure.",
                "agreed": (f"At least 3 of 4 experts gave the same level. A criterion is flagged when experts split "
                           f"on {ROUND2_FLAG_SHARE:.0%} or more of its items, which may point to unclear rating "
                           f"instructions."),
            },
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
    """The recommendation for the Overview page: go or no go on the labels to tune against.

    No go while a criterion is flagged or labels wait for a re-rate. Then the card lists numbered steps, rubric
    first, since re-rating under wording that is about to change wastes the re-rate. Go only when both are clear
    and the Trusted share reaches TRUSTED_GOOD.
    `ai` (from `engine.ai_checks.stand_in`) only adds whether the AI matches experts on Trusted labels."""
    result = buckets(df)
    if result.value is None:
        return result
    counts = result.details["counts"]
    table = result.details["items"]
    flag = round2_flag(df)
    flagged = flag.details["flagged"]
    trusted, rerate, total = counts["Trusted"], counts["Re-rate"], sum(counts.values())
    no_consensus = counts["No expert consensus"]
    steps = []

    if flagged:
        name = flagged[0].replace("_", " ")
        is_trusted = table["bucket"] == "Trusted"
        in_flagged = table["criterion"].isin(flagged)
        steps.append({
            "action": "Clarify the rubric",
            "cost": "",
            "cost_help": "",
            "reading": (f"{name.capitalize()} criterion: test new wording in the Rubric tab, "
                        f"then spot-check its Trusted labels."),
            "term": "spot-check its Trusted labels",
            "term_help": (f"Only {name} labels are affected: the other criteria ({int((is_trusted & ~in_flagged).sum())} "
                          f"Trusted labels) keep their wording. If the fix only sharpens the wording, the "
                          f"{int((is_trusted & in_flagged).sum())} {name} Trusted labels most likely still hold, and the "
                          f"spot-check confirms it. If it changes what a level means, {name} needs re-rating."),
        })
    if rerate:
        hours = rerate * RERATE_EXPERTS * MINUTES_PER_LABEL / 60
        reading = f"Add {RERATE_EXPERTS} new experts to each."
        steps.append({
            "action": f"Re-rate {rerate} labels",
            "cost": f"{hours:.1f} expert hours · ${hours * COST_PER_HOUR:,.0f}",
            "cost_help": (f"{rerate} labels × {RERATE_EXPERTS} new experts × {MINUTES_PER_LABEL} minutes each = "
                          f"{hours:.1f} hours, at ${COST_PER_HOUR} per hour. Example rates."),
            "reading": reading,
        })

    risk = risk_help = ""
    if steps:
        causes = ("truly disagree, need more ratings, or read an unclear rubric differently" if flagged
                  else "truly disagree or just need more ratings")
        risk = ("Tuning now only on agreed labels could bias the AI toward easier items "
                "and make it unreliable on harder ones.")
        risk_help = (f"Experts disagree on the harder labels. Until we check whether they {causes}, "
                     f"those labels can't be used to tune or check the AI.")
        status = "fair"
    elif result.value["Trusted"] >= TRUSTED_GOOD:
        steps.append({
            "action": f"Tune on the {trusted} Trusted labels",
            "cost": "",
            "cost_help": "",
            "reading": ("Experts agree on these, and the AI matches them as well as experts match each other."
                        if ai is not None and ai.value else "Experts agree on these."),
        })
        if no_consensus:
            risk = (f"On the {no_consensus} No expert consensus labels there is no agreed answer, "
                    f"so the AI can't be checked there.")
        status = "good"
    else:
        steps.append({"action": "Need more ratings", "cost": "", "cost_help": "",
                      "reading": "Too few labels are Trusted to check the AI against yet."})
        status = "weak"
    return ModuleResult(
        name="verdict",
        value=steps[0]["action"],
        status=status,
        reading=steps[0]["reading"],
        details={"steps": steps, "risk": risk, "risk_help": risk_help, "counts": counts, "total": total},
    )


def trusted_range(df: pd.DataFrame) -> ModuleResult:
    """Trusted share with a 95% range grouped by item, today and with more items rated.

    No expert consensus labels are left out: they may be truly subjective, so no answer is right or wrong
    and they shouldn't count against the share. Re-rate labels stay in, since they still have a right answer."""
    table = bucket_table(df)
    scored = table[table["bucket"] != "No expert consensus"]
    if scored.empty:
        return ModuleResult("trusted_range", None, "na", "No expert ratings yet.")

    # Items keep different numbers of scored labels, so use a ratio with a range grouped by item
    per_item = (scored["bucket"] == "Trusted").groupby(scored["item_id"]).agg(["sum", "size"])
    n = len(per_item)
    share = float(per_item["sum"].sum() / per_item["size"].sum())
    resid = per_item["sum"] - share * per_item["size"]
    sd = float(np.sqrt((resid ** 2).sum() / (n - 1)) / per_item["size"].mean()) if n > 1 else 0.0
    rows = []
    for extra in [0] + EXTRA_PASSAGES:
        margin = float(1.96 * sd / np.sqrt(n + extra))
        rows.append({
            "label": "Today" if extra == 0 else f"+{extra} items",
            "items": n + extra,
            "low": max(0.0, share - margin),
            "high": min(1.0, share + margin),
            "margin": margin,
        })
    today = rows[0]
    unsafe = 1 - today["low"]
    warning = f"so up to about 1 in {round(1 / unsafe)} labels might not be correct." if unsafe else ""
    reading = (f"{share:.0%} of labels are Trusted, not counting No expert consensus, which may be truly subjective. "
               f"The true share could be as low as {today['low']:.0%}" + (f", {warning} " if warning else ". ")
               + "Rating more items or clearer rating instructions narrows it.")
    return ModuleResult(
        name="trusted_range",
        value=share,
        status="na",
        reading=reading,
        details={"rows": rows, "share": share, "unsafe": unsafe, "warning": warning,
                 "help": ("A 95% range for the Trusted share across the whole dataset: the true share most likely "
                          "falls inside it. No expert consensus labels are left out, since they may be truly "
                          "subjective. It is worked out item by item, so it narrows as more items are rated "
                          "or as experts agree more often on each item.")},
    )
