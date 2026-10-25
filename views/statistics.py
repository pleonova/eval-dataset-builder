import math

import altair as alt
import streamlit as st

from config import ALPHA_FAIR, ALPHA_GOOD, CRITERIA, LEVELS
from engine.statistics import alpha_by_criterion, level_confusion, rater_kappas
from engine.load import load_ratings
from result import ModuleResult
from views import render_card
from views.overview import BLUE

SHORT = {level: level.split("_")[0] for level in LEVELS}
CONFUSION_KEY = "statistics_criterion"

CSS = f"""
<style>
.eeb-kicker {{ font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
  color: {BLUE}; margin-bottom: 4px; }}
.eeb-card {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 14px 16px; margin: 1rem 0; }}
.eeb-card .title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 8px; }}
.eeb-card .sub {{ font-size: 0.8rem; color: #6b7280; margin: -4px 0 12px; }}
.eeb-card .note {{ font-size: 0.8rem; color: #6b7280; margin-top: 8px; }}
.eeb-strip {{ display: grid; grid-template-columns: 150px 1fr 64px 64px 64px; align-items: center; gap: 10px;
  font-size: 0.85rem; margin: 6px 0; }}
.eeb-strip.kappa {{ grid-template-columns: 150px 1fr 64px; }}
.eeb-strip.head {{ font-size: 0.75rem; color: #6b7280; margin-bottom: 2px; }}
.eeb-strip .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.eeb-strip .track {{ position: relative; height: 14px; }}
.eeb-strip .axis {{ position: relative; height: 14px; font-size: 0.7rem; color: #6b7280; }}
.eeb-strip .axis span {{ position: absolute; transform: translateX(-50%); }}
.eeb-strip .ref {{ position: absolute; top: -3px; bottom: -3px; border-left: 1px dashed #9ca3af; }}
.eeb-strip .band {{ position: absolute; top: 0; height: 14px; border-radius: 3px; background: #e5e7eb; }}
.eeb-strip .span {{ position: absolute; top: 5px; height: 4px; border-radius: 2px; background: #9ca3af; }}
.eeb-strip .point {{ position: absolute; top: 2px; width: 10px; height: 10px; margin-left: -5px;
  border-radius: 50%; background: #6b7280; }}
.eeb-strip.focus .name, .eeb-strip.focus .num.main {{ font-weight: 600; }}
.eeb-strip.focus .span, .eeb-strip.focus .point {{ background: {BLUE}; }}
.eeb-simulated {{ font-size: 0.8rem; color: #6b7280; font-style: italic; margin-top: 1.5rem; }}
</style>
"""


def get_result() -> ModuleResult:
    return ModuleResult(
        name="statistics",
        value=None,
        status="na",
        reading="Coming next: alpha by criterion with grouped ranges, confusion between levels, per-rater kappa.",
    )


@st.cache_data
def get_results() -> dict[str, ModuleResult]:
    df = load_ratings()
    return {"alpha": alpha_by_criterion(df), "confusion": level_confusion(df), "kappas": rater_kappas(df)}


def name(value: str) -> str:
    return value.replace("_", " ").capitalize()


def scale(lo: float, hi: float):
    return lambda v: (min(max(v, lo), hi) - lo) / (hi - lo) * 100


def axis_row(pos, ticks: list[float], extra_cols: int, fmt: str = "{:.1f}") -> str:
    labels = "".join(f'<span style="left:{pos(t):.1f}%">{fmt.format(t)}</span>' for t in ticks)
    return f'<div class="eeb-strip{" kappa" if extra_cols == 1 else ""}"><span></span><div class="axis">{labels}</div>' \
           + "<span></span>" * extra_cols + "</div>"


def alpha_card(result: ModuleResult) -> None:
    rows = result.details.get("rows", [])
    if not rows:
        return
    pos = scale(0.4, 1.0)
    refs = "".join(f'<div class="ref" style="left:{pos(v):.1f}%"></div>' for v in (ALPHA_FAIR, ALPHA_GOOD))
    lines = ["""
<div class="eeb-strip head"><span>Criterion</span><span>Alpha, with 95% range by passage</span>
  <span class="num">Alpha</span><span class="num">Split first try</span><span class="num">Trusted</span></div>"""]
    for r in rows:
        focus = " focus" if r["criterion"] == result.details["weakest"] else ""
        lines.append(f"""
<div class="eeb-strip{focus}"><span class="name">{name(r['criterion'])}</span>
  <div class="track">{refs}<div class="span" style="left:{pos(r['low']):.1f}%;width:{pos(r['high']) - pos(r['low']):.1f}%"></div>
    <div class="point" style="left:{pos(r['alpha']):.1f}%"></div></div>
  <span class="num main">{r['alpha']:.2f}</span><span class="num">{r['round2_share']:.0%}</span>
  <span class="num">{r['trusted_share']:.0%}</span></div>""")
    lines.append(axis_row(pos, [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], 3))
    st.markdown(f"""
<div class="eeb-card"><div class="eeb-kicker">Alpha by criterion</div>
<div class="title">{result.details['headline']}</div>
<div class="sub">First-try agreement among round-1 experts. Dashed lines mark {ALPHA_FAIR} and {ALPHA_GOOD}.
Ranges come from resampling whole passages.</div>
{''.join(lines)}
<div class="note">{result.reading}</div></div>""", unsafe_allow_html=True)


