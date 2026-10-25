import streamlit as st

from config import ALPHA_FAIR, RUBRIC_MAX_FLIP
from rubric.analyze import rubric
from result import ModuleResult
from views import page_header, render_card
from views.overview import BLUE

STEPS = ["AI dry run", "Expert pilot", "Rate at scale"]
MODEL_NAMES = {"openai/gpt-oss-120b": "GPT-OSS 120B (OpenAI)", "qwen/qwen3.8-27b": "Qwen 3.8 27B (Alibaba)"}

CSS = f"""
<style>
.eeb-banner {{ background: {BLUE}14; border-left: 3px solid {BLUE}; border-radius: 6px; padding: 10px 14px;
  font-size: 0.9rem; margin-bottom: 1.25rem; }}
.eeb-steps {{ display: flex; align-items: flex-start; margin: 0.25rem 0 1.5rem; }}
.eeb-step {{ display: flex; flex-direction: column; align-items: center; gap: 6px; width: 110px;
  font-size: 0.8rem; color: #6b7280; }}
.eeb-step .num {{ width: 24px; height: 24px; border-radius: 50%; border: 1.5px solid #d1d5db; background: #f3f4f6;
  display: flex; align-items: center; justify-content: center; font-weight: 600; }}
.eeb-step.active {{ color: inherit; font-weight: 600; }}
.eeb-step.active .num {{ border: 2px solid {BLUE}; background: {BLUE}26; color: {BLUE}; }}
.eeb-steps .link {{ flex: 1; height: 2px; background: #e5e7eb; margin-top: 12px; }}
.eeb-kicker {{ font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
  color: {BLUE}; margin-bottom: 4px; }}
.eeb-answer {{ border: 2px solid {BLUE}; border-radius: 8px; padding: 14px 16px; margin-bottom: 1rem; }}
.eeb-answer .title {{ font-size: 1.2rem; font-weight: 600; }}
.eeb-answer .badge-row {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 8px 0; }}
.eeb-badge {{ border: 1px dashed currentColor; border-radius: 999px; padding: 1px 10px; font-size: 0.75rem;
  font-weight: 600; white-space: nowrap; }}
.eeb-answer .hint {{ font-size: 0.8rem; color: #6b7280; }}
.eeb-card {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 14px 16px; margin: 1rem 0; }}
.eeb-card .note {{ font-size: 0.8rem; color: #6b7280; margin-top: 8px; }}
.eeb-rules {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
.eeb-rules th {{ text-align: left; font-size: 0.8rem; padding: 6px 8px; border-bottom: 1px solid #d1d5db; }}
.eeb-rules td {{ padding: 10px 8px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
.eeb-rules tr:last-child td {{ border-bottom: none; }}
.eeb-rules tr.unclear td:first-child, .eeb-rules tr.unclear .clear {{ font-weight: 600; }}
.eeb-rules tr.clear-row .showed, .eeb-rules tr.clear-row .fix {{ color: #6b7280; }}
.eeb-rules tr.unclear .fix {{ color: {BLUE}; font-weight: 600; }}
.eeb-rules .clear {{ white-space: nowrap; }}
.eeb-help {{ display: inline-flex; align-items: center; justify-content: center; width: 15px; height: 15px;
  margin-left: 4px; border-radius: 50%; border: 1px solid #9ca3af; color: #6b7280; font-size: 0.65rem;
  font-weight: 600; cursor: help; vertical-align: 1px; }}
.eeb-simulated {{ font-size: 0.8rem; color: #6b7280; font-style: italic; margin-top: 1.5rem; }}
</style>
"""


@st.cache_data
def get_result() -> ModuleResult:
    return rubric()


def steps(active: int = 0) -> None:
    parts = []
    for i, step in enumerate(STEPS):
        if i:
            parts.append('<div class="link"></div>')
        state = " active" if i == active else ""
        parts.append(f'<div class="eeb-step{state}"><div class="num">{i + 1}</div>{step}</div>')
    st.markdown(f'<div class="eeb-steps">{"".join(parts)}</div>', unsafe_allow_html=True)


