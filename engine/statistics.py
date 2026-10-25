"""Statistics view: alpha by criterion with ranges grouped by passage, confusion between levels, per-rater kappa."""
from itertools import combinations

import krippendorff
import numpy as np
import pandas as pd

from config import ALPHA_BOOT, CRITERIA, LEVELS
from engine.ai_checks import expert_kappas, judge_vs_experts
from engine.alpha import alpha_status
from engine.buckets import bucket_table
from engine.load import round1_experts
from result import ModuleResult


def _alpha_matrix(matrix: np.ndarray) -> float:
    return float(krippendorff.alpha(
        reliability_data=matrix,
        level_of_measurement="ordinal",
        value_domain=list(range(1, len(LEVELS) + 1)),
    ))


def alpha_by_criterion(df: pd.DataFrame, n_boot: int = ALPHA_BOOT, seed: int = 0) -> ModuleResult:
    """Alpha per criterion with a 95% range from resampling whole passages, next to round-2 and Trusted shares."""
    experts = round1_experts(df)
    table = bucket_table(df)
    if experts.empty or table.empty:
        return ModuleResult("alpha_by_criterion", None, "na", "No expert ratings to measure agreement on.")

    rng = np.random.default_rng(seed)
    rows = []
    for criterion in CRITERIA:
        subset = experts[experts["criterion"] == criterion]
        if subset.empty:
            continue
        matrix = subset.pivot_table(index="rater_id", columns="item_id", values="score",
                                    aggfunc="first").to_numpy(dtype=float)
        n = matrix.shape[1]
        boots = [_alpha_matrix(matrix[:, rng.integers(0, n, n)]) for _ in range(n_boot)]
        value = _alpha_matrix(matrix)
        crit = table[table["criterion"] == criterion]
        rows.append({
            "criterion": criterion,
            "alpha": value,
            "low": float(np.percentile(boots, 2.5)),
            "high": float(np.percentile(boots, 97.5)),
            "status": alpha_status(value),
            "round2_share": float(crit["split"].mean()),
            "trusted_share": float((crit["bucket"] == "Trusted").mean()),
            "items": len(crit),
        })

    weakest = min(rows, key=lambda r: r["alpha"])
    others = [r for r in rows if r is not weakest]
    name = weakest["criterion"].replace("_", " ")
    reading = (f"{name.capitalize()} has the lowest first-try agreement (alpha {weakest['alpha']:.2f}, "
               f"range {weakest['low']:.2f} to {weakest['high']:.2f}). ")
    if others and weakest["high"] < min(r["low"] for r in others):
        reading += "Its range sits below the others, so the gap is not chance."
    else:
        reading += "Its range overlaps the others, so more passages are needed to be sure."
    return ModuleResult(
        name="alpha_by_criterion",
        value={r["criterion"]: r["alpha"] for r in rows},
        status=weakest["status"],
        reading=reading,
        details={"rows": rows, "weakest": weakest["criterion"],
                 "headline": f"{name.capitalize()} has the lowest expert agreement"},
    )


def level_confusion(df: pd.DataFrame) -> ModuleResult:
    """Every pair of round-1 experts on the same passage, counted by the two levels they gave."""
    experts = round1_experts(df)
    if experts.empty:
        return ModuleResult("confusion", None, "na", "No expert ratings yet.")

    rows = []
    for criterion, g in experts.groupby("criterion"):
        counts = pd.DataFrame(0, index=LEVELS, columns=LEVELS)
        for _, item in g.groupby("item_id"):
            for a, b in combinations(item["label"], 2):
                counts.loc[a, b] += 1
                if a != b:
                    counts.loc[b, a] += 1
        for a in LEVELS:
            for b in LEVELS:
                rows.append({"criterion": criterion, "row": a, "col": b, "pairs": int(counts.loc[a, b])})
    matrix = pd.DataFrame(rows)

    off = matrix[matrix["row"] < matrix["col"]]  # each disagreeing pair once
    top = {}
    for criterion, g in off.groupby("criterion"):
        best = g.loc[g["pairs"].idxmax()]
        top[criterion] = {"pair": (best["row"], best["col"]), "pairs": int(best["pairs"]),
                          "share": float(best["pairs"] / g["pairs"].sum()) if g["pairs"].sum() else 0.0}
    worst = max(top, key=lambda c: top[c]["pairs"])
    a, b = (level.replace("_", " ") for level in top[worst]["pair"])
    reading = (f"On {worst.replace('_', ' ')}, {top[worst]['share']:.0%} of expert disagreements are "
               f"{a} against {b}. A clearer line between those two levels in the rubric would help most.")
    return ModuleResult(
        name="confusion",
        value=top[worst]["pairs"],
        status="na",
        reading=reading,
        details={"matrix": matrix, "top": top, "worst": worst,
                 "headline": f"Experts mix up {a} and {b} most"},
    )


def rater_kappas(df: pd.DataFrame) -> ModuleResult:
    """Each expert against the majority of the others, and the AI judge against expert consensus, on Trusted items."""
    kappas = expert_kappas(df)
    judge = judge_vs_experts(df)
    if not kappas:
        return ModuleResult("rater_kappas", None, "na", "Not enough Trusted items to compare raters.")

    rows = [{"rater": r, "kappa": k, "kind": "Expert"} for r, k in sorted(kappas.items())]
    if judge.value is not None:
        rows.append({"rater": "AI judge", "kappa": judge.value, "kind": "AI judge"})
    low, high = min(kappas.values()), max(kappas.values())
    ceiling = sum(kappas.values()) / len(kappas)
    weakest = min(kappas, key=kappas.get)
    reading = (f"Experts score {low:.2f} to {high:.2f} against each other, with {weakest.replace('_', ' ')} "
               f"lowest. ")
    if judge.value is not None:
        place = "inside" if low <= judge.value <= high else ("above" if judge.value > high else "below")
        reading += f"The AI judge scores {judge.value:.2f}, {place} that range."
    return ModuleResult(
        name="rater_kappas",
        value=judge.value,
        status=judge.status,
        reading=reading,
        details={"rows": rows, "expert_range": (low, high), "ceiling": ceiling,
                 "headline": ("The AI judge scores like an expert" if judge.status == "good"
                              else "The AI judge scores below the experts")},
    )
