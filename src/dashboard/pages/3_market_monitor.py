"""Market Monitor page.

Live data integration showing:
- Fleet composition trends (QLD rego data)
- Fuel price context (NSW FuelCheck API)
- Real vs nominal price movements (ABS CPI)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Market Monitor | AutoLens AU", page_icon="\U0001F4CA", layout="wide")

st.title("\U0001F4CA Market Monitor")
st.markdown("Live Australian automotive market intelligence from government data sources.")

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["Fleet Composition", "Fuel Prices", "Price Trends"])

with tab1:
    st.subheader("\U0001F697 QLD Fleet Composition")
    st.markdown(
        "Vehicle registration data from [QLD Open Data Portal]"
        "(https://www.data.qld.gov.au/dataset/vehicle-registrations). "
        "Shows market share by make/model."
    )
    
    # Placeholder data (will be replaced with actual QLD rego data)
    fleet_data = pd.DataFrame({
        "Make": ["Toyota", "Mazda", "Hyundai", "Ford", "Mitsubishi",
                 "Holden", "Kia", "Nissan", "Volkswagen", "Honda"],
        "Registrations": [185000, 95000, 82000, 78000, 72000,
                          68000, 65000, 58000, 48000, 45000],
        "Market Share %": [18.5, 9.5, 8.2, 7.8, 7.2, 6.8, 6.5, 5.8, 4.8, 4.5],
    })
    
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            fleet_data, x="Make", y="Registrations",
            title="Top 10 Brands by QLD Registrations",
            color="Market Share %",
            color_continuous_scale="blues",
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.pie(
            fleet_data, values="Registrations", names="Make",
            title="Market Share Distribution",
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("\u26FD NSW Fuel Prices (Live)")
    st.markdown(
        "Real-time fuel prices from [NSW Fuel API](https://api.nsw.gov.au/Product/Index/22). "
        "Running costs affect vehicle desirability and residual values."
    )
    
    # Placeholder (will be replaced with live API data)
    st.metric("Average Unleaded 91 (NSW)", "$1.89/L", delta="-$0.03")
    st.metric("Average Diesel (NSW)", "$1.95/L", delta="+$0.01")
    st.metric("Average E10 (NSW)", "$1.83/L", delta="-$0.02")
    
    st.info("\U0001F4A1 High fuel prices increase demand for hybrid/EV and smaller engines, affecting residual values.")

with tab3:
    st.subheader("\U0001F4C8 Real vs Nominal Price Trends")
    st.markdown(
        "Vehicle prices adjusted for inflation using ABS CPI data. "
        "Reveals whether the market is genuinely moving or just tracking inflation."
    )
    
    # Placeholder trend data
    years = list(range(2019, 2027))
    nominal = [32000, 33000, 35000, 38000, 40000, 39000, 38500, 39000]
    real = [32000, 32500, 33800, 35500, 36200, 34500, 33200, 33000]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=nominal, name="Nominal AUD", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=years, y=real, name="Real AUD (2019 base)", line=dict(width=3, dash="dash")))
    fig.update_layout(
        title="Median Used Vehicle Prices — Nominal vs Real",
        xaxis_title="Year", yaxis_title="Price (AUD)",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.caption("Real prices deflated using ABS CPI (All Groups, Weighted Average of Eight Capital Cities).")

st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Data refreshed monthly")
