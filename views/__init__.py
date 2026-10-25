import re

import streamlit as st

from result import ModuleResult

YELLOW = "#eab308"


def render_card(result: ModuleResult) -> None:
    with st.container(border=True):
        if result.status != "na":
            st.caption(result.status.upper())
        st.write(result.reading)


def render_note(result: ModuleResult) -> None:
    """Yellow callout bar, styled like the Rubric banner, for stub and draft notes."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", result.reading)
    lines = "".join(f"<div>{line}</div>" for line in text.split("\n\n"))
    st.markdown(f"""
<div style="background:{YELLOW}1f; border-left:3px solid {YELLOW}; border-radius:6px; padding:10px 14px;
  font-size:0.9rem; margin-bottom:1.25rem; display:flex; flex-direction:column; gap:4px">{lines}</div>""",
                unsafe_allow_html=True)
