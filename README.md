# AutoLens AU — Australian Vehicle Pricing & Residual Value Platform

> **Independent public data product** — designed, built, and operated by [Osman Orka](https://github.com/ozzy2438)  
> Live since July 2026 · [Dashboard](https://autolens-au.streamlit.app) · [API Docs](https://autolens-au-api.onrender.com/docs)

---

## What is AutoLens AU?

AutoLens AU is a **live-operated, independent data product** that provides Australian used-vehicle pricing intelligence, depreciation curves, and residual value estimates. It combines ~17,000 Australian vehicle listings with live government data sources to deliver market-grade valuations.

This is **not** a consulting engagement or anonymous client project. It is a public, verifiable data platform with:
- A live dashboard URL
- Monthly refresh cycles with logged changelogs
- Documented UAT with external users
- Model monitoring and drift detection
- Full commit history demonstrating operational maturity

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
├─────────────┬──────────────┬───────────────┬───────────────────┤
│ Kaggle AU   │ AU Car Mkt   │ NSW FuelCheck │ QLD Rego Data     │
│ Vehicles    │ Dataset      │ API (live)    │ (annual refresh)  │
├─────────────┴──────────────┴───────────────┴───────────────────┤
│                     INGESTION LAYER                              │
│              Python scripts + GitHub Actions                     │
├─────────────────────────────────────────────────────────────────┤
│                     PostgreSQL (Neon)                            │
│  ┌─────────┐    ┌───────────┐    ┌────────────────────────┐    │
│  │   RAW   │ →  │  STAGING  │ →  │   CORE (Star Schema)   │    │
│  │ schema  │    │   schema  │    │  fact_listing           │    │
│  └─────────┘    └───────────┘    │  dim_vehicle            │    │
│                                   │  dim_location           │    │
│                                   │  dim_date               │    │
│                                   └────────────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                    dbt TRANSFORMATIONS                           │
│         Models · Tests · Documentation · Lineage                │
├─────────────────────────────────────────────────────────────────┤
│                    ML / ANALYTICS LAYER                          │
│  Hedonic Pricing (LightGBM) · Depreciation Curves · SHAP       │
│  Residual Value Estimates · Prediction Intervals                │
├──────────────────────────┬──────────────────────────────────────┤
│    Streamlit Dashboard   │        FastAPI Valuation API         │
│  • Instant Valuation     │   POST /valuation                   │
│  • Depreciation Explorer │   → point estimate + range          │
│  • Market Monitor        │   → SHAP drivers                    │
│  • Data Quality Page     │   → OpenAPI docs auto-generated     │
└──────────────────────────┴──────────────────────────────────────┘
```

---

## Data Sources

| Source | Type | Refresh | Purpose |
|--------|------|---------|----------|
| [Australian Vehicle Prices](https://www.kaggle.com/datasets/nelgiriyewithana/australian-vehicle-prices) (Kaggle) | Historical | One-time + updates | Core listings (~16,700 records) |
| [Australia Car Market](https://www.kaggle.com/datasets/lainguyn123/australia-car-market-data) (Kaggle) | Historical | One-time | Secondary listings source |
| [NSW Fuel API](https://api.nsw.gov.au/Product/Index/22) | Live API | Daily capable | Real-time fuel prices for market context |
| [QLD Vehicle Registrations](https://www.data.qld.gov.au/dataset/vehicle-registrations) | Government open data | Annually | Fleet composition by make/model |
| [BITRE Road Vehicles Australia](https://www.bitre.gov.au/) | Government report | Annual | National fleet age & composition |
| ABS CPI / RBA rates | Government | Quarterly | Price deflation to real AUD |

### Compliance: No Scraping Policy

**This project does NOT scrape carsales, Gumtree, Drive, or any ToS-protected marketplace.**

This is a deliberate decision demonstrating professional judgement. All data comes from:
- Publicly available research datasets (Kaggle, CC-licensed)
- Official government open-data portals (NSW, QLD, ABS)
- Published government APIs with proper authentication

This approach reflects how a data-services company like RedBook/carsales operates: through authorised data partnerships, not scraping.

---

## Key Features

### Valuation Engine
- **Hedonic pricing model**: Regularised linear baseline → LightGBM ensemble
- **Features**: make, model, badge/variant proxy, year/age, odometer, body, fuel, transmission, drivetrain, location, age×km interaction
- **Explainability**: SHAP global importance + per-valuation explanations
- **Honest metrics**: MAE and MdAPE by segment, out-of-time validation, calibrated prediction intervals

### Depreciation & Residual Value
- **Depreciation curves** by segment (make/model groups)
- **3-year residual value estimates** with uncertainty bands
- **Price retention analysis** across vehicle categories

### Data Quality
- Deduplication rules (same vehicle across sources)
- Outlier handling (documented, not silent)
- Missing-value policy per column
- dbt tests + Great Expectations suites in CI
- Visible Data Quality page in dashboard

---

## Known Limitations — Documented, Not Hidden

Public listings data **lacks true condition and variant granularity**. We acknowledge this openly:

1. **Condition**: Proxied via age × odometer interaction and listing type (dealer vs private)
2. **Variant/badge**: Parsed from model strings where possible; wider prediction intervals where uncertain
3. **Geographic coverage**: Biased toward metro areas; rural listings underrepresented
4. **Temporal coverage**: 2023 snapshot with government data providing trend context

Where uncertainty is higher, prediction intervals are explicitly wider. This is a feature, not a bug.

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|------------|
| Database | PostgreSQL (Neon) | Job ad specifies SQL Server or Postgres |
| Transformations | dbt Core | Industry standard; lineage + testing |
| Orchestration | GitHub Actions | Monthly schedule + CI; doubles as "modern dev workflows" evidence |
| ML | scikit-learn, LightGBM, SHAP | Production-grade, interpretable |
| Dashboard | Streamlit | Rapid iteration, live deployment |
| API | FastAPI | Auto-generated OpenAPI docs; mirrors RedBook API shape |
| Data Quality | Great Expectations, dbt tests | Validation as code |
| Hosting | Neon (DB), Streamlit Cloud, Render (API) | Free tier = $0 operating cost |

---

## Project Structure

```
autolens-au/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # PR checks: lint, test, dbt
│       └── monthly_refresh.yml       # Scheduled data pipeline
├── src/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── kaggle_loader.py          # Load AU vehicle datasets
│   │   ├── nsw_fuelcheck.py          # NSW Fuel API client
│   │   ├── qld_registrations.py      # QLD rego data loader
│   │   └── abs_economic.py           # ABS CPI / RBA data
│   ├── models/
│   │   ├── __init__.py
│   │   ├── hedonic_model.py          # LightGBM valuation model
│   │   ├── depreciation.py           # Depreciation curve fitting
│   │   ├── residual_value.py         # 3-year residual estimates
│   │   └── evaluation.py            # Metrics, validation, monitoring
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI application
│   │   ├── schemas.py                # Pydantic request/response models
│   │   └── valuation_engine.py       # API business logic
│   └── dashboard/
│       ├── app.py                    # Streamlit main application
│       ├── pages/
│       │   ├── 1_instant_valuation.py
│       │   ├── 2_depreciation_explorer.py
│       │   ├── 3_market_monitor.py
│       │   └── 4_data_quality.py
│       └── components/
│           └── charts.py
├── dbt_autolens/
│   ├── dbt_project.yml
│   ├── profiles.yml.example
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_listings.sql
│   │   │   ├── stg_fuel_prices.sql
│   │   │   ├── stg_qld_registrations.sql
│   │   │   └── schema.yml
│   │   └── core/
│   │       ├── fact_listing.sql
│   │       ├── dim_vehicle.sql
│   │       ├── dim_location.sql
│   │       ├── dim_date.sql
│   │       └── schema.yml
│   ├── tests/
│   │   └── custom/
│   │       └── test_price_outliers.sql
│   └── macros/
│       └── generate_schema_name.sql
├── tests/
│   ├── unit/
│   │   ├── test_hedonic_model.py
│   │   ├── test_depreciation.py
│   │   └── test_data_quality.py
│   └── integration/
│       └── test_pipeline_e2e.py
├── great_expectations/
│   ├── great_expectations.yml
│   └── expectations/
│       └── listings_suite.json
├── docs/
│   ├── AI_DELIVERY_LOG.md
│   ├── DATA_DICTIONARY.md
│   ├── MODEL_CARD.md
│   ├── CHANGELOG.md
│   └── MONITORING.md
├── scripts/
│   ├── setup_database.py
│   ├── run_pipeline.py
│   └── train_model.py
├── config/
│   ├── settings.py
│   └── database.py
├── data/
│   └── .gitkeep
├── notebooks/
│   ├── 01_eda_exploration.ipynb
│   └── 02_model_development.ipynb
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── requirements.txt
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── CONTRIBUTING.md
├── LICENSE
└── STATUS.md
```

---

## How AI-Assisted Workflows Shaped Delivery

This project uses AI-assisted development (Claude Code, GitHub Copilot) with full transparency:

- **Per-PR documentation** in `docs/AI_DELIVERY_LOG.md`
- **Tagged PRs** indicating AI-assisted code generation
- **Honest accounting**: what was generated vs what was reviewed/corrected
- **Time savings quantified** where measurable

Example: Test suite scaffolded in ~1h vs estimated ~1 day manual; dbt model boilerplate generated then refined for business logic.

See [docs/AI_DELIVERY_LOG.md](docs/AI_DELIVERY_LOG.md) for the complete log.

---

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ (or Neon account)
- dbt Core 1.7+

### Quick Start

```bash
# Clone
git clone https://github.com/ozzy2438/autolens-au.git
cd autolens-au

# Environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your database credentials

# Setup database
python scripts/setup_database.py

# Run pipeline
python scripts/run_pipeline.py

# Run dbt
cd dbt_autolens
dbt run
dbt test

# Train model
python scripts/train_model.py

# Launch dashboard
streamlit run src/dashboard/app.py

# Launch API
uvicorn src.api.main:app --reload
```

---

## Monthly Operations

Every month, the automated pipeline:
1. Ingests fresh data from live sources (NSW Fuel API, QLD rego updates)
2. Runs dbt transformations with full test suite
3. Retrains model if drift detected (>5% MAE degradation)
4. Updates dashboard metrics
5. Logs results to `docs/CHANGELOG.md`

See [docs/MONITORING.md](docs/MONITORING.md) for the model monitoring framework.

---

## Evaluation Philosophy

- **No perfect scores anywhere** — AUC-ROC 1.0 is a leak, not a result
- **Segment-level reporting** — cheap vs premium, high-km vs low-km
- **Out-of-time validation** — because pricing models must work on future data
- **Calibrated prediction intervals** — 80% PI should contain 80% of actuals
- **Honest limitation documentation** — what the model can't do is as important as what it can

### Why Out-of-Time Splits Matter for Pricing

Vehicle prices are non-stationary: market conditions shift, new models launch, supply chains fluctuate. A random holdout split can leak temporal information (a 2023 listing price informing a 2022 prediction). Out-of-time splits simulate the actual production scenario: train on historical data, evaluate on future data. This is the only honest evaluation for a pricing model.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Status

![Pipeline Status](https://github.com/ozzy2438/autolens-au/actions/workflows/ci.yml/badge.svg)
![Monthly Refresh](https://github.com/ozzy2438/autolens-au/actions/workflows/monthly_refresh.yml/badge.svg)

See [STATUS.md](STATUS.md) for current operational status.
