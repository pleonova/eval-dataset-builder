import pandas as pd
import streamlit as st

from config import BUCKETS
from result import ModuleResult
from views import RED, page_header, render_note
from views.overview import BLUE, BUCKET_COLORS, dot

FILTER_KEY = "details_bucket"
FILTERS = ["All", *BUCKETS]

# Placeholder content: example values from the Analyst view wireframe in the build plan.
HELP = {
    "agreement": ("Krippendorff's alpha: how much experts agree beyond chance. 1 is perfect, 0 is chance. "
                  "0.8 or higher is solid; 0.67 to 0.8 is fair; below 0.67 is weak. With this much data, "
                  "the true value could be anywhere from 0.58 to 0.82."),
    "ceiling": ("The average share of experts who gave each item's most common answer. No AI can agree with "
                "the experts more often than they agree with each other."),
    "trusted": ("Exact matches with the expert answer on items experts agree on. Cohen's kappa, which "
                "discounts lucky guesses, is in the details."),
    "no_consensus": ("On items with no expert consensus, the average share of experts who gave the AI's answer. "
                     "A 3-of-5 answer counts 60%, a 1-of-5 answer 20%. Compare it to the experts' own score on "
                     "the same measure; \"at least one expert gave it\" alone is too easy to pass."),
    "top": "The share of experts who gave the most common answer for this item.",
    "recheck": ("What happened when 2 new experts rated this item: split again, sided with one answer, "
                "or not yet asked."),
}
BADGES = {"good": "✓ Good", "fair": "~ Fair", "weak": "✗ Weak"}
METRICS = [
    {"label": "Expert agreement", "help": "agreement", "value": "0.71", "status": "fair",
     "lines": ("Usable, but not", "yet solid (0.8+)")},
    {"label": "AI ceiling", "help": "ceiling", "value": "85%", "status": "good",
     "lines": ("Best any AI can", "score on this set")},
    {"label": "AI on Trusted", "help": "trusted", "value": "70 of 76", "status": "good",
     "lines": ("AI matches experts", "where they agree")},
    {"label": "AI, no consensus", "help": "no_consensus", "value": "58%", "status": "good",
     "lines": ("Experts' own: 61%", "Random: 30%")},
]
NEXT_STEPS = [
    ("Vocabulary: splits cluster on Moderately vs Very", "Rewrite rule"),
    ("AI misses 6 items that experts agree on", "Review prompt"),
    ("8 Re-rate items: confirm with 2 new experts each", "Add experts"),
]
COUNTS = {"All": 100, "Trusted": 76, "Re-rate": 8, "No expert consensus": 16}
ITEMS = pd.DataFrame([
    {"item": "p_047", "top": "40%", "recheck": "Not yet", "bucket": "Re-rate", "ai": "40%", "miss": False},
    {"item": "p_031", "top": "60%", "recheck": "Split again", "bucket": "No expert consensus", "ai": "60%", "miss": False},
    {"item": "p_052", "top": "80%", "recheck": "", "bucket": "Trusted", "ai": "20% miss", "miss": True},
    {"item": "p_014", "top": "100%", "recheck": "", "bucket": "Trusted", "ai": "100%", "miss": False},
    {"item": "p_009", "top": "50%", "recheck": "Not yet", "bucket": "Re-rate", "ai": "50%", "miss": False},
    {"item": "p_023", "top": "50%", "recheck": "Split again", "bucket": "No expert consensus", "ai": "50%", "miss": False},
    {"item": "p_038", "top": "75%", "recheck": "", "bucket": "Trusted", "ai": "100%", "miss": False},
    {"item": "p_056", "top": "50%", "recheck": "Sided with one", "bucket": "Trusted", "ai": "100%", "miss": False},
])


def filter_css() -> str:
    """Color each bucket filter button with its bucket color, with a matching dot. "All" stays plain."""
    rules = []
    for i, bucket in enumerate(BUCKETS, start=2):
        color = BUCKET_COLORS[bucket]
        button = f".st-key-{FILTER_KEY} button:nth-of-type({i})"
        rules.append(f"""
{button} p::before {{ content: ""; display: inline-block; width: 9px; height: 9px; border-radius: 50%;
  background: {color}; margin-right: 7px; vertical-align: 1px; }}
{button}[aria-checked="true"] {{ background: {color}26; border-color: {color}; color: inherit; }}""")
    return "".join(rules)


