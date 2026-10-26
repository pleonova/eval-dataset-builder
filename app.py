import streamlit as st

from views import cost, details, overview, rubric, statistics

st.set_page_config(page_title="Expert Eval Builder", layout="centered")
st.markdown("""
<style>
[data-testid="stMainBlockContainer"] { padding-top: 3.5rem; }
.eeb-brand { display: flex; align-items: center; gap: 8px; }
.eeb-brand .mark { width: 28px; height: 28px; border-radius: 7px; background: #2563eb;
  display: flex; align-items: center; justify-content: center; }
.eeb-brand .name { font-size: 1.35rem; font-weight: 600; letter-spacing: -0.01em; }
.eeb-demo { font-size: 0.8rem; color: #6b7280; font-style: italic; margin: -0.25rem 0 0.5rem; }
.eeb-demo b { font-style: normal; font-weight: 600; display: block; }
.eeb-demo a { color: inherit; text-decoration: underline; text-underline-offset: 2px; }
.eeb-demo a:hover { color: #2563eb; }
.st-key-eeb_header [data-testid="stMarkdownContainer"] { margin-bottom: 0; }
.st-key-data_sample button, .st-key-data_upload button { min-height: 0; padding: 2px 10px; }
.st-key-data_sample button *, .st-key-data_upload button * { font-size: 0.8rem !important; }
/* Same dashed outline as the "Not added yet" AI card, since uploading isn't built yet */
.st-key-data_upload button { border: 1px dashed #d1d5db; }
</style>""", unsafe_allow_html=True)

# The data source is shared by every tab, so it sits in the header beside the app name
header = st.container(horizontal=True, vertical_alignment="center", key="eeb_header")
header.markdown("""
<div class="eeb-brand">
  <div class="mark"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white"
    stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 13l5 5L20 7"/></svg></div>
  <div class="name">Expert Eval Builder</div>
</div>""", unsafe_allow_html=True, width="content")
# Example data is the only source for now, so it always shows as selected
with header:
    st.space("stretch")
    if st.button("Upload Data", icon=":material/upload:", key="data_upload", help="Feature coming soon"):
        st.toast("Uploading your own data is coming soon.")
    st.button("Demo Data", type="primary", icon=":material/check:", key="data_sample")
LC_REPO = "https://github.com/learning-commons-org/evaluators"
st.markdown(f'<div class="eeb-demo"><b>Synthetic Demo Data</b>Complexity levels and criteria from Learning Commons '
            f'(<a href="{LC_REPO}" target="_blank">evaluators</a>, '
            f'<a href="{LC_REPO}/tree/main/datasets" target="_blank">data</a>)</div>',
            unsafe_allow_html=True)

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
