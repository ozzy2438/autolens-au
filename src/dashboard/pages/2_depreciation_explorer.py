"""Observed depreciation curves and fitted residual-value projections."""

import pandas as pd
import streamlit as st

from src.dashboard.components.charts import create_depreciation_chart
from src.dashboard.data_access import DashboardDataError, get_listing_data
from src.models.depreciation import compute_all_depreciation_curves
from src.models.hedonic_model import engineer_features
from src.models.residual_value import compute_segment_residual_values

st.set_page_config(page_title="Depreciation Explorer | AutoLens AU", page_icon="📉", layout="wide")


@st.cache_data(ttl=300)
def _load_listings() -> pd.DataFrame:
    return get_listing_data()


st.title("📉 Depreciation Explorer")
st.markdown("Observed median listing-price retention by vehicle age and brand.")

try:
    raw_listings = _load_listings()
    listings = engineer_features(raw_listings)
    listings["price"] = pd.to_numeric(listings["price"], errors="coerce")
except DashboardDataError as error:
    listings = pd.DataFrame()
    st.warning(f"Listing data is unavailable; no synthetic curve is shown. ({error})")

if not listings.empty:
    brands = sorted(listings["brand"].dropna().unique().tolist())
    left, right = st.columns(2)
    with left:
        selected_brands = st.multiselect(
            "Brands to compare", options=brands, default=brands[: min(3, len(brands))]
        )
    with right:
        max_age = st.slider("Maximum vehicle age", 5, 20, 15)

    curves = compute_all_depreciation_curves(
        listings[listings["age"] <= max_age],
        segments=selected_brands,
        min_samples=1,
    )
    if curves:
        st.plotly_chart(
            create_depreciation_chart(curves, max_age=max_age), use_container_width=True
        )
        curve_table = pd.concat(curves.values(), ignore_index=True)
        st.dataframe(
            curve_table[["segment", "age", "median_price", "retention_pct", "sample_count"]],
            use_container_width=True,
            hide_index=True,
        )
        residual_values = compute_segment_residual_values(
            listings[listings["brand"].isin(selected_brands)],
            segment_col="brand",
            horizon_years=3,
            min_samples=30,
        )
        if not residual_values.empty:
            st.markdown("### Fitted three-year residual-value projections")
            st.dataframe(
                residual_values[
                    [
                        "segment",
                        "residual_value_pct",
                        "projected_value_aud",
                        "sample_count",
                        "model_r_squared",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
    elif selected_brands:
        st.info("The selected brands do not have at least three observed age buckets.")

st.caption(
    "Retention is anchored to each segment's youngest observed age bucket. Residual values are "
    "fitted projections from observed medians, not guaranteed transaction prices."
)
