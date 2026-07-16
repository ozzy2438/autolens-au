"""Instant valuation backed by the calibrated local model artifact."""

# Make the repository root importable and bridge Streamlit secrets into the
# environment before any `src.` / `config.` import reads configuration.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.dashboard.runtime import bootstrap

bootstrap()

from datetime import UTC, datetime

import pandas as pd
import streamlit as st

from src.api.schemas import MAX_MANUFACTURE_YEAR, MIN_MANUFACTURE_YEAR, ValuationRequest
from src.api.valuation_engine import ValuationEngine
from src.dashboard.components.charts import create_shap_waterfall, create_valuation_gauge
from src.dashboard.data_access import DashboardDataError, get_listing_catalog
from src.dashboard.release_artifacts import ReleaseArtifactError, prepare_dashboard_artifacts

st.set_page_config(page_title="Instant Valuation | AutoLens AU", page_icon="💰", layout="wide")


@st.cache_resource
def _load_engine() -> ValuationEngine:
    prepare_dashboard_artifacts()
    valuation_engine = ValuationEngine()
    valuation_engine.load()
    return valuation_engine


@st.cache_data(ttl=300)
def _load_catalog() -> pd.DataFrame:
    return get_listing_catalog()


try:
    engine: ValuationEngine | None = _load_engine()
    model_error = None
except (FileNotFoundError, ReleaseArtifactError, TypeError, OSError) as error:
    engine = None
    model_error = str(error)

try:
    catalog = _load_catalog()
except DashboardDataError:
    catalog = pd.DataFrame(columns=["brand", "model", "listing_count"])

fallback_brands = [
    "Toyota",
    "Mazda",
    "Hyundai",
    "Ford",
    "Kia",
    "Mitsubishi",
    "Volkswagen",
    "BMW",
    "Mercedes-Benz",
]
brands = sorted(catalog["brand"].dropna().unique().tolist()) or fallback_brands

st.title("💰 Instant Valuation")
if engine is None:
    st.warning(
        "Valuation is unavailable because no calibrated model bundle is present. "
        f"No heuristic price will be shown. ({model_error})"
    )
else:
    st.success(
        f"Calibrated model v{engine.model.version if engine.model else 'unknown'} loaded. "
        "Explanations below are local TreeSHAP contributions."
    )

with st.form("valuation_form"):
    left, right = st.columns(2)
    with left:
        brand = st.selectbox("Brand", options=brands)
        matching_models = catalog.loc[catalog["brand"] == brand, "model"].dropna().unique().tolist()
        model_name = (
            st.selectbox("Model", matching_models)
            if matching_models
            else st.text_input("Model", value="Camry")
        )
        variant = st.text_input("Variant / badge", value="Unknown")
        year = st.slider(
            "Year of manufacture",
            min_value=MIN_MANUFACTURE_YEAR,
            max_value=min(datetime.now(UTC).year + 1, MAX_MANUFACTURE_YEAR),
            value=2020,
        )
        kilometres = st.number_input(
            "Kilometres", min_value=0, max_value=1000000, value=45000, step=5000
        )
    with right:
        body_type = st.selectbox(
            "Body type", ["Sedan", "SUV", "Hatchback", "Wagon", "Ute", "Coupe", "Van"]
        )
        fuel_type = st.selectbox("Fuel type", ["Petrol", "Diesel", "Hybrid", "Electric", "LPG"])
        transmission = st.selectbox("Transmission", ["Automatic", "Manual"])
        drive_type = st.selectbox("Drive type", ["Unknown", "FWD", "RWD", "AWD", "4WD"])
        location = st.selectbox("Location", ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"])
    submitted = st.form_submit_button(
        "🔎 Get valuation", type="primary", use_container_width=True, disabled=engine is None
    )

if submitted and engine is not None:
    result = engine.valuate(
        ValuationRequest(
            brand=brand,
            model=str(model_name),
            variant=variant,
            year=year,
            kilometres=int(kilometres),
            body_type=body_type,
            fuel_type=fuel_type,
            transmission=transmission,
            drive_type=drive_type,
            condition="Used",
            location=location,
            doors=None,
            seats=None,
            cylinders=None,
        )
    )
    metric_columns = st.columns(4)
    metric_columns[0].metric("Estimate", f"${result.point_estimate_aud:,.0f}")
    metric_columns[1].metric("Lower bound", f"${result.lower_bound_aud:,.0f}")
    metric_columns[2].metric("Upper bound", f"${result.upper_bound_aud:,.0f}")
    metric_columns[3].metric(
        "Segment median",
        f"${result.segment_median_aud:,.0f}" if result.segment_median_aud else "Unavailable",
    )
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(
            create_valuation_gauge(
                result.point_estimate_aud,
                result.lower_bound_aud,
                result.upper_bound_aud,
            ),
            use_container_width=True,
        )
    with chart_right:
        st.plotly_chart(
            create_shap_waterfall([driver.model_dump() for driver in result.price_drivers]),
            use_container_width=True,
        )
    st.caption(result.disclaimer)