CSS = f"""
<style>
.eeb-kicker {{ font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
  color: {BLUE}; margin-bottom: 4px; }}
.eeb-metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 0.5rem; }}
.eeb-metric {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 12px 14px; }}
.eeb-metric .label {{ font-size: 0.8rem; color: #6b7280; display: flex; justify-content: space-between;
  align-items: center; gap: 6px; }}
.eeb-metric .value {{ font-size: 1.35rem; font-weight: 600; margin: 4px 0 6px; }}
.eeb-metric .line {{ font-size: 0.75rem; color: #6b7280; line-height: 1.35; }}
.eeb-metric .lines {{ margin-top: 8px; }}
.eeb-badge {{ display: inline-block; font-size: 0.75rem; font-weight: 600; padding: 1px 10px; border-radius: 10px;
  border: 1px solid #111827; }}
.eeb-badge.good {{ background: #11182714; }}
.eeb-badge.fair {{ border-style: dashed; }}
.eeb-key {{ font-size: 0.75rem; color: #6b7280; margin-top: 8px; }}
.eeb-help {{ position: relative; display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; border-radius: 50%; border: 1px solid #9ca3af; color: #6b7280;
  font-size: 0.68rem; font-weight: 600; cursor: pointer; flex: none; outline: none; text-transform: none;
  letter-spacing: 0; vertical-align: 1px; margin-left: 4px; }}
.eeb-help .tip {{ display: none; position: absolute; top: 24px; left: 50%; transform: translateX(-50%);
  width: 260px; z-index: 20; background: #f9fafb; border: 1px solid #d1d5db; border-radius: 8px;
  padding: 10px 12px; font-size: 0.8rem; font-weight: 400; line-height: 1.4; color: #111827; text-align: left;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); cursor: default; white-space: normal; }}
.eeb-help .tip b {{ display: block; margin-bottom: 4px; }}
.eeb-help:hover, .eeb-help:focus {{ border-color: {BLUE}; color: {BLUE}; background: {BLUE}14; }}
.eeb-help:hover .tip, .eeb-help:focus .tip, .eeb-help:focus-within .tip {{ display: block; }}
.eeb-metric:last-child .eeb-help .tip {{ left: auto; right: -8px; transform: none; }}
/* Dashed gray: these cards show what the page could hold, not finished results */
.eeb-next {{ border: 1px dashed #9ca3af; border-radius: 8px; padding: 14px 16px; margin: 1rem 0; }}
.eeb-next .title, .eeb-card .title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 8px; }}
.eeb-next .step {{ display: flex; justify-content: space-between; gap: 12px; font-size: 0.9rem; margin: 6px 0; }}
.eeb-next .act {{ color: {BLUE}; font-weight: 600; white-space: nowrap; }}
.eeb-card {{ border: 1px dashed #9ca3af; border-radius: 8px; padding: 14px 16px; margin: 1rem 0; }}
.eeb-card .row {{ font-size: 0.9rem; margin: 4px 0; }}
.eeb-card .note {{ font-size: 0.8rem; color: #6b7280; font-style: italic; margin-top: 8px; }}
.eeb-items {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 0.5rem; }}
.eeb-items th {{ text-align: left; font-weight: 600; padding: 8px 10px; border-bottom: 1px solid #d1d5db;
  white-space: nowrap; }}
.eeb-items td {{ padding: 8px 10px; border-bottom: 1px solid #f3f4f6; }}
.eeb-items .quiet {{ color: #6b7280; }}
.eeb-items .miss {{ color: {RED}; font-weight: 600; }}
.eeb-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }}
.st-key-details_items {{ border: 1px dashed #9ca3af; border-radius: 8px; padding: 14px 16px; }}
.eeb-simulated {{ font-size: 0.8rem; color: #6b7280; font-style: italic; margin-top: 1.5rem; }}
{filter_css()}
</style>
"""


def get_result() -> ModuleResult:
    return ModuleResult(
        name="details",
        value=None,
        status="na",
        reading=("**Placeholder:** Sample data used to demonstrate how this page will look with real results.\n\n"
                 "**Coming next:** The real numbers from the engine, with steps linked to their items."),
    )