def answer_card(result: ModuleResult) -> None:
    st.markdown(f"""
<div class="eeb-answer"><div class="eeb-kicker">Is the rubric clear enough to send to experts?</div>
  <div class="title">{result.details["headline"]}</div>
  <div class="badge-row"><span class="eeb-badge">Simulated by AI raters</span>
    <span class="hint">Spots potentially confusing rubric instructions. Not proof experts agree.</span></div>
  <div>{result.reading}</div></div>""", unsafe_allow_html=True)


def help_icon(rule: dict) -> str:
    tip = (f"Agreement across AI runs (alpha): {rule['alpha']:.2f}, clear needs {ALPHA_FAIR:.2f} or higher. "
           f"Changed answers on {rule['flipped']} of {rule['items']} passages, "
           f"clear needs {RUBRIC_MAX_FLIP:.0%} or fewer.")
    return f'<span class="eeb-help" title="{tip}">?</span>'


def rules_table(result: ModuleResult) -> None:
    rows = []
    for rule in result.details["rules"]:
        css = "clear-row" if rule["clear"] else "unclear"
        mark = "✓ Yes" if rule["clear"] else "✗ No"
        rows.append(f"""
<tr class="{css}"><td>{rule['criterion'].replace('_', ' ').capitalize()}</td>
  <td class="clear">{mark}{help_icon(rule)}</td><td class="showed">{rule['showed']}</td>
  <td class="fix">{rule['fix']}</td></tr>""")
    st.markdown(f"""
<div class="eeb-card"><div class="eeb-kicker">Rubric rules</div>
<table class="eeb-rules"><thead><tr><th>Rubric rule</th><th>Clear?</th><th>What the AI raters showed</th>
  <th>Fix</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<div class="note">{result.details["savings"]}</div></div>""", unsafe_allow_html=True)


def ai_answers(result: ModuleResult) -> None:
    ratings = result.details["ratings"]
    with st.expander("Show AI answers"):
        criterion = st.segmented_control(
            "Rule", [r["criterion"] for r in result.details["rules"]], key="rubric_rule",
            format_func=lambda c: c.replace("_", " ").capitalize(), label_visibility="collapsed",
        ) or result.details["rules"][0]["criterion"]
        subset = ratings[ratings["criterion"] == criterion]
        table = (subset.assign(rater=subset["model"].map(lambda m: MODEL_NAMES.get(m, m)) + " · run "
                               + subset["run"].astype(str),
                               label=subset["label"].str.replace("_", " "))
                       .pivot_table(index="item_id", columns="rater", values="label", aggfunc="first"))
        st.dataframe(table.rename_axis("Passage").reset_index(), hide_index=True, width="stretch")


def render() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    page_header("Is the rubric clear enough to send to experts?",
                "Before experts rate anything, AI raters from two providers apply the draft rubric. "
                "Where they flip or disagree, the wording is probably unclear.")
    st.markdown('<div class="eeb-banner">Simulated ratings from AI raters, not experts. '
                'Used only to spot potentially confusing rubric instructions.</div>', unsafe_allow_html=True)
    steps(active=0)
    result = get_result()
    if result.status == "na":
        render_card(result)
        return

    answer_card(result)
    rules_table(result)
    ready = result.details["ready"]
    col, note = st.columns([1, 2], vertical_alignment="center")
    if col.button("Start expert pilot", disabled=not ready, key="rubric_pilot"):
        st.toast("Coming next: the expert pilot on the same passages.")
    if not ready:
        note.caption("Unlocks when all rules are clear.")
    ai_answers(result)

    models = " and ".join(MODEL_NAMES.get(m, m) for m in result.details["models"])
    st.markdown(f'<div class="eeb-simulated">{models}, {result.details["runs"]} runs each, '
                f'on {result.details["items"]} sample passages.</div>', unsafe_allow_html=True)
