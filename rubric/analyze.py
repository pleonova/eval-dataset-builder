"""Read data/dry_run.json and decide, per rubric rule, whether the AI raters applied it clearly."""
import json
from collections import Counter
from itertools import combinations
from pathlib import Path

import krippendorff
import pandas as pd

from config import (ALPHA_FAIR, COST_PER_HOUR, LEVELS, MINUTES_PER_LABEL, PILOT_EXPERTS, PILOT_ITEMS,
                    RUBRIC_MAX_FLIP, REVISION_ROUNDS)
from result import ModuleResult

DRY_RUN_PATH = Path(__file__).resolve().parent.parent / "data" / "dry_run.json"
SCORES = {level: i + 1 for i, level in enumerate(LEVELS)}


def load_dry_run(path: Path | str = DRY_RUN_PATH) -> pd.DataFrame:
    ratings = json.loads(Path(path).read_text())["ratings"]
    return pd.DataFrame(ratings, columns=["model", "provider", "run", "item_id", "criterion", "label", "clause"])


def flip_rate(runs: pd.DataFrame) -> tuple[int, int]:
    """Passages where at least one model's runs disagree, out of all passages."""
    flipped = runs.groupby(["item_id", "model"])["label"].nunique().gt(1).groupby("item_id").any()
    return int(flipped.sum()), len(flipped)


def ai_alpha(runs: pd.DataFrame) -> float:
    """Ordinal alpha with every model-run as a rater. All runs giving one label counts as full agreement."""
    if runs["label"].nunique() == 1:
        return 1.0
    matrix = (runs.assign(rater=runs["model"] + "#" + runs["run"].astype(str), score=runs["label"].map(SCORES))
                  .pivot_table(index="rater", columns="item_id", values="score", aggfunc="first"))
    value = krippendorff.alpha(reliability_data=matrix.to_numpy(dtype=float), level_of_measurement="ordinal",
                               value_domain=list(SCORES.values()))
    return 1.0 if pd.isna(value) else float(value)


def confused_levels(runs: pd.DataFrame) -> tuple[str, str] | None:
    """The pair of levels that most often sit side by side in the answers for one passage."""
    pairs = Counter()
    for _, labels in runs.groupby("item_id")["label"]:
        counts = Counter(labels)
        for a, b in combinations(sorted(counts, key=SCORES.get), 2):
            pairs[(a, b)] += counts[a] * counts[b]
    return pairs.most_common(1)[0][0] if pairs else None


def check_rule(criterion: str, runs: pd.DataFrame) -> dict:
    alpha = ai_alpha(runs)
    flipped, items = flip_rate(runs)
    clear = alpha >= ALPHA_FAIR and flipped / items <= RUBRIC_MAX_FLIP
    pair = confused_levels(runs)
    changed = f"changed answers on {flipped} of {items} passages"

    if clear and not pair:
        showed = "Agreed, and gave the same answer every run"
    elif clear:
        showed = f"Mostly agreed; {changed}" if flipped else "Mostly agreed, and gave the same answer every run"
    else:
        between = f"{pair[0].replace('_', ' ')} and {pair[1].replace('_', ' ')}"
        split = alpha < ALPHA_FAIR
        showed = (f"Split between {between}" + (f", and {changed}" if flipped else "") if split
                  else f"{changed.capitalize()}, mostly between {between}")
    fix = (f"Sharpen the line between {pair[0].replace('_', ' ')} and {pair[1].replace('_', ' ')}, "
           f"with an anchor example at that boundary") if not clear else "None"
    return {
        "criterion": criterion,
        "clear": clear,
        "alpha": alpha,
        "flipped": flipped,
        "items": items,
        "flip_rate": flipped / items,
        "confused": pair,
        "showed": showed,
        "fix": fix,
    }


def savings_line() -> str:
    hours = PILOT_ITEMS * PILOT_EXPERTS * MINUTES_PER_LABEL / 60
    cost = hours * COST_PER_HOUR
    return (f"One expert round is {PILOT_ITEMS} passages × {PILOT_EXPERTS} experts × {MINUTES_PER_LABEL} minutes "
            f"= {hours:.0f} hours (${cost:,.0f} at ${COST_PER_HOUR}/hour). {REVISION_ROUNDS} revision rounds cost "
            f"${cost * REVISION_ROUNDS:,.0f}, and a pre-checked rubric needs one.")


def rubric(path: Path | str = DRY_RUN_PATH) -> ModuleResult:
    if not Path(path).exists():
        return ModuleResult("rubric", None, "na",
                            "Coming next: run python -m rubric.dry_run to rate the sample passages with AI raters.")
    df = load_dry_run(path)
    if df.empty:
        return ModuleResult("rubric", None, "na", "The AI dry run has no ratings yet.")

    rules = [check_rule(c, g) for c, g in df.groupby("criterion", sort=False)]
    unclear = [r for r in rules if not r["clear"]]
    if unclear:
        first = unclear[0]
        name = first["criterion"].replace("_", " ")
        low, high = (level.replace("_", " ") for level in first["confused"])
        headline = f"Not ready: fix {len(unclear)} of {len(rules)} rules before experts rate"
        reading = (f"The AI raters could not apply the {name} rule the same way, mostly between {low} and {high}. "
                   f"Sharpen that line in the rubric, then rerun the dry run.")
    else:
        headline = "Ready for experts: every rule reads clearly"
        reading = ("The AI raters applied every rule the same way across models and runs. "
                   "Start the expert pilot to see whether experts agree too.")
    return ModuleResult(
        name="rubric",
        value={r["criterion"]: r["clear"] for r in rules},
        status="weak" if unclear else "good",
        reading=reading,
        details={
            "headline": headline,
            "ready": not unclear,
            "rules": rules,
            "models": sorted(df["model"].unique()),
            "runs": int(df["run"].nunique()),
            "items": int(df["item_id"].nunique()),
            "savings": savings_line(),
            "ratings": df,
        },
    )
