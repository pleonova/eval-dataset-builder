import streamlit as st

from views import analyst, cost, decision, precheck

st.set_page_config(page_title="Expert Eval Builder", layout="wide")
st.title("Expert Eval Builder")

tab_decision, tab_precheck, tab_analyst, tab_cost = st.tabs(
    ["Decision", "Pre-check", "Analyst", "Cost"]
)

with tab_decision:
    decision.render()
with tab_precheck:
    precheck.render()
with tab_analyst:
    analyst.render()
with tab_cost:
    cost.render()
