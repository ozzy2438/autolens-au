# AutoLens AU — Australian Vehicle Pricing & Residual Value Platform

> **Independent public data product** — designed and built by [Osman Orka](https://github.com/ozzy2438)
> **Pre-launch:** the pipeline, model, dashboard, and API are under validation. No public deployment is currently claimed.

---

## What is AutoLens AU?

AutoLens AU is an **independent public data product in active development** for Australian
used-vehicle pricing intelligence, depreciation curves, and residual-value estimates. The
repository currently contains the application and data-platform scaffold; the first verified
data load, model training run, and public deployment have not yet been completed.

This is **not** a consulting engagement or anonymous client project. Evidence is published only
after it exists. The current state is:

- CI, ingestion, dbt, modelling, API, and dashboard code are present and being remediated
- No successful production refresh has been recorded
- No trained production model or measured production metric is available
- No public dashboard/API uptime or external UAT is claimed
- Operational evidence will be added through timestamped workflow runs and pull requests

---

## Target Architecture

The diagram below is the intended architecture, not a claim that every component is currently
deployed or populated.

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
├─────────────┬──────────────┬───────────────┬───────────────────┤
│ Kaggle AU   │ AU Car Mkt   │ NSW FuelCheck │ QLD Rego Data     │
│ Vehicles    │ Dataset      │ API client    │ (annual source)   │
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

## Planned Product Capabilities

These capabilities remain acceptance criteria until a verified training and refresh run publishes
their artifacts and metrics.

### Valuation Engine
- **Hedonic pricing model**: Regularised linear baseline → LightGBM ensemble
- **Features**: make, model, badge/variant proxy, year/age, odometer, body, fuel, transmission, drivetrain, location, age×km interaction
- **Explainability target**: SHAP global importance + per-valuation explanations
- **Evaluation target**: MAE and MdAPE by segment, snapshot-based out-of-time validation, calibrated prediction intervals

### Depreciation & Residual Value
- **Depreciation curves** by segment (make/model groups)
- **3-year residual value estimates** with uncertainty bands
- **Price retention analysis** across vehicle categories

### Data Quality
- Deduplication rules (same vehicle across sources)
- Outlier handling (documented, not silent)
- Missing-value policy per column
- dbt tests in CI; one validation framework will be retained as the production quality gate
- Visible Data Quality page in dashboard

---

## Known Limitations — Documented, Not Hidden

Public listings data **lacks true condition and variant granularity**. We acknowledge this openly:

1. **Condition**: Proxied via age × odometer interaction and listing type (dealer vs private)
2. **Variant/badge**: Parsed from model strings where possible; wider prediction intervals where uncertain
3. **Geographic coverage**: Biased toward metro areas; rural listings underrepresented
4. **Temporal coverage**: 2023 snapshot with government data providing trend context
5. **Temporal validation**: manufacture year is not listing time. A genuine out-of-time test is
   impossible until multiple `snapshot_date` refreshes exist
6. **Current readiness**: no production model is trained, prediction intervals are not calibrated,
   and public service availability has not been established

Once calibrated intervals exist, higher-uncertainty cases will be reported with wider ranges.

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|------------|
| Database | PostgreSQL (Neon) | Job ad specifies SQL Server or Postgres |
| Transformations | dbt Core | Industry standard; lineage + testing |
| Orchestration | GitHub Actions | Monthly schedule + CI; doubles as "modern dev workflows" evidence |
| ML | scikit-learn, LightGBM, SHAP | Production-grade, interpretable |
| Dashboard | Streamlit | Rapid iteration; deployment planned |
| API | FastAPI | Auto-generated OpenAPI docs; mirrors RedBook API shape |
| Data Quality | Great Expectations, dbt tests | Validation as code |
| Intended hosting | Neon (DB), Streamlit Cloud, Render (API) | Not deployed or verified yet |

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

This project uses AI-assisted development with commit-level disclosure:

- **Commit/PR documentation** in `docs/AI_DELIVERY_LOG.md`
- **Tagged PRs** for work performed through a pull-request workflow
- **Honest accounting**: what was generated vs what was reviewed/corrected
- **Time savings quantified** where measurable

The initial scaffold was pushed directly to `main`, so it must not be described as “10+ PRs”.
Time-saved figures are estimates and are labelled as such in the log.

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

## Intended Monthly Operations

After production credentials, data contracts, and quality gates are validated, the automated
pipeline is intended to:
1. Ingests fresh data from live sources (NSW Fuel API, QLD rego updates)
2. Runs dbt transformations with full test suite
3. Retrains model if drift detected (>5% MAE degradation)
4. Updates dashboard metrics
5. Logs results to `docs/CHANGELOG.md`

The workflow has not yet completed a production refresh. See
[docs/MONITORING.md](docs/MONITORING.md) for the monitoring acceptance criteria.

---

## Evaluation Philosophy

- **No perfect scores anywhere** — AUC-ROC 1.0 is a leak, not a result
- **Segment-level reporting** — cheap vs premium, high-km vs low-km
- **Out-of-time validation when data permits** — use listing `snapshot_date`, never manufacture year
- **Calibrated prediction intervals** — 80% PI should contain 80% of actuals
- **Honest limitation documentation** — what the model can't do is as important as what it can

### Why Out-of-Time Splits Matter for Pricing

Vehicle prices are non-stationary: market conditions shift, new models launch, and supply chains
fluctuate. A random holdout can leak temporal information. A genuine out-of-time split trains on
earlier listing snapshots and evaluates on later snapshots. The source data currently represents a
single 2023 snapshot, so manufacture-year splitting is only an extrapolation test across vehicle
ages, not out-of-time validation. True temporal validation will begin after refresh history exists.

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
