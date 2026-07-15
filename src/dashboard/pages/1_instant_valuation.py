"""Instant Valuation page.

User selects vehicle parameters and receives:
- Predicted retail price range with calibrated prediction interval
- SHAP-based "why" explanations after model validation
- Comparison to segment median
"""

import streamlit as st

st.set_page_config(
    page_title="Instant Valuation | AutoLens AU", page_icon="\U0001f4b0", layout="wide"
)

st.title("\U0001f4b0 Instant Valuation")
st.markdown("Enter vehicle details for valuation once the verified model artifact is available.")
st.warning(
    "Valuation is unavailable: the first production model has not been trained. "
    "No heuristic or placeholder price is shown as a model result.",
)

# Vehicle selection form
col1, col2 = st.columns(2)

with col1:
    brand = st.selectbox(
        "Brand",
        options=[
            "Toyota",
            "Mazda",
            "Hyundai",
            "Ford",
            "Holden",
            "Kia",
            "Mitsubishi",
            "Volkswagen",
            "BMW",
            "Mercedes-Benz",
            "Audi",
            "Nissan",
            "Honda",
            "Subaru",
            "Lexus",
            "Land Rover",
            "Tesla",
            "Other",
        ],
        index=0,
    )
    model_name = st.text_input("Model", value="Camry")
    year = st.slider("Year of Manufacture", min_value=1990, max_value=2026, value=2020)
    kilometres = st.number_input(
        "Kilometres", min_value=0, max_value=500000, value=45000, step=5000
    )

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

st.button("\U0001f50d Get Valuation", type="primary", use_container_width=True, disabled=True)
