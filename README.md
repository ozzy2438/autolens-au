# AutoLens AU — Australian Vehicle Pricing & Residual Value Platform

> **Independent public data product** — designed and built by [Osman Orka](https://github.com/ozzy2438)
> **Pre-launch:** the pipeline, model, dashboard, and API are under validation. No public deployment is currently claimed.

---

## What is AutoLens AU?

AutoLens AU is an **independent public data product in active development** for Australian
used-vehicle pricing intelligence, depreciation curves, and residual-value estimates. The
repository contains tested ingestion, transformation, modelling, API, and dashboard implementations;
the first credentialled production load, model training run, and public deployment have not yet
been completed.

This is **not** a consulting engagement or anonymous client project. Evidence is published only
after it exists. The current state is:

- CI runs the full Python suite and a seed-backed `dbt build`
- Source parsers have been validated against current QLD, BITRE and RBA publications
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
│ Kaggle AU   │ AU Car Mkt   │ NSW FuelCheck │ QLD Activity      │
│ Vehicles    │ Dataset      │ API client    │ + BITRE + RBA     │
├─────────────┴──────────────┴───────────────┴───────────────────┤
│                     INGESTION LAYER                              │
│              Python scripts + GitHub Actions                     │
├─────────────────────────────────────────────────────────────────┤
│                         Snowflake                                │
│  ┌─────────┐    ┌───────────┐    ┌────────────────────────┐    │
│  │   RAW   │ →  │  STAGING  │ →  │   CORE (Star Schema)   │    │
│  │ schema  │    │   schema  │    │  fact_listing           │    │
│  └─────────┘    └───────────┘    │  dim_vehicle            │    │
│                                   │  dim_location           │    │
│                                   │  dim_year               │    │
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
| [QLD registration activity](https://www.data.qld.gov.au/dataset/vehicle-registration-new-and-transfers-test) | Government open data | Partitioned updates | New-registration and transfer activity; not total fleet |
| [BITRE Road Vehicles Australia](https://www.bitre.gov.au/resource/roads-vehicles/road-vehicles-australia-january-2025) | Government report | Annual | National registered vehicles by make |
| [RBA statistical tables G1/F1](https://www.rba.gov.au/statistics/tables/) | Government | Quarterly/daily | CPI deflation and cash-rate context |

### Compliance: No Scraping Policy

**This project does NOT scrape carsales, Gumtree, Drive, or any ToS-protected marketplace.**

This is a deliberate decision demonstrating professional judgement. All data comes from:
- Publicly available research datasets (Kaggle, CC-licensed)
- Official government open-data portals (NSW, QLD, ABS)
- Published government APIs with proper authentication

This approach reflects how a data-services company like RedBook/carsales operates: through authorised data partnerships, not scraping.

---

## Implemented Product Capabilities

These code paths are tested, but product outputs remain unavailable until a verified training and
refresh run publishes their artifacts and metrics.

### Valuation Engine
- **Hedonic pricing model**: Regularised linear baseline → LightGBM
- **Features**: make, model, badge/variant proxy, year/age, odometer, body, fuel, transmission, drivetrain, location, age×km interaction
- **Explainability**: local TreeSHAP contributions generated from the trained LightGBM pipeline
- **Evaluation**: MAE and MdAPE by segment; genuine snapshot OOT when available, explicitly
  labelled random fallback otherwise; held-out split-conformal prediction intervals

### Depreciation & Residual Value
- **Depreciation curves** by segment (make/model groups)
- **3-year residual value estimates** with uncertainty bands
- **Price retention analysis** across vehicle categories

### Data Quality
- Deduplication rules (same vehicle across sources)
- Outlier handling (documented, not silent)
- Missing-value policy per column
- dbt source/model/relationship tests run through `dbt build` in CI
- Data Quality page reads persisted workflow evidence, source row counts, freshness and model metrics

---

## Known Limitations — Documented, Not Hidden

Public listings data **lacks true condition and variant granularity**. We acknowledge this openly:

1. **Condition**: Source labels are coarse (new/used/demo); there is no physical condition score
2. **Variant/badge**: Used where supplied by the source; otherwise explicitly `Unknown`
3. **Geographic coverage**: Biased toward metro areas; rural listings underrepresented
4. **Temporal coverage**: 2023 snapshot with government data providing trend context
5. **Temporal validation**: manufacture year is not listing time. A genuine out-of-time test is
   impossible until multiple `snapshot_date` refreshes exist
6. **Current readiness**: no production model is trained, so no measured interval calibration or
   public service availability is claimed

Once calibrated intervals exist, higher-uncertainty cases will be reported with wider ranges.

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|------------|
| Database | Snowflake + local PostgreSQL compatibility | Managed production RBAC/compute; secretless PR tests |
| Transformations | dbt Core | Industry standard; lineage + testing |
| Orchestration | GitHub Actions | Monthly schedule + CI; doubles as "modern dev workflows" evidence |
| ML | scikit-learn, LightGBM, SHAP | Production-grade, interpretable |
| Dashboard | Streamlit | Rapid iteration; deployment planned |
| API | FastAPI | Auto-generated OpenAPI docs; mirrors RedBook API shape |
| Data Quality | dbt tests + pytest | One enforced validation path in CI |
| Intended hosting | Snowflake, Streamlit Cloud, Render (API) | Database provisioned; services not publicly deployed |

### Why Snowflake (decision record)

The target job advert names SQL Server or PostgreSQL, and the code keeps a fully
working PostgreSQL path: local Docker development and every pull-request CI gate run
on PostgreSQL with no secrets, which also keeps forked-PR builds safe. Production and
the credentialled CI integration run on Snowflake instead, and that is a deliberate
choice rather than a detour from the advert:

- **Access control as a first-class artefact.** Ingestion, transformation, read-only
  application, and CI each get a distinct least-privilege role over managed-access
  schemas, and the human account no longer runs day-to-day work as `ACCOUNTADMIN`.
  This is the kind of governance a data-services company operates, and it is visible
  and reviewable in [`infra/snowflake/bootstrap.sql`](infra/snowflake/bootstrap.sql).
- **Key-pair service identities, no passwords in automation.** Every non-human caller
  (CI, the scheduled pipeline, and the future dashboard/API) authenticates with an RSA
  key pair; no password reaches GitHub Actions, Streamlit, or Render.
- **Cost-controlled, idempotent, reproducible.** A single X-Small warehouse with
  60-second auto-suspend backs ingestion, dbt, CI, and application reads; the account
  bootstrap is re-runnable and a credit
  [resource monitor](infra/snowflake/resource_monitor.sql) caps spend.
- **Same modelling code, portable SQL.** The dbt project and ingestion loaders emit
  dialect-appropriate SQL, so the warehouse choice does not lock the transformation or
  Python layers to one vendor.

The honest framing for interviews is *"PostgreSQL-compatible by design, operated on
Snowflake with production-grade RBAC, key-pair auth, and isolated CI"* — a stronger
story than a single local database, told without overclaiming. Operating cost is no
longer strictly `$0`; it is a small, deliberate, capped monthly credit spend.

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
│   │   ├── qld_registrations.py      # QLD activity loader
│   │   ├── bitre_vehicles.py         # BITRE workbook loader
│   │   └── abs_economic.py           # RBA CPI / cash-rate data
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
│       ├── data_access.py            # Read-only DB/artifact repository
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
│   │       ├── dim_year.sql
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
- Python 3.11.x
- Snowflake account for production/runtime operations
- PostgreSQL 15+ only for local Docker and secretless integration tests
- dbt Core 1.11.x

### Quick Start

```bash
# Clone
git clone https://github.com/ozzy2438/autolens-au.git
cd autolens-au

# Environment
python -m venv .venv
source .venv/bin/activate
python -m pip install uv==0.6.13
uv sync --frozen --extra dev --extra dbt

# Configure
cp .env.example .env
# Edit .env with a least-privileged Snowflake service identity.
# Never use ACCOUNTADMIN for the application or pipeline.
mkdir -p ~/.dbt
cp dbt_autolens/profiles.yml.example ~/.dbt/profiles.yml

# Setup database
python scripts/setup_database.py

# Run pipeline
python scripts/run_pipeline.py

# Run dbt
cd dbt_autolens
dbt build

# Train model
python scripts/train_model.py

# Launch dashboard
streamlit run src/dashboard/app.py

# Launch API
uvicorn src.api.main:app --reload
```

`uv.lock` is the dependency source of truth. `requirements.txt` is a generated, fully pinned
Streamlit Cloud export; run `make requirements` after lock changes. CI rejects drift between them.

Snowflake warehouse/database/schema/role configuration is defined in the credential-free,
idempotent [`infra/snowflake/bootstrap.sql`](infra/snowflake/bootstrap.sql). See
[`docs/SNOWFLAKE.md`](docs/SNOWFLAKE.md) for the permission matrix, key-pair authentication,
GitHub secret names, deployment settings, validation, and rotation procedure.

For Streamlit Cloud, configure `MODEL_RELEASE_REPOSITORY=ozzy2438/autolens-au`. The dashboard
then retrieves the newest complete `model-*` prerelease, verifies the release asset digests, and
caches the calibrated model plus measured metrics. Public releases require no GitHub token; a
read-only `GITHUB_TOKEN` can be supplied for private repositories or higher API limits.

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