def confusion_chart(result: ModuleResult, criterion: str) -> alt.Chart:
    data = result.details["matrix"]
    data = data[data["criterion"] == criterion].copy()
    data["row"] = data["row"].map(SHORT)
    data["col"] = data["col"].map(SHORT)
    data["same"] = data["row"] == data["col"]
    order = [SHORT[level] for level in LEVELS]
    off_max = max(1, int(data.loc[~data["same"], "pairs"].max()))
    base = alt.Chart(data).encode(
        x=alt.X("col:N", sort=order, title="Other expert", axis=alt.Axis(labelAngle=0, orient="top")),
        y=alt.Y("row:N", sort=order, title="One expert"),
    )
    cells = base.mark_rect(cornerRadius=3, stroke="white", strokeWidth=2).encode(
        color=alt.condition("datum.same", alt.value("#f3f4f6"),
                            alt.Color("pairs:Q", scale=alt.Scale(domain=[0, off_max], range=["#eff6ff", BLUE]),
                                      legend=None)),
        tooltip=[alt.Tooltip("row:N", title="One expert"), alt.Tooltip("col:N", title="Other expert"),
                 alt.Tooltip("pairs:Q", title="Expert pairs")],
    )
    text = base.mark_text(fontSize=13).encode(
        text="pairs:Q",
        color=alt.condition(f"!datum.same && datum.pairs > {off_max / 2}", alt.value("white"), alt.value("#374151")),
    )
    return (cells + text).properties(height=240).configure_view(stroke=None)


def confusion_card(result: ModuleResult) -> None:
    if "matrix" not in result.details:
        return
    with st.container(border=True, key="statistics_confusion"):
        st.markdown(f"""
<div class="eeb-kicker">Confusion between levels</div>
<div class="title" style="font-size:1.1rem;font-weight:600">{result.details['headline']}</div>
<div class="sub" style="font-size:0.8rem;color:#6b7280;margin:4px 0 8px">Every pair of round-1 experts on the
same passage. The gray diagonal is agreement; blue cells are the levels they mix up.</div>""",
                    unsafe_allow_html=True)
        st.session_state.setdefault(CONFUSION_KEY, name(result.details["worst"]))
        choice = st.segmented_control("Criterion", [name(c) for c in CRITERIA], key=CONFUSION_KEY,
                                      label_visibility="collapsed") or name(result.details["worst"])
        criterion = choice.lower().replace(" ", "_")
        st.altair_chart(confusion_chart(result, criterion), width="stretch")
        st.markdown(f'<div style="font-size:0.8rem;color:#6b7280">{result.reading}</div>', unsafe_allow_html=True)


def kappa_card(result: ModuleResult) -> None:
    rows = result.details.get("rows", [])
    if not rows:
        return
    low, high = result.details["expert_range"]
    lo = math.floor((min(r["kappa"] for r in rows) - 0.03) * 20) / 20
    hi = min(1.0, math.ceil((max(r["kappa"] for r in rows) + 0.03) * 20) / 20)
    pos = scale(lo, hi)
    band = f'<div class="band" style="left:{pos(low):.1f}%;width:{max(0.6, pos(high) - pos(low)):.1f}%"></div>'
    ceiling = f'<div class="ref" style="left:{pos(result.details["ceiling"]):.1f}%"></div>'
    lines = ['<div class="eeb-strip kappa head"><span>Rater</span><span>Kappa on Trusted labels</span>'
             '<span class="num">Kappa</span></div>']
    for r in rows:
        focus = " focus" if r["kind"] == "AI judge" else ""
        lines.append(f"""
<div class="eeb-strip kappa{focus}"><span class="name">{r['rater'] if focus else name(r['rater'])}</span>
  <div class="track">{band}{ceiling}<div class="point" style="left:{pos(r['kappa']):.1f}%"></div></div>
  <span class="num main">{r['kappa']:.2f}</span></div>""")
    ticks = [round(lo + i * 0.05, 2) for i in range(int(round((hi - lo) / 0.05)) + 1)]
    lines.append(axis_row(pos, ticks, 1, "{:.2f}"))
    st.markdown(f"""
<div class="eeb-card"><div class="eeb-kicker">Per-rater kappa</div>
<div class="title">{result.details['headline']}</div>
<div class="sub">Each expert against the majority of the other three; the AI judge against expert consensus.
Gray band is the expert range; the dashed line is the AI ceiling ({result.details['ceiling']:.2f}).</div>
{''.join(lines)}
<div class="note">{result.reading}</div></div>""", unsafe_allow_html=True)


def render() -> None:
    render_card(get_result())
    st.markdown(CSS, unsafe_allow_html=True)
    results = get_results()
    alpha_card(results["alpha"])
    confusion_card(results["confusion"])
    kappa_card(results["kappas"])
    st.markdown('<div class="eeb-simulated">Ratings are simulated, with planted patterns.</div>',
                unsafe_allow_html=True)
