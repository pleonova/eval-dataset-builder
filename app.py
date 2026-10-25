import streamlit as st

from views import cost, details, overview, rubric, statistics

st.set_page_config(page_title="Expert Eval Builder", layout="centered")
st.markdown("""
<style>
[data-testid="stMainBlockContainer"] { padding-top: 3.5rem; }
.eeb-brand { display: flex; align-items: center; gap: 8px; margin-bottom: 0.75rem; }
.eeb-brand .mark { width: 22px; height: 22px; border-radius: 6px; background: #2563eb;
  display: flex; align-items: center; justify-content: center; }
.eeb-brand .name { font-size: 1rem; font-weight: 600; letter-spacing: -0.01em; }
</style>
<div class="eeb-brand">
  <div class="mark"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white"
    stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 13l5 5L20 7"/></svg></div>
  <div class="name">Expert Eval Builder</div>
</div>""", unsafe_allow_html=True)

tab_overview, tab_rubric, tab_statistics, tab_details, tab_cost = st.tabs(
    ["Overview", "Rubric", "Statistics", "Details", "Cost"]
)

with tab_overview:
    overview.render()
with tab_rubric:
    rubric.render()
with tab_statistics:
    statistics.render()
with tab_details:
    details.render()
with tab_cost:
    cost.render()
