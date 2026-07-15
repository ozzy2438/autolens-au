"""AutoLens AU Dashboard — Main Application.

Streamlit multi-page dashboard providing:
1. Instant Valuation — select vehicle params, get predicted price
2. Depreciation Explorer — compare retention curves
3. Market Monitor — fleet composition and fuel price trends
4. Data Quality — pipeline health, freshness, test results

Deployment: Streamlit Cloud (free tier)
URL: https://autolens-au.streamlit.app
"""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="AutoLens AU — Vehicle Pricing Intelligence",
    page_icon="\U0001F697",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Main page content
st.title("\U0001F697 AutoLens AU")
st.subheader("Australian Vehicle Pricing & Residual Value Platform")

st.markdown("""
---

### Welcome to AutoLens AU

This is an **independent public data product** providing Australian used-vehicle
pricing intelligence, depreciation curves, and residual value estimates.

#### Features

| Page | Description |
|------|-------------|
| **Instant Valuation** | Select make/model/year/km → predicted price + confidence band |
| **Depreciation Explorer** | Compare retention curves across brands and models |
| **Market Monitor** | Fleet composition trends, fuel prices, economic context |
| **Data Quality** | Pipeline health, data freshness, test results |

#### Data Sources

- **~16,700 Australian vehicle listings** (Kaggle public datasets)
- **NSW Fuel API** (live government data)
- **QLD Vehicle Registrations** (annual fleet composition)
- **ABS CPI / RBA** (economic context)

#### Methodology

- Hedonic pricing model (LightGBM) on log(price)
- SHAP-based explainability for each valuation
- Segment-level depreciation curves with parametric fitting
- 3-year residual value projections with uncertainty bands

---

*Built and operated by [Osman Orka](https://github.com/ozzy2438)*  
*[GitHub Repository](https://github.com/ozzy2438/autolens-au) · [API Documentation](https://autolens-au-api.onrender.com/docs)*
""")

# Sidebar
with st.sidebar:
    st.markdown("### \U0001F4CA AutoLens AU")
    st.markdown("Independent Data Product")
    st.markdown("---")
    st.markdown("**Status:** \U0001F7E2 Operational")
    st.markdown("**Last Refresh:** July 2026")
    st.markdown("**Model Version:** 1.0.0")
    st.markdown("---")
    st.markdown(
        "[GitHub](https://github.com/ozzy2438/autolens-au) | "
        "[API Docs](https://autolens-au-api.onrender.com/docs)"
    )
