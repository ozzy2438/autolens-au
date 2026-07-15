"""AutoLens AU Streamlit landing page."""

import streamlit as st

from src.dashboard.data_access import (
    DashboardDataError,
    load_model_metrics,
    load_refresh_status,
)
from src.dashboard.release_artifacts import ReleaseArtifactError, prepare_dashboard_artifacts

st.set_page_config(
    page_title="AutoLens AU — Vehicle Pricing Intelligence",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    refresh = load_refresh_status()
except DashboardDataError:
    refresh = {"status": "status_unreadable", "completed_at": None}
try:
    prepare_dashboard_artifacts()
    metrics = load_model_metrics()
except (DashboardDataError, ReleaseArtifactError):
    metrics = {}

st.title("🚗 AutoLens AU")
st.subheader("Australian Vehicle Pricing & Residual Value Platform")
st.markdown(
    """
AutoLens AU is an **independent public data product under active pre-launch development**.
It combines Australian vehicle listings with official government reference sources and exposes
only data, test results, and model metrics that have actually been recorded.

| Page | Product |
|---|---|
| **Instant Valuation** | Calibrated LightGBM estimate with local TreeSHAP drivers |
| **Depreciation Explorer** | Observed price-retention curves and residual-value projections |
| **Market Monitor** | QLD registration activity, BITRE fleet, fuel, CPI and cash-rate context |
| **Data Quality** | Source counts, freshness, workflow and dbt evidence |

If the database or calibrated artifact is absent, the corresponding page reports that dependency
as unavailable; it does not substitute demo values.
"""
)

st.markdown("### Method and source boundaries")
st.markdown(
    """
- No scraping of carsales, Gumtree, Drive, or other ToS-protected marketplaces.
- Listing history is stored by ingestion snapshot; repeated snapshots are idempotent.
- A snapshot-based out-of-time evaluation is used only when at least two usable observations exist.
- QLD data is labelled as **new-registration and transfer activity**, not total active fleet.
"""
)

with st.sidebar:
    st.markdown("### 📊 AutoLens AU")
    st.markdown("Independent Data Product")
    st.markdown("---")
    st.markdown(f"**Refresh status:** {refresh.get('status', 'unknown')}")
    st.markdown(f"**Last refresh:** {refresh.get('completed_at') or 'Not run'}")
    st.markdown(f"**Model version:** {metrics.get('model_version', 'Not trained')}")
    st.markdown(f"**Validation:** {metrics.get('validation_strategy', 'Not measured')}")
    st.markdown("---")
    st.markdown("[GitHub](https://github.com/ozzy2438/autolens-au)")
