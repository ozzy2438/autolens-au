"""Data Quality & Pipeline Health page.

Shows:
- Row counts and data freshness
- Failed test log
- Refresh history
- Pipeline run status

This page demonstrates operational maturity:
RedBook sells data reliability; showing you think in those terms
is worth more than another model.
"""

import streamlit as st

st.set_page_config(page_title="Data Quality | AutoLens AU", page_icon="\u2705", layout="wide")

st.title("\u2705 Data Quality & Pipeline Health")
st.markdown("Monitoring data freshness, quality gates, and pipeline status.")

# Status overview
st.markdown("### Pipeline Status")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Pipeline Status", "Not run")
with col2:
    st.metric("Last Refresh", "None")
with col3:
    st.metric("Verified Records", "0")
with col4:
    st.metric("Last dbt Build", "Not run")

st.markdown("---")

# Data freshness
st.markdown("### Data Freshness")
st.info("No source has a recorded successful ingestion. Freshness cannot yet be calculated.")

st.markdown("---")

# Test results
st.markdown("### Quality Gate Results")
st.info("No dbt or data-quality result has been recorded against an ingested dataset.")

st.markdown("---")

# Refresh history
st.markdown("### Refresh History (Changelog)")
st.info("No refresh history exists. The first entry will be generated from workflow artifacts.")

st.markdown("---")
st.caption(
    "Quality gates are being established in GitHub Actions. "
    "A refresh will be recorded only after ingestion and all required tests succeed. "
    "See docs/MONITORING.md for the full monitoring framework.",
)
