# AutoLens AU — Operational Status

## Current Status: Pre-launch; Snowflake platform validated, first production refresh pending

| Component | Status | Last Check |
|-----------|--------|------------|
| Dashboard | Not deployed; verified release-artifact retrieval implemented | 2026-07-15 |
| Valuation API | Not deployed or verified | 2026-07-15 |
| Production database | Snowflake warehouse/RBAC/schemas and empty RAW tables verified; not populated | 2026-07-15 |
| CI Pipeline | Python/PostgreSQL gates passing; real Snowflake seed + dbt build validated (47/47) | 2026-07-15 |
| Monthly Refresh | Snowflake key-pair identity configured; no source-credentialled run recorded | 2026-07-15 |
| Model | Calibrated/TreeSHAP implementation tested; production artifact not trained | 2026-07-15 |
| Model Drift | Not evaluable before a baseline and later snapshot exist | 2026-07-15 |
| Container Delivery | GHCR workflow implemented; correctly blocked until a model release exists | 2026-07-15 |
| Deployment Health | Six-hourly workflow implemented; public URL variables not configured | 2026-07-15 |
| GitHub Secrets | Snowflake CI/pipeline identities configured; source and hosting secrets remain | 2026-07-15 |

---

## Uptime Log

No uptime measurement has started. A six-hourly point-in-time health workflow now exists, but its
`API_HEALTH_URL` and `DASHBOARD_URL` repository variables are intentionally unset until real
services are deployed. Public URLs will be listed only after that workflow verifies both endpoints.

---

## Incident Log

No production incidents can be recorded before launch. Pre-launch defects are tracked through
GitHub issues, pull requests, and CI runs.

---

## Links

- CI Status: https://github.com/ozzy2438/autolens-au/actions
- Audit remediation PR: https://github.com/ozzy2438/autolens-au/pull/1
- Deployment evidence follow-up PR: https://github.com/ozzy2438/autolens-au/pull/2

The previously documented Streamlit and Render URLs were not publicly functional on 2026-07-15
and have been removed until deployment is verified.
