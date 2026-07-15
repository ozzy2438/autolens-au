"""Instant Valuation page.

User selects vehicle parameters and receives:
- Predicted retail price range with confidence band
- SHAP-based "why" explanations
- Comparison to segment median
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Instant Valuation | AutoLens AU", page_icon="\U0001F4B0", layout="wide")

st.title("\U0001F4B0 Instant Valuation")
st.markdown("Get an estimated market value for any Australian vehicle.")

# Vehicle selection form
col1, col2 = st.columns(2)

with col1:
    brand = st.selectbox(
        "Brand",
        options=["Toyota", "Mazda", "Hyundai", "Ford", "Holden", "Kia", "Mitsubishi",
                 "Volkswagen", "BMW", "Mercedes-Benz", "Audi", "Nissan", "Honda",
                 "Subaru", "Lexus", "Land Rover", "Tesla", "Other"],
        index=0,
    )
    model_name = st.text_input("Model", value="Camry")
    year = st.slider("Year of Manufacture", min_value=1990, max_value=2026, value=2020)
    kilometres = st.number_input("Kilometres", min_value=0, max_value=500000, value=45000, step=5000)

with col2:
    body_type = st.selectbox(
        "Body Type",
        options=["Sedan", "SUV", "Hatchback", "Wagon", "Ute", "Coupe", "Convertible", "Van"],
    )
    fuel_type = st.selectbox(
        "Fuel Type",
        options=["Petrol", "Diesel", "Hybrid", "Electric", "LPG"],
    )
    transmission = st.selectbox(
        "Transmission",
        options=["Automatic", "Manual"],
    )
    location = st.selectbox(
        "Location (State)",
        options=["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
    )

st.markdown("---")

if st.button("\U0001F50D Get Valuation", type="primary", use_container_width=True):
    # TODO: Call valuation API or model directly
    st.markdown("### Estimated Market Value")
    
    # Placeholder valuation (replace with actual model call)
    import numpy as np
    base_price = 35000
    age = 2026 - year
    depreciation = base_price * (1 - 0.12) ** age
    km_adjustment = -0.00003 * kilometres
    estimated = max(depreciation + km_adjustment * 1000, 3000)
    lower = estimated * 0.85
    upper = estimated * 1.15
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Lower Estimate", f"${lower:,.0f}")
    with col_b:
        st.metric("Point Estimate", f"${estimated:,.0f}", delta=None)
    with col_c:
        st.metric("Upper Estimate", f"${upper:,.0f}")
    
    st.info(f"80% confidence interval: ${lower:,.0f} – ${upper:,.0f} AUD")
    
    # Price drivers
    st.markdown("#### Key Price Drivers")
    drivers_data = {
        "Factor": ["Vehicle Age", "Kilometres", "Brand", "Body Type", "Location"],
        "Impact": [
            f"-${age * 2000:,.0f}" if age > 0 else "+$0",
            f"-${max(0, (kilometres - 15000*age) * 0.02):,.0f}",
            "+$3,000" if brand in ["Toyota", "Mazda"] else "+$0",
            "+$2,000" if body_type == "SUV" else "+$0",
            "+$1,000" if location in ["NSW", "VIC"] else "+$0",
        ],
        "Direction": ["\U0001F53B" if age > 0 else "\u2796", "\U0001F53B", "\U0001F53A", "\U0001F53A", "\U0001F53A"],
    }
    st.table(pd.DataFrame(drivers_data))
    
    st.caption(
        "\u26A0\uFE0F Disclaimer: This is an estimated market value based on publicly available data. "
        "Actual prices may vary based on condition, options, and market conditions."
    )
