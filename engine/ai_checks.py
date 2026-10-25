"""Can the AI judge stand in for an expert? Judge kappa vs expert range, AI ceiling, self-consistency."""
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from config import LEVELS, SELF_CONSISTENCY_FAIR, SELF_CONSISTENCY_GOOD
from engine.buckets import bucket_table
from engine.consensus import majority
from engine.load import is_judge, round1_experts
from result import ModuleResult

SCORES = {level: i + 1 for i, level in enumerate(LEVELS)}
KEY = ["item_id", "criterion"]


def qwk(a, b) -> float:
    """Quadratic weighted kappa on ordered labels."""
    return float(cohen_kappa_score(
        [SCORES[x] for x in a], [SCORES[x] for x in b],
        weights="quadratic", labels=list(SCORES.values()),
    ))


def judge_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per item and criterion: the judge's majority label and whether all runs agree."""
    rows = []
    for (item_id, criterion), g in df[is_judge(df)].groupby(KEY):
        runs = g.sort_values("rater_id")["label"].tolist()
        rows.append({
            "item_id": item_id,
            "criterion": criterion,
            "judge": majority(runs),
            "runs": ", ".join(runs),
            "consistent": len(set(runs)) == 1,
        })
    return pd.DataFrame(rows, columns=KEY + ["judge", "runs", "consistent"])


def _trusted(df: pd.DataFrame) -> pd.DataFrame:
    table = bucket_table(df)
    return table[table["bucket"] == "Trusted"] if not table.empty else table


def expert_kappas(df: pd.DataFrame, trusted: pd.DataFrame | None = None) -> dict[str, float]:
    """Each round-1 expert against the majority of the other three, on Trusted items."""
    trusted = _trusted(df) if trusted is None else trusted
    experts = round1_experts(df).merge(trusted[KEY], on=KEY)
    wide = experts.pivot_table(index=KEY, columns="rater_id", values="label", aggfunc="first")
    kappas = {}
    for rater in wide.columns:
        others = wide.drop(columns=rater)
        rest = others.apply(lambda r: majority(r.dropna()), axis=1)
        pairs = pd.DataFrame({"own": wide[rater], "rest": rest}).dropna()
        if not pairs.empty:
            kappas[rater] = qwk(pairs["own"], pairs["rest"])
    return kappas


def judge_vs_experts(df: pd.DataFrame) -> ModuleResult:
    trusted = _trusted(df)
    merged = trusted.merge(judge_table(df), on=KEY)
    judged = merged.dropna(subset=["label", "judge"])
    kappas = expert_kappas(df, trusted)
    if judged.empty or not kappas:
        return ModuleResult("judge_kappa", None, "na", "Not enough Trusted items to compare the judge with experts.")

    kappa = qwk(judged["judge"], judged["label"])
    low, high = min(kappas.values()), max(kappas.values())
    ceiling = sum(kappas.values()) / len(kappas)
    if kappa >= low:
        status = "good"
        reading = (f"The AI judge can stand in for an expert: kappa {kappa:.2f}, "
                   f"inside or above the expert range of {low:.2f} to {high:.2f}.")
    else:
        status = "weak"
        reading = (f"The AI judge cannot stand in for an expert yet: kappa {kappa:.2f}, "
                   f"below the expert range of {low:.2f} to {high:.2f}.")
    return ModuleResult(
        name="judge_kappa",
        value=kappa,
        status=status,
        reading=reading,
        details={
            "expert_kappas": kappas,
            "expert_range": (low, high),
            "ceiling": ceiling,
            "n_items": len(judged),
            "n_exact": int((judged["judge"] == judged["label"]).sum()),
            "n_no_majority": int(merged["judge"].isna().sum()),
            "interval": "Range coming next.",
        },
    )


def ai_ceiling(df: pd.DataFrame) -> ModuleResult:
    kappas = expert_kappas(df)
    if not kappas:
        return ModuleResult("ai_ceiling", None, "na", "Not enough Trusted items to set an AI ceiling.")
    ceiling = sum(kappas.values()) / len(kappas)
    return ModuleResult(
        name="ai_ceiling",
        value=ceiling,
        status="na",
        reading=(f"AI ceiling is {ceiling:.2f}: the best an AI judge can be expected to score, "
                 f"given how often experts agree."),
        details={"expert_kappas": kappas},
    )


def self_consistency_status(share: float) -> str:
    if share >= SELF_CONSISTENCY_GOOD:
        return "good"
    if share >= SELF_CONSISTENCY_FAIR:
        return "fair"
    return "weak"


def self_consistency(df: pd.DataFrame) -> ModuleResult:
    table = judge_table(df)
    if table.empty:
        return ModuleResult("self_consistency", None, "na", "No judge runs to check.")
    share = float(table["consistent"].mean())
    by_criterion = table.groupby("criterion")["consistent"].mean().to_dict()
    return ModuleResult(
        name="self_consistency",
        value=share,
        status=self_consistency_status(share),
        reading=f"The judge gives the same answer on all 3 runs for {share:.0%} of items.",
        details={"by_criterion": by_criterion, "flips": table[~table["consistent"]]},
    )


def subjective_items(df: pd.DataFrame) -> ModuleResult:
    """Judge label next to the experts' spread on No expert consensus items. Not scored."""
    table = bucket_table(df)
    if table.empty:
        return ModuleResult("subjective", None, "na", "No expert ratings yet.")
    subjective = table[table["bucket"] == "No expert consensus"]
    items = subjective[KEY + ["round1", "round2"]].merge(judge_table(df), on=KEY, how="left")
    reading = (f"{len(items)} items have no expert consensus. The judge's answers there "
               f"are shown, not scored.")
    return ModuleResult(
        name="subjective",
        value=len(items),
        status="na",
        reading=reading,
        details={"items": items},
    )


def stand_in(df: pd.DataFrame) -> ModuleResult:
    """Plain lines for the Decision page, one per bucket the AI is judged on."""
    judge = judge_vs_experts(df)
    if judge.value is None:
        return ModuleResult("stand_in", None, "na", judge.reading)
    n, exact = judge.details["n_items"], judge.details["n_exact"]
    answer = "yes" if judge.status == "good" else "not yet"
    lines = [
        {"bucket": "Trusted", "text": f"Trusted labels: {answer}, it matches experts on {exact} of {n}"},
        {"bucket": "No expert consensus",
         "text": "No expert consensus: it acts like one expert, so keep a person reviewing"},
    ]
    consistency = self_consistency(df)
    return ModuleResult(
        name="stand_in",
        value=judge.status == "good",
        status=judge.status,
        reading=lines[0]["text"],
        details={"lines": lines, "note": consistency.reading, "note_status": consistency.status},
    )
