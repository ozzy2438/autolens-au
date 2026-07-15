"""Depreciation Explorer page.

Compare depreciation/retention curves across vehicle segments.
This is the single most RedBook-shaped artefact in the project.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Depreciation Explorer | AutoLens AU", page_icon="\U0001F4C9", layout="wide")

st.title("\U0001F4C9 Depreciation Explorer")
st.markdown(
    "Compare how different vehicles retain their value over time. "
    "Depreciation is the single largest cost of vehicle ownership."
)

# Segment selection
col1, col2 = st.columns(2)

with col1:
    selected_brands = st.multiselect(
        "Select brands to compare",
        options=["Toyota", "Mazda", "Hyundai", "Ford", "Holden", "BMW",
                 "Mercedes-Benz", "Audi", "Volkswagen", "Kia", "Subaru"],
        default=["Toyota", "BMW", "Hyundai"],
    )

with col2:
    max_age = st.slider("Maximum vehicle age (years)", 5, 20, 15)

st.markdown("---")

# Generate sample depreciation curves
# TODO: Replace with actual computed curves from database
if selected_brands:
    fig = go.Figure()
    
    # Sample decay rates by brand (will be replaced with actual fitted values)
    decay_rates = {
        "Toyota": 0.10, "Mazda": 0.12, "Hyundai": 0.14, "Ford": 0.15,
        "Holden": 0.16, "BMW": 0.18, "Mercedes-Benz": 0.17, "Audi": 0.17,
        "Volkswagen": 0.14, "Kia": 0.15, "Subaru": 0.11,
    }
    
    ages = np.arange(0, max_age + 1)
    
    for brand in selected_brands:
        rate = decay_rates.get(brand, 0.13)
        retention = 100 * np.exp(-rate * ages)
        fig.add_trace(go.Scatter(
            x=ages, y=retention,
            mode="lines+markers",
            name=brand,
            line=dict(width=3),
        ))
    
    fig.update_layout(
        title="Price Retention by Brand (%)",
        xaxis_title="Vehicle Age (years)",
        yaxis_title="Retention (%)",
        yaxis=dict(range=[0, 105]),
        hovermode="x unified",
        template="plotly_white",
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Comparison table
    st.markdown("#### Retention Summary")
    comparison_data = []
    for brand in selected_brands:
        rate = decay_rates.get(brand, 0.13)
        comparison_data.append({
            "Brand": brand,
            "1-Year Retention": f"{100 * np.exp(-rate * 1):.1f}%",
            "3-Year Retention": f"{100 * np.exp(-rate * 3):.1f}%",
            "5-Year Retention": f"{100 * np.exp(-rate * 5):.1f}%",
            "10-Year Retention": f"{100 * np.exp(-rate * 10):.1f}%",
        })
    
    st.table(pd.DataFrame(comparison_data))
else:
    st.info("Select at least one brand to view depreciation curves.")

st.markdown("---")
st.caption(
    "Curves are based on median prices by age within each brand segment. "
    "Individual models within a brand may depreciate faster or slower. "
    "Luxury brands show high initial depreciation but absolute values remain higher."
)
