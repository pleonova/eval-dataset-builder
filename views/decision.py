from collections import Counter

import altair as alt
import pandas as pd
import streamlit as st

from config import BUCKETS
from engine.ai_checks import stand_in, subjective_items
from engine.buckets import buckets, round2_flag, trusted_range, verdict
from engine.load import load_ratings
from result import ModuleResult

BLUE = "#2563eb"
BUCKET_COLORS = {"Trusted": "#4caf50", "Re-rate": "#f59e0b", "No expert consensus": "#ec7fa9"}
BUCKET_LINES = {
    "Trusted": ("Experts agree", "Use to test the AI"),
    "Re-rate": ("Experts split, not yet", "confirmed: add 2 experts"),
    "No expert consensus": ("Split held with new experts", "Likely subjective in practice"),
}
FILTER_KEY = "decision_bucket"


def filter_css() -> str:
    """Color each Show labels button with its bucket color, with a matching dot."""
    rules = []
    for i, bucket in enumerate(BUCKETS, start=1):
        color = BUCKET_COLORS[bucket]
        button = f".st-key-{FILTER_KEY} button:nth-of-type({i})"
        rules.append(f"""
{button} p::before {{ content: ""; display: inline-block; width: 9px; height: 9px; border-radius: 50%;
  background: {color}; margin-right: 7px; vertical-align: 1px; }}
{button}[aria-checked="true"] {{ background: {color}26; border-color: {color}; color: inherit; }}""")
    return "".join(rules)


CSS = f"""
<style>
.eeb-principle {{ background: {BLUE}0f; border: 1px solid {BLUE}66; border-radius: 8px;
  padding: 10px 14px; font-size: 0.9rem; margin-bottom: 1rem; }}
.eeb-principle .sub {{ color: #6b7280; }}
.eeb-verdict {{ border: 2px solid {BLUE}; border-radius: 8px; padding: 14px 16px; margin-bottom: 1.5rem; }}
.eeb-verdict .top {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; }}
.eeb-verdict .action {{ font-size: 1.2rem; font-weight: 600; }}
.eeb-verdict .reason {{ margin-top: 6px; }}
.eeb-head {{ display: flex; justify-content: space-between; align-items: baseline; }}
.eeb-head .title {{ font-weight: 600; }}
.eeb-head .hint {{ font-size: 0.75rem; color: #6b7280; }}
.eeb-tile {{ margin-bottom: 4px; }}
.eeb-tile .name {{ font-weight: 600; }}
.eeb-tile .line {{ font-size: 0.8rem; color: #6b7280; line-height: 1.35; }}
.eeb-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }}
.eeb-card {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 14px 16px; margin: 1rem 0; }}
.eeb-card .title {{ font-weight: 600; margin-bottom: 8px; }}
.eeb-card .sub {{ font-size: 0.8rem; color: #6b7280; margin: -4px 0 12px; }}
.eeb-card .row {{ font-size: 0.9rem; margin: 4px 0; }}
.eeb-card .note {{ font-size: 0.8rem; color: #6b7280; margin-top: 8px; }}
.eeb-range {{ display: grid; grid-template-columns: 110px 1fr 70px; align-items: center; gap: 12px;
  font-size: 0.85rem; margin: 6px 0; }}
.eeb-range .track {{ position: relative; height: 12px; }}
.eeb-range .span {{ position: absolute; top: 0; height: 12px; border-radius: 6px; background: {BLUE}; }}
.eeb-range .point {{ position: absolute; top: 1px; width: 10px; height: 10px; margin-left: -5px;
  border-radius: 50%; background: {BLUE}; }}
.eeb-range .pm {{ color: #6b7280; }}
.eeb-range.last .name {{ font-weight: 600; }}
.eeb-range.last .pm {{ color: {BLUE}; font-weight: 600; }}
.st-key-decision_bar [data-testid="stElementToolbar"] {{ display: none; }}
.eeb-simulated {{ font-size: 0.8rem; color: #6b7280; font-style: italic; margin-bottom: 0.5rem; }}
{filter_css()}
</style>
"""