def help_icon(label: str, key: str) -> str:
    """A "?" that shows its help text on hover, and stays open after a click until you click elsewhere."""
    return f'<span class="eeb-help" tabindex="0">?<span class="tip"><b>{label}</b>{HELP[key]}</span></span>'


def metric_tiles() -> None:
    tiles = "".join(f"""
<div class="eeb-metric"><div class="label"><span>{m['label']}</span>{help_icon(m['label'], m['help'])}</div>
  <div class="value">{m['value']}</div><span class="eeb-badge {m['status']}">{BADGES[m['status']]}</span>
  <div class="lines"><div class="line">{m['lines'][0]}</div><div class="line">{m['lines'][1]}</div></div></div>"""
                    for m in METRICS)
    st.markdown(f"""
<div class="eeb-card"><div class="eeb-kicker">How do the numbers look?</div>
<div class="title">Experts agree fairly, and the AI matches them where they agree</div>
<div class="eeb-metrics">{tiles}</div>
<div class="eeb-key">✓ Good · ~ Fair · ✗ Weak · Click a ? to see what a number means</div></div>""",
                unsafe_allow_html=True)


def next_steps() -> None:
    steps = "".join(f'<div class="step"><span>{i}. {text}</span><span class="act">{action} ›</span></div>'
                    for i, (text, action) in enumerate(NEXT_STEPS, start=1))
    st.markdown(f"""
<div class="eeb-next"><div class="eeb-kicker">What to go after next</div>
<div class="title">Three fixes, most useful first</div>{steps}</div>""", unsafe_allow_html=True)


def stand_in_panel() -> None:
    st.markdown(f"""
<div class="eeb-card"><div class="eeb-kicker">Can AI stand in?</div>
<div class="title">On the {COUNTS['No expert consensus']} No expert consensus items</div>
<div class="row">✓ <b>Swap test:</b> AI in an expert's seat keeps agreement at 0.71 (range 0.66 to 0.74)</div>
<div class="row">✓ <b>Self-consistency:</b> same answer in all 3 runs on 94 of 100 items</div>
<div class="note">Passing means the AI is as reliable as one expert, not the panel.</div></div>""", unsafe_allow_html=True)


def item_table() -> None:
    st.markdown(f"""
<div class="eeb-kicker">Which items need a closer look?</div>
<div class="title" style="font-size:1.1rem;font-weight:600;margin-bottom:8px">{COUNTS['Re-rate']} Re-rate and
{COUNTS['No expert consensus']} No expert consensus items to check</div>""", unsafe_allow_html=True)
    st.session_state.setdefault(FILTER_KEY, "All")
    choice = st.segmented_control("Bucket", FILTERS, key=FILTER_KEY, label_visibility="collapsed",
                                  format_func=lambda f: f"{f} {COUNTS[f]}") or "All"
    items = ITEMS if choice == "All" else ITEMS[ITEMS["bucket"] == choice]

    rows = "".join(f"""
<tr><td>{r.item}</td><td>{r.top}</td><td class="{'' if r.recheck else 'quiet'}">{r.recheck or 'n/a'}</td>
  <td>{dot(r.bucket)}{r.bucket}</td><td class="{'miss' if r.miss else 'quiet'}">{r.ai}</td></tr>"""
                   for r in items.itertuples())
    st.markdown(f"""
<table class="eeb-items"><thead><tr><th>Item</th><th>Top answer{help_icon('Top answer', 'top')}</th>
  <th>Recheck{help_icon('Recheck', 'recheck')}</th><th>Bucket</th><th>AI match</th></tr></thead>
<tbody>{rows}</tbody></table>""", unsafe_allow_html=True)

    export = items.drop(columns="miss").rename(columns={"item": "item_id", "top": "top_answer", "ai": "ai_match"})
    st.download_button("Export CSV", export.to_csv(index=False), file_name="details_items.csv", mime="text/csv")


def render() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    page_header("Which items need attention?",
                "Item by item: the headline numbers, fixes in order, and every item "
                "with its bucket and how the AI did.")
    render_note(get_result())
    metric_tiles()
    next_steps()
    stand_in_panel()
    with st.container(border=True, key="details_items"):
        item_table()
    st.markdown('<div class="eeb-simulated">Example values, shown as a placeholder for this page.</div>',
                unsafe_allow_html=True)
