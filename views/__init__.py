import streamlit as st

from result import ModuleResult


def render_card(result: ModuleResult) -> None:
    with st.container(border=True):
        st.caption(result.status.upper())
        st.write(result.reading)
