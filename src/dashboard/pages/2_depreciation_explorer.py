"""Depreciation Explorer page.

Compare depreciation/retention curves across vehicle segments.
This is the single most RedBook-shaped artefact in the project.
"""

import streamlit as st

st.set_page_config(
    page_title="Depreciation Explorer | AutoLens AU", page_icon="\U0001f4c9", layout="wide"
)

st.title("\U0001f4c9 Depreciation Explorer")
st.markdown(
    "Compare how different vehicles retain their value over time. "
    "Depreciation is the single largest cost of vehicle ownership.",
)
st.warning(
    "Depreciation curves are unavailable until the listing dataset has been loaded and the "
    "segment curves have been computed. No synthetic decay rates are displayed.",
)

# Segment selection
col1, col2 = st.columns(2)

with col1:
    selected_brands = st.multiselect(
        "Select brands to compare",
        options=[
            "Toyota",
            "Mazda",
            "Hyundai",
            "Ford",
            "Holden",
            "BMW",
            "Mercedes-Benz",
            "Audi",
            "Volkswagen",
            "Kia",
            "Subaru",
        ],
        default=["Toyota", "BMW", "Hyundai"],
    )

with col2:
    max_age = st.slider("Maximum vehicle age (years)", 5, 20, 15)

st.markdown("---")

if selected_brands:
    st.info(
        f"Awaiting computed curves for {len(selected_brands)} selected brand(s), "
        f"up to {max_age} years.",
    )

st.markdown("---")
st.caption(
    "When available, curves will be based on observed median prices by age within each segment "
    "and labelled with their source snapshot.",
)
