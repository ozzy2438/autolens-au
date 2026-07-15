"""AutoLens AU Dashboard — Main Application.

Streamlit multi-page dashboard providing:
1. Instant Valuation — select vehicle params, get predicted price
2. Depreciation Explorer — compare retention curves
3. Market Monitor — fleet composition and fuel price trends
4. Data Quality — pipeline health, freshness, test results

Deployment target: Streamlit Cloud (not yet verified)
"""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="AutoLens AU — Vehicle Pricing Intelligence",
    page_icon="\U0001f697",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Main page content
st.title("\U0001f697 AutoLens AU")
st.subheader("Australian Vehicle Pricing & Residual Value Platform")

st.markdown("""
---

### Welcome to AutoLens AU

This is an **independent public data product in pre-launch development** for Australian
used-vehicle pricing intelligence, depreciation curves, and residual value estimates.

> **Current state:** no production refresh, trained model, or public service deployment has been
> verified. Pages show availability honestly and will display results only from recorded artifacts.

#### Features

| Page | Description |
|------|-------------|
| **Instant Valuation** | Select make/model/year/km → predicted price + confidence band |
| **Depreciation Explorer** | Compare retention curves across brands and models |
| **Market Monitor** | Fleet composition trends, fuel prices, economic context |
| **Data Quality** | Pipeline health, data freshness, test results |

#### Data Sources

- **Australian vehicle listings** (Kaggle source; load pending)
- **NSW Fuel API** (client validation pending)
- **QLD Vehicle Registrations** (resource validation pending)
- **ABS CPI / RBA** (integration pending)

#### Methodology

- Hedonic pricing model (LightGBM) on log(price)
- SHAP-based explainability for each valuation
- Segment-level depreciation curves with parametric fitting
- 3-year residual value projections with uncertainty bands

---

*Built by [Osman Orka](https://github.com/ozzy2438)*
*[GitHub Repository](https://github.com/ozzy2438/autolens-au) · API deployment pending*
""")

# Sidebar
with st.sidebar:
    st.markdown("### \U0001f4ca AutoLens AU")
    st.markdown("Independent Data Product")
    st.markdown("---")
    st.markdown("**Status:** Pre-launch remediation")
    st.markdown("**Last Refresh:** Not run")
    st.markdown("**Model Version:** Not trained")
    st.markdown("---")
    st.markdown(
        "[GitHub](https://github.com/ozzy2438/autolens-au)",
    )
