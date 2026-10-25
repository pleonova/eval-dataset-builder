import streamlit as st

from views import cost, details, overview, rubric

st.set_page_config(page_title="Expert Eval Builder", layout="centered")
st.markdown("""
<style>
[data-testid="stMainBlockContainer"] { padding-top: 3.5rem; }
.eeb-brand { display: flex; align-items: center; gap: 10px; margin-bottom: 0.75rem; }
.eeb-brand .mark { width: 30px; height: 30px; border-radius: 8px; background: #2563eb;
  display: flex; align-items: center; justify-content: center; }
.eeb-brand .name { font-size: 1.45rem; font-weight: 700; letter-spacing: -0.02em; }
</style>
<div class="eeb-brand">
  <div class="mark"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white"
    stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 13l5 5L20 7"/></svg></div>
  <div class="name">Expert Eval Builder</div>
</div>""", unsafe_allow_html=True)

tab_overview, tab_rubric, tab_details, tab_cost = st.tabs(
    ["Overview", "Rubric", "Details", "Cost"]
)

with tab_overview:
    overview.render()
with tab_rubric:
    rubric.render()
with tab_details:
    details.render()
with tab_cost:
    cost.render()
