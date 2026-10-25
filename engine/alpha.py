"""Krippendorff's alpha (ordinal) on round-1 experts, per criterion and overall."""
import krippendorff
import pandas as pd

from config import ALPHA_FAIR, ALPHA_GOOD, CRITERIA, LEVELS
from engine.load import round1_experts
from result import ModuleResult


def alpha_status(value: float) -> str:
    if value >= ALPHA_GOOD:
        return "good"
    if value >= ALPHA_FAIR:
        return "fair"
    return "weak"


def _alpha(experts: pd.DataFrame, columns: list[str]) -> float:
    matrix = experts.pivot_table(index="rater_id", columns=columns, values="score", aggfunc="first")
    return float(krippendorff.alpha(
        reliability_data=matrix.to_numpy(dtype=float),
        level_of_measurement="ordinal",
        value_domain=list(range(1, len(LEVELS) + 1)),
    ))


def expert_alpha(df: pd.DataFrame) -> ModuleResult:
    experts = round1_experts(df)
    if experts.empty:
        return ModuleResult("alpha", None, "na", "No expert ratings to measure agreement on.")

    overall = _alpha(experts, ["criterion", "item_id"])
    by_criterion = {}
    for criterion in CRITERIA:
        subset = experts[experts["criterion"] == criterion]
        if subset.empty:
            continue
        value = _alpha(subset, ["item_id"])
        by_criterion[criterion] = {"alpha": value, "status": alpha_status(value)}

    weakest = min(by_criterion, key=lambda c: by_criterion[c]["alpha"])
    reading = (
        f"Overall expert agreement is {alpha_status(overall)} (alpha {overall:.2f}). "
        f"{weakest.replace('_', ' ').capitalize()} is the weakest criterion "
        f"at {by_criterion[weakest]['alpha']:.2f}."
    )
    return ModuleResult(
        name="alpha",
        value=overall,
        status=alpha_status(overall),
        reading=reading,
        details={"by_criterion": by_criterion, "weakest": weakest},
    )
