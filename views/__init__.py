import re

import streamlit as st

from result import ModuleResult

RED = "#c0504d"


def render_card(result: ModuleResult) -> None:
    with st.container(border=True):
        if result.status != "na":
            st.caption(result.status.upper())
        st.write(result.reading)


def page_header(title: str, tagline: str, css: str = "") -> None:
    """Page title and gray tagline. Call it first in render() so titles line up across tabs.
    The page's CSS rides along in the same element so it adds no extra gap."""
    st.markdown(f"""{css}
<div style="font-size:1.6rem; font-weight:700; letter-spacing:-0.02em; line-height:1.25; margin:0.25rem 0 0.35rem">
  {title}</div>
<div style="font-size:1rem; color:#6b7280; line-height:1.45; margin-bottom:0.5rem">{tagline}</div>""",
                unsafe_allow_html=True)


def render_note(result: ModuleResult) -> None:
    """Red callout bar, styled like the Rubric banner, for stub and draft notes."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", result.reading)
    lines = "".join(f"<div>{line}</div>" for line in text.split("\n\n"))
    st.markdown(f"""
<div style="background:{RED}1f; border-left:3px solid {RED}; border-radius:6px; padding:10px 14px;
  font-size:0.9rem; display:flex; flex-direction:column; gap:4px">{lines}</div>""",
                unsafe_allow_html=True)
