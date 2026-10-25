from collections import Counter
from functools import partial

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
LABELS_OPEN_KEY = "decision_labels_open"


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
.eeb-verdict {{ border: 2px solid {BLUE}; border-radius: 8px; padding: 14px 16px; margin-bottom: 1.5rem; }}
.eeb-verdict .top {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; }}
.eeb-kicker {{ font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
  color: {BLUE}; margin-bottom: 4px; }}
.eeb-verdict .action {{ font-size: 1.2rem; font-weight: 600; }}
.eeb-verdict .reason {{ margin-top: 6px; }}
.eeb-head {{ display: flex; justify-content: space-between; align-items: baseline; }}
.eeb-head .title {{ font-size: 1.1rem; font-weight: 600; }}
.eeb-head .hint {{ font-size: 0.75rem; color: #6b7280; }}
.eeb-tile {{ margin-bottom: 14px; }}
.eeb-tile .name {{ font-weight: 600; }}
.eeb-tile .line {{ font-size: 0.8rem; color: #6b7280; line-height: 1.35; }}
.eeb-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }}
.eeb-card {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 14px 16px; margin: 1rem 0; }}
.eeb-card .title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 8px; }}
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
[class*="st-key-decision_bar"] [data-testid="stElementToolbar"] {{ display: none; }}
.st-key-decision_mix {{ border-color: #d1d5db; border-radius: 8px; }}
.eeb-crit {{ display: grid; grid-template-columns: 170px 1fr 200px; align-items: center; gap: 12px;
  font-size: 0.85rem; margin: 6px 0; }}
.eeb-crit .track {{ height: 10px; border-radius: 5px; background: #f3f4f6; }}
.eeb-crit .fill {{ height: 10px; border-radius: 5px; background: #9ca3af; }}
.eeb-crit.flagged .name {{ font-weight: 600; }}
.eeb-crit.flagged .fill {{ background: #4b5563; }}
.eeb-crit .count {{ color: #6b7280; white-space: nowrap; }}
.eeb-crit .tag {{ color: {BLUE}; font-weight: 600; }}
.eeb-simulated {{ font-size: 0.8rem; color: #6b7280; font-style: italic; margin-top: 1.5rem; }}
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
  <div class="eeb-kicker">What to do next</div>
  <div class="top"><span class="action">{result.details.get('action', result.reading)}</span>{cost}</div>
  <div class="reason">{result.reading}</div>
</div>""", unsafe_allow_html=True)


def pick_bucket_from_bar(chart_key: str) -> None:
    """Clicking a color opens Show labels on that bucket; clicking it again closes Show labels."""
    points = st.session_state[chart_key].selection.get("pick", [])
    st.session_state["decision_bar_version"] = st.session_state.get("decision_bar_version", 0) + 1
    bucket = points[0]["bucket"] if points else None
    is_open = st.session_state.get(LABELS_OPEN_KEY, False)
    if bucket is None or (is_open and bucket == st.session_state.get(FILTER_KEY)):
        st.session_state[LABELS_OPEN_KEY] = False
    else:
        st.session_state[FILTER_KEY] = bucket
        st.session_state[LABELS_OPEN_KEY] = True


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


def where_labels_stand(results: dict[str, ModuleResult]) -> None:
    counts = results["buckets"].details["counts"]
    total = sum(counts.values())
    with st.container(border=True, key="decision_mix"):
        _labels_card(counts, total, results)


def _labels_card(counts: dict, total: int, results: dict[str, ModuleResult]) -> None:
    st.markdown(f"""
<div class="eeb-kicker">Where labels stand</div>
<div class="eeb-head"><span class="title">{counts['Trusted']} of {total} labels are safe to tune against</span>
  <span class="hint">Click a color to see those labels</span></div>""", unsafe_allow_html=True)
    chart_key = f"decision_bar_{st.session_state.get('decision_bar_version', 0)}"
    st.altair_chart(bucket_bar(counts), width="stretch", on_select=partial(pick_bucket_from_bar, chart_key),
                    selection_mode="pick", key=chart_key)

    for col, bucket in zip(st.columns(3), BUCKETS):
        first, second = BUCKET_LINES[bucket]
        col.markdown(f"""
<div class="eeb-tile"><div class="name">{dot(bucket)}{bucket} · {counts[bucket]}</div>
  <div class="line">{first}</div><div class="line">{second}</div></div>""", unsafe_allow_html=True)

    with st.expander("Show labels", key=LABELS_OPEN_KEY, on_change="rerun"):
        item_table(results)


def rubric_card(result: ModuleResult) -> None:
    rows = []
    for r in result.details.get("rows", []):
        flagged = " flagged" if r["flagged"] else ""
        tag = '<span class="tag"> · rubric unclear</span>' if r["flagged"] else ""
        rows.append(f"""
<div class="eeb-crit{flagged}"><span class="name">{r['criterion'].replace('_', ' ').capitalize()}</span>
  <div class="track"><div class="fill" style="width:{r['share'] * 100:.0f}%"></div></div>
  <span class="count">{r['split']} of {r['items']} split{tag}</span></div>""")
    st.markdown(f"""
<div class="eeb-card"><div class="eeb-kicker">Is the rubric clear?</div>
<div class="title">{result.details.get("headline", "")}</div>
<div class="sub">Passages where experts split on the first try and needed a second round. A high share points
to unclear wording, even when the second round settles the label.</div>
{''.join(rows)}
<div class="note">{result.reading}</div></div>""", unsafe_allow_html=True)


def stand_in_card(result: ModuleResult) -> None:
    rows = "".join(f'<div class="row">{dot(line["bucket"])}<b>{line["label"]}:</b> {line["text"]}</div>'
                   for line in result.details.get("lines", []))
    note = f'<div class="note">{result.details["note"]}</div>' if result.details.get("note") else ""
    st.markdown(f"""
<div class="eeb-card"><div class="eeb-kicker">Can the AI stand in for experts?</div>
<div class="title">{result.details.get("headline", "")}</div>{rows or result.reading}{note}</div>
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
<div class="eeb-card"><div class="eeb-kicker">How sure are we?</div>
<div class="title">More ratings mean steadier, more trustworthy results</div>
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
    choice = st.segmented_control("Bucket", BUCKETS, key=FILTER_KEY, label_visibility="collapsed")
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

    verdict_card(results["verdict"])
    where_labels_stand(results)
    stand_in_card(results["stand_in"])
    rubric_card(results["round2"])
    certainty_card(results["range"])
    st.markdown('<div class="eeb-simulated">Ratings are simulated, with planted patterns.</div>',
                unsafe_allow_html=True)
