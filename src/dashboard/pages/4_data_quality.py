"""Measured data freshness, model evidence, and workflow status."""

import pandas as pd
import streamlit as st

from src.dashboard.data_access import (
    DashboardDataError,
    get_source_health,
    load_model_metrics,
    load_refresh_status,
)

st.set_page_config(page_title="Data Quality | AutoLens AU", page_icon="✅", layout="wide")
st.title("✅ Data Quality & Pipeline Health")
st.markdown("Only persisted source counts, timestamps, test results and model metrics appear here.")

try:
    refresh = load_refresh_status()
except DashboardDataError as error:
    refresh = {"status": "unreadable", "completed_at": None, "dbt": {}}
    st.error(str(error))

try:
    health = get_source_health()
except DashboardDataError:
    health = pd.DataFrame()
try:
    metrics = load_model_metrics()
except DashboardDataError:
    metrics = {}

available_rows = (
    int(health.loc[health["status"] == "available", "row_count"].sum()) if not health.empty else 0
)
dbt_status = refresh.get("dbt", {}).get("status", "not_run")
columns = st.columns(4)
columns[0].metric("Refresh status", refresh.get("status", "unknown"))
columns[1].metric("Last refresh", refresh.get("completed_at") or "Not run")
columns[2].metric("Available source rows", f"{available_rows:,}")
columns[3].metric("Last dbt build", dbt_status)

st.markdown("### Source freshness")
if health.empty or not (health["status"] == "available").any():
    st.info("No source table is reachable from the configured database.")
else:
    st.dataframe(health, use_container_width=True, hide_index=True)

st.markdown("### Quality gate evidence")
dbt = refresh.get("dbt", {})
if dbt_status == "not_run":
    st.info("No production refresh dbt result has been recorded.")
else:
    gate_columns = st.columns(3)
    gate_columns[0].metric("dbt status", dbt_status)
    gate_columns[1].metric("Tests passed", dbt.get("tests_passed", "Unknown"))
    gate_columns[2].metric("Tests failed", dbt.get("tests_failed", "Unknown"))

st.markdown("### Model evidence")
if not metrics:
    st.info("No verified model metrics artifact exists.")
else:
    overall = metrics.get("lgbm_metrics", {}).get("overall", {})
    interval = metrics.get("prediction_interval_metrics", {})
    model_columns = st.columns(4)
    model_columns[0].metric("Validation", metrics.get("validation_strategy", "unknown"))
    model_columns[1].metric("MAE", f"${overall.get('mae', 0):,.0f}")
    model_columns[2].metric("MdAPE", f"{overall.get('mdape', 0):.1f}%")
    coverage = interval.get("actual_coverage")
    model_columns[3].metric("80% interval coverage", f"{coverage:.1%}" if coverage else "Unknown")

st.markdown("### Refresh details")
st.json(refresh)
