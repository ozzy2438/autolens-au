"""Government-source automotive market context."""

# Make the repository root importable and bridge Streamlit secrets into the
# environment before any `src.` / `config.` import reads configuration.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.dashboard.runtime import bootstrap

bootstrap()

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.data_access import (
    DashboardDataError,
    get_bitre_vehicle_makes,
    get_economic_context,
    get_latest_fuel_prices,
    get_listing_price_trends,
    get_qld_activity,
)

st.set_page_config(page_title="Market Monitor | AutoLens AU", page_icon="📊", layout="wide")
st.title("📊 Market Monitor")
st.markdown("Measured automotive context from QLD Open Data, BITRE, NSW FuelCheck and RBA.")

activity_tab, fleet_tab, fuel_tab, economy_tab = st.tabs(
    ["QLD Activity", "National Fleet", "Fuel Prices", "Economic Context"]
)

with activity_tab:
    st.subheader("QLD new-registration and transfer activity")
    try:
        qld = get_qld_activity()
        if qld.empty:
            st.info("The QLD activity table exists but contains no recorded observations.")
        else:
            qld["activity_count"] = pd.to_numeric(qld["activity_count"], errors="coerce")
            top_makes = qld.groupby("make")["activity_count"].sum().nlargest(10).index.tolist()
            filtered = qld[qld["make"].isin(top_makes)]
            st.plotly_chart(
                px.line(
                    filtered,
                    x="activity_month",
                    y="activity_count",
                    color="make",
                    line_dash="transaction_type",
                ),
                use_container_width=True,
            )
            st.caption(
                "This is transaction activity, not a count or market share of all active QLD vehicles."
            )
    except DashboardDataError as error:
        st.info(f"QLD activity is unavailable. ({error})")

with fleet_tab:
    st.subheader("BITRE registered vehicles by make")
    try:
        bitre = get_bitre_vehicle_makes()
        if bitre.empty:
            st.info("The BITRE table exists but contains no recorded observations.")
        else:
            latest_year = int(bitre["reference_year"].max())
            latest = bitre[bitre["reference_year"] == latest_year].nlargest(
                15, "registered_vehicles"
            )
            st.plotly_chart(
                px.bar(
                    latest,
                    x="registered_vehicles",
                    y="make",
                    orientation="h",
                    title=f"Top makes — {latest_year}",
                ),
                use_container_width=True,
            )
    except (DashboardDataError, TypeError, ValueError) as error:
        st.info(f"BITRE fleet data is unavailable. ({error})")

with fuel_tab:
    st.subheader("Latest NSW station fuel observations")
    try:
        fuel = get_latest_fuel_prices()
        if fuel.empty:
            st.info("The NSW fuel table exists but contains no recorded observations.")
        else:
            st.plotly_chart(
                px.bar(
                    fuel,
                    x="fuel_type",
                    y="average_aud_per_litre",
                    error_y=(fuel["maximum_aud_per_litre"] - fuel["average_aud_per_litre"]),
                    error_y_minus=(fuel["average_aud_per_litre"] - fuel["minimum_aud_per_litre"]),
                    labels={"average_aud_per_litre": "AUD per litre"},
                ),
                use_container_width=True,
            )
            st.dataframe(fuel, use_container_width=True, hide_index=True)
    except DashboardDataError as error:
        st.info(f"NSW fuel prices are unavailable. ({error})")

with economy_tab:
    st.subheader("CPI, cash rate and listing snapshot medians")
    try:
        cpi, cash_rate = get_economic_context()
        left, right = st.columns(2)
        with left:
            if cpi.empty:
                st.info("No CPI observations recorded.")
            else:
                st.line_chart(cpi.set_index("period_date")["cpi_index"])
        with right:
            if cash_rate.empty:
                st.info("No cash-rate observations recorded.")
            else:
                st.line_chart(cash_rate.set_index("period_date")["cash_rate_target_pct"])
        trends = get_listing_price_trends()
        if len(trends) >= 2:
            trend_chart = trends.set_index("snapshot_date")[
                ["median_price_aud", "real_median_price_aud"]
            ]
            st.line_chart(trend_chart)
        else:
            st.info(
                "At least two listing snapshots are required before a nominal-vs-real vehicle "
                "price trend can be shown."
            )
    except DashboardDataError as error:
        st.info(f"Economic context is unavailable. ({error})")
