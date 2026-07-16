# AutoLens AU — Operational Status

## Current Status: First measured refresh and model release complete; public deployment pending

| Component | Status | Last Check |
|-----------|--------|------------|
| Dashboard | Not deployed; release-artifact retrieval implemented and a calibrated release now exists | 2026-07-16 |
| Valuation API | Not deployed; tested container image published to GHCR | 2026-07-16 |
| Production database | Populated: 16,648 listing snapshot rows, QLD activity, CPI/cash-rate in `AUTOLENS_AU` | 2026-07-16 |
| CI Pipeline | Python/PostgreSQL gates plus real Snowflake dbt build and ingestion write check, all passing | 2026-07-16 |
| Monthly Refresh | First credentialled run recorded ([run 29472238867](https://github.com/ozzy2438/autolens-au/actions/runs/29472238867)); status **degraded**: NSW fuel and BITRE sources failed, required listings succeeded | 2026-07-16 |
| Model | First calibrated artifact trained and published as [`model-29472238867-1`](https://github.com/ozzy2438/autolens-au/releases/tag/model-29472238867-1): LightGBM MAE $5,859, MdAPE 10.1%, 80% PI coverage 79.95%, single-snapshot random holdout (honestly labelled; genuine out-of-time validation begins with the second monthly snapshot) | 2026-07-16 |
| Model Drift | Baseline established; first drift evaluation possible after the August snapshot | 2026-07-16 |
| Container Delivery | First image published: `ghcr.io/ozzy2438/autolens-au` (preflight verified the model release) | 2026-07-16 |
| Deployment Health | Six-hourly workflow implemented; public URL variables not configured | 2026-07-16 |
| GitHub Secrets | Snowflake CI/pipeline, NSW FuelCheck and Kaggle identities configured; hosting secrets remain | 2026-07-16 |

---

## Known degraded sources

The first refresh recorded two best-effort source failures (the refresh design lets the
required listings source proceed regardless):

- `fuel` (NSW FuelCheck): request retries exhausted — under investigation
- `bitre` (workbook download): read timeout — under investigation

Both are tracked for the next refresh; evidence is in
[`docs/operations/latest_refresh.json`](docs/operations/latest_refresh.json).

---

## Uptime Log

No uptime measurement has started. A six-hourly point-in-time health workflow exists, but its
`API_HEALTH_URL` and `DASHBOARD_URL` repository variables are intentionally unset until real
services are deployed. Public URLs will be listed only after that workflow verifies both endpoints.

---

## Incident Log

No production incidents can be recorded before launch. Pre-launch defects are tracked through
GitHub issues, pull requests, and CI runs.

---

## Links

- [CI Status](https://github.com/ozzy2438/autolens-au/actions)
- [First measured refresh evidence (PR #12)](https://github.com/ozzy2438/autolens-au/pull/12)
- [First model release](https://github.com/ozzy2438/autolens-au/releases/tag/model-29472238867-1)

The previously documented Streamlit and Render URLs were not publicly functional on 2026-07-15
and have been removed until deployment is verified.
