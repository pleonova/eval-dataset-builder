from collections import Counter

import streamlit as st

from config import BUCKETS
from engine.ai_checks import stand_in, subjective_items
from engine.buckets import buckets, round2_flag, verdict
from engine.load import load_ratings
from result import ModuleResult

BLUE = "#2563eb"
BUCKET_COLORS = {"Trusted": "#4caf50", "Re-rate": "#f59e0b", "No expert consensus": "#ec7fa9"}
BUCKET_LINES = {
    "Trusted": ("Experts agree", "Use to test the AI"),
    "Re-rate": ("Experts split, not yet", "confirmed: add 2 experts"),
    "No expert consensus": ("Split held with new experts", "Likely subjective in practice"),
}

CSS = f"""
<style>
.eeb-principle {{ background: {BLUE}0f; border: 1px solid {BLUE}66; border-radius: 8px;
  padding: 10px 14px; font-size: 0.9rem; margin-bottom: 1rem; }}
.eeb-principle .sub {{ color: #6b7280; }}
.eeb-verdict {{ border: 2px solid {BLUE}; border-radius: 8px; padding: 14px 16px; margin-bottom: 1.5rem; }}
.eeb-verdict .top {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; }}
.eeb-verdict .action {{ font-size: 1.2rem; font-weight: 600; }}
.eeb-verdict .reason {{ margin-top: 6px; }}
.eeb-head {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }}
.eeb-head .title {{ font-weight: 600; }}
.eeb-head .hint {{ font-size: 0.75rem; color: #6b7280; }}
.eeb-bar {{ display: flex; gap: 3px; height: 24px; margin-bottom: 14px; }}
.eeb-bar div {{ border-radius: 4px; }}
.eeb-tile {{ margin-bottom: 12px; }}
.eeb-tile .name {{ font-weight: 600; }}
.eeb-tile .line {{ font-size: 0.8rem; color: #6b7280; line-height: 1.35; }}
.eeb-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }}
.eeb-card {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 14px 16px; margin: 1.5rem 0; }}
.eeb-card .title {{ font-weight: 600; margin-bottom: 8px; }}
.eeb-card .row {{ font-size: 0.9rem; margin: 4px 0; }}
.eeb-card .note {{ font-size: 0.8rem; color: #6b7280; margin-top: 8px; }}
</style>
"""


@st.cache_data
def get_results() -> dict[str, ModuleResult]:
    df = load_ratings()
    return {
        "verdict": verdict(df),
        "buckets": buckets(df),
        "round2": round2_flag(df),
        "stand_in": stand_in(df),
        "subjective": subjective_items(df),
    }


def dot(bucket: str) -> str:
    return f'<span class="eeb-dot" style="background:{BUCKET_COLORS[bucket]}"></span>'


def verdict_card(result: ModuleResult) -> None:
    cost = f"<span>{result.details['cost']}</span>" if result.details.get("cost") else ""
    st.markdown(f"""
<div class="eeb-verdict">
  <div class="top"><span class="action">{result.details.get('action', result.reading)}</span>{cost}</div>
  <div class="reason">{result.reading}</div>
</div>""", unsafe_allow_html=True)


def where_labels_stand(result: ModuleResult, flag: ModuleResult) -> None:
    counts, total = result.details["counts"], sum(result.details["counts"].values())
    segments = "".join(
        f'<div style="flex:{counts[b]};background:{BUCKET_COLORS[b]}"></div>' for b in BUCKETS if counts[b])
    st.markdown(f"""
<div class="eeb-head"><span class="title">Where the current {total} labels stand</span>
  <span class="hint">60 passages × 3 criteria</span></div>
<div class="eeb-bar">{segments}</div>""", unsafe_allow_html=True)

    for col, bucket in zip(st.columns(3), BUCKETS):
        first, second = BUCKET_LINES[bucket]
        col.markdown(f"""
<div class="eeb-tile"><div class="name">{dot(bucket)}{bucket} · {counts[bucket]}</div>
  <div class="line">{first}</div><div class="line">{second}</div></div>""", unsafe_allow_html=True)

    if flag.details.get("flagged"):
        st.info(flag.reading)


def stand_in_card(result: ModuleResult) -> None:
    rows = "".join(f'<div class="row">{dot(line["bucket"])}{line["text"]}</div>'
                   for line in result.details.get("lines", []))
    note = f'<div class="note">{result.details["note"]}</div>' if result.details.get("note") else ""
    st.markdown(f"""
<div class="eeb-card"><div class="title">Can the AI stand in for experts?</div>{rows or result.reading}{note}</div>
""", unsafe_allow_html=True)


def spread(labels: str) -> str:
    """'very_complex, very_complex, moderately_complex' -> 'very complex × 2, moderately complex × 1'"""
    if not labels:
        return ""
    counts = Counter(labels.split(", "))
    return ", ".join(f"{label.replace('_', ' ')} × {n}" for label, n in counts.most_common())


def item_table(results: dict[str, ModuleResult]) -> None:
    choice = st.segmented_control("Show labels", BUCKETS, default="Re-rate", key="decision_bucket")
    if choice == "No expert consensus":
        items = results["subjective"].details["items"].copy()
        items["judge"] = items["judge"].str.replace("_", " ")
        columns = {"item_id": "Passage", "criterion": "Criterion", "round1": "Round 1 experts",
                   "round2": "Round 2 experts", "judge": "AI judge"}
    else:
        items = results["buckets"].details["items"]
        items = items[items["bucket"] == choice].copy() if choice else items.copy()
        items["label"] = items["label"].str.replace("_", " ")
        columns = {"item_id": "Passage", "criterion": "Criterion", "label": "Label",
                   "round1": "Round 1 experts", "round2": "Round 2 experts"}
        if choice == "Re-rate":
            del columns["label"], columns["round2"]
    items["criterion"] = items["criterion"].str.replace("_", " ")
    items["round1"] = items["round1"].map(spread)
    items["round2"] = items["round2"].map(spread)
    st.dataframe(items[list(columns)].rename(columns=columns), hide_index=True, width="stretch")


def render() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    results = get_results()
    st.caption("Ratings are simulated, with planted patterns.")
    st.markdown("""
<div class="eeb-principle">AI is no better than the humans it is checked against.<br>
<span class="sub">First confirm whether experts truly disagree or need more ratings.</span></div>
""", unsafe_allow_html=True)

    verdict_card(results["verdict"])
    where_labels_stand(results["buckets"], results["round2"])
    stand_in_card(results["stand_in"])
    item_table(results)
