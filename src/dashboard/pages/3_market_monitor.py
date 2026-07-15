"""Market Monitor page.

Planned data integrations:
- Fleet composition trends (QLD rego data)
- Fuel price context (NSW FuelCheck API)
- Real vs nominal price movements (ABS CPI)
"""

import streamlit as st

st.set_page_config(page_title="Market Monitor | AutoLens AU", page_icon="\U0001f4ca", layout="wide")

st.title("\U0001f4ca Market Monitor")
st.markdown("Australian automotive market context from government data sources.")
st.warning(
    "Government-source ingestion has not completed a verified run. "
    "This page intentionally shows no placeholder observations.",
)

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["Fleet Composition", "Fuel Prices", "Price Trends"])

with tab1:
    st.subheader("\U0001f697 QLD Fleet Composition")
    st.markdown(
        "Vehicle registration data from [QLD Open Data Portal]"
        "(https://www.data.qld.gov.au/dataset/vehicle-registrations). "
        "Shows market share by make/model.",
    )

    st.info("Awaiting a validated QLD Open Data resource and first successful ingestion.")

with tab2:
    st.subheader("\u26fd NSW Fuel Prices")
    st.markdown(
        "Real-time fuel prices from [NSW Fuel API](https://api.nsw.gov.au/Product/Index/22). "
        "Running costs affect vehicle desirability and residual values.",
    )

    st.info("Awaiting NSW FuelCheck credentials and a verified API ingestion.")

with tab3:
    st.subheader("\U0001f4c8 Real vs Nominal Price Trends")
    st.markdown(
        "Vehicle prices adjusted for inflation using ABS CPI data. "
        "Reveals whether the market is genuinely moving or just tracking inflation.",
    )

    st.info("Awaiting validated CPI/RBA ingestion and listing snapshots with comparable dates.")

st.markdown("---")
st.caption("Last successful data refresh: none recorded")