@st.cache_data
def get_results() -> dict[str, ModuleResult]:
    df = load_ratings()
    return {
        "verdict": verdict(df),
        "buckets": buckets(df),
        "round2": round2_flag(df),
        "range": trusted_range(df),
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


def pick_bucket_from_bar() -> None:
    """Clicking a color on the bar selects that bucket in the Show labels filter."""
    points = st.session_state["decision_bar"].selection.get("pick", [])
    if points:
        st.session_state[FILTER_KEY] = points[0]["bucket"]


def bucket_bar(counts: dict) -> alt.Chart:
    data = pd.DataFrame([{"bucket": b, "count": counts[b], "order": i} for i, b in enumerate(BUCKETS)])
    pick = alt.selection_point(name="pick", fields=["bucket"], on="click")
    return alt.Chart(data).mark_bar(cornerRadius=4, height=24, cursor="pointer", stroke="white",
                                    strokeWidth=3).encode(
        x=alt.X("count:Q", stack="zero", axis=None, scale=alt.Scale(domain=[0, sum(counts.values())])),
        color=alt.Color("bucket:N", scale=alt.Scale(domain=BUCKETS, range=list(BUCKET_COLORS.values())),
                        legend=None),
        order="order:Q",
        tooltip=[alt.Tooltip("bucket:N", title="Bucket"), alt.Tooltip("count:Q", title="Labels")],
    ).add_params(pick).properties(height=32).configure_view(stroke=None)


def where_labels_stand(result: ModuleResult) -> None:
    counts, total = result.details["counts"], sum(result.details["counts"].values())
    st.markdown(f"""
<div class="eeb-head"><span class="title">Where the current {total} labels stand</span>
  <span class="hint">Click a color to see those labels</span></div>""", unsafe_allow_html=True)
    st.altair_chart(bucket_bar(counts), width="stretch", on_select=pick_bucket_from_bar,
                    selection_mode="pick", key="decision_bar")

    for col, bucket in zip(st.columns(3), BUCKETS):
        first, second = BUCKET_LINES[bucket]
        col.markdown(f"""
<div class="eeb-tile"><div class="name">{dot(bucket)}{bucket} · {counts[bucket]}</div>
  <div class="line">{first}</div><div class="line">{second}</div></div>""", unsafe_allow_html=True)


def stand_in_card(result: ModuleResult) -> None:
    rows = "".join(f'<div class="row">{dot(line["bucket"])}{line["text"]}</div>'
                   for line in result.details.get("lines", []))
    note = f'<div class="note">{result.details["note"]}</div>' if result.details.get("note") else ""
    st.markdown(f"""
<div class="eeb-card"><div class="title">Can the AI stand in for experts?</div>{rows or result.reading}{note}</div>
""", unsafe_allow_html=True)


def certainty_card(result: ModuleResult) -> None:
    rows = result.details.get("rows", [])
    if not rows:
        return
    lo = min(r["low"] for r in rows) - 0.05
    hi = max(r["high"] for r in rows) + 0.05
    pos = lambda v: (v - lo) / (hi - lo) * 100
    share = result.details["share"]
    lines = []
    for i, r in enumerate(rows):
        opacity = 0.25 + 0.5 * i / max(1, len(rows) - 1)
        last = " last" if i == len(rows) - 1 else ""
        lines.append(f"""
<div class="eeb-range{last}"><span class="name">{r['label']}</span>
  <div class="track"><div class="span" style="left:{pos(r['low']):.1f}%;width:{pos(r['high']) - pos(r['low']):.1f}%;opacity:{opacity:.2f}"></div>
  <div class="point" style="left:{pos(share):.1f}%"></div></div>
  <span class="pm">±{r['margin'] * 100:.0f} pts</span></div>""")
    st.markdown(f"""
<div class="eeb-card"><div class="title">More ratings mean steadier, more trustworthy results</div>
<div class="sub">A wide bar means the share of labels you can trust could still shift between checks.</div>
{''.join(lines)}
<div class="note">{result.reading}</div></div>""", unsafe_allow_html=True)


def spread(labels: str) -> str:
    """'very_complex, very_complex, moderately_complex' -> 'very complex × 2, moderately complex × 1'"""
    if not labels:
        return ""
    counts = Counter(labels.split(", "))
    return ", ".join(f"{label.replace('_', ' ')} × {n}" for label, n in counts.most_common())


def item_table(results: dict[str, ModuleResult]) -> None:
    st.session_state.setdefault(FILTER_KEY, "Re-rate")
    choice = st.segmented_control("Show labels", BUCKETS, key=FILTER_KEY)
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
    st.markdown('<div class="eeb-simulated">Ratings are simulated, with planted patterns.</div>',
                unsafe_allow_html=True)
    st.markdown("""
<div class="eeb-principle">AI is no better than the humans it is checked against.<br>
<span class="sub">First confirm whether experts truly disagree or need more ratings.</span></div>
""", unsafe_allow_html=True)

    verdict_card(results["verdict"])
    where_labels_stand(results["buckets"])
    item_table(results)
    stand_in_card(results["stand_in"])
    certainty_card(results["range"])

    flag = results["round2"]
    if flag.details.get("flagged"):
        st.info(flag.reading)
