# AutoLens AU — Australian Vehicle Pricing & Residual Value Platform
### Complete build roadmap · Targeting carsales/RedBook-class Data Analyst roles · July 2026

---

## Remediation execution status — 15 July 2026

This roadmap is now tracked in the repository. “Implemented” below means the code path and its
automated tests exist; it does **not** mean a credentialled production run, deployment, UAT session,
or month of operating history has happened.

| Workstream | State | Verifiable evidence / remaining gate |
|---|---|---|
| Truth and public claims | Implemented | Pre-launch wording; fabricated uptime, refresh, UAT and metric claims removed |
| Python + dbt CI | Implemented | Ruff, mypy, full pytest and seed-backed `dbt build` are blocking PR checks |
| Listing ingestion | Implemented | Two mapped Kaggle schemas, schema-drift rejection, stable fingerprint and append-only snapshots |
| Government sources | Implemented | Current QLD CKAN activity, BITRE Table 7, RBA G1 CPI and F1 cash-rate loaders |
| Valuation artifact | Implemented, not trained on production data | Model/variant features, held-out interval calibration, TreeSHAP, measured metrics artifact |
| Temporal evaluation | Guarded | Snapshot OOT only with ≥2 usable snapshots; single-snapshot fallback is labelled honestly |
| Dashboard + API | Implemented, not deployed | Real DB/artifact paths, verified model-release retrieval and explicit unavailable states |
| Monthly operations | Implemented, not run | Measured status/changelog, dbt evidence, drift decision and release artifact workflow |
| Container delivery | Implemented, not released | GHCR delivery refuses to publish without a calibrated model release |
| Deployment health | Implemented, not configured | Six-hourly point-in-time API/dashboard probes require real public URL variables |
| Production credentials | Blocked externally | GitHub currently has no DB, Kaggle, NSW FuelCheck or hosting secrets configured |
| ≥3 refreshes / ≥3 UAT users | Calendar/user work | Cannot be truthfully completed by code or backfilled |

The next real-world gate is to provision the named GitHub secrets, run the monthly workflow once,
review its evidence PR, configure hosting, and then begin the genuine multi-month/UAT record.

---

## 0. Target positioning statement (use only after the evidence exists)

AutoLens AU is currently a **public, pre-launch independent data product**. It may be described as
“live-operated” on the CV, GitHub, LinkedIn, or in interviews only after public endpoints and a real
operating record exist. No anonymous client. No implied employer.

Why this framing wins the "bu adam sorun çıkarmaz" test:

- A hiring manager can verify every claim in 90 seconds: live URL, commit history, monthly refresh changelog, model monitoring page, documented UAT. An anonymous client engagement can verify nothing.
- The interview story has one arc with clean ownership language: *"I scoped it, I built it, I operate it, these are the users, this is what changed after their feedback."* No ownership ambiguity to trip over (VicRoads lesson #2).
- CV framing and verbal narrative are identical, so nothing collapses under panel questioning (VicRoads lesson #3).
- It converts your biggest structural weakness (solo portfolio, no referees) into a strength: *operational maturity you can prove*.

**Current CV label:** `Independent Data Product — public, pre-launch (github.com/ozzy2438/autolens-au)`

**Future label after verification:** `Independent Data Product — public, live-operated (github.com/ozzy2438/autolens-au · verified demo URL)`

---

## Phase 0 — Master Career Truth Sheet (Day 1, before any code)

Your friend's single best recommendation. One document, one source of truth, everything else derives from it.

For every CV entry, record: exact organisation name (or "independent public project"), exact title, exact dates, who the contract was with (if any), team structure, your real role, what went live, realised vs modelled outcomes, and whether the name can be disclosed.

Immediate fixes it must resolve:

1. **Coder Academy dates:** 2021–2022 vs Jun 2022–Mar 2024 appear on different CVs. Pick the true one; propagate to LinkedIn, GitHub profile, all CVs.
2. **The five anonymous clients:** each one gets reclassified honestly. Anything that was a portfolio build gets relabelled `Independent Data Product` with its public repo linked. The plate project becomes *"Plate-Value Intelligence — Personalised Registration Plate Valuation & Auction Strategy (public project, UK DVLA auction data)"* — the title your friend correctly said it should have had.
3. **The AUC-ROC 1.0000 in the portfolio PDF:** remove or correct. A perfect score reads as either an error or a leak; both destroy trust with a technical reviewer. Report honest error metrics with segment breakdowns.

---

## Phase 1 — Data strategy (Week 1)

The friend's list of what the project must contain (make, model, year, variant, odometer, location, condition, dealer/private split, depreciation, residual value, AUD) drives the source selection.

### Core listings data (historical base)
- **Australian Vehicle Prices dataset** (~16,700 Australian listings): Brand, Model, Year, New/Used, Transmission, Engine, DriveType, FuelType, Kilometres, Location, BodyType, Doors, Seats, Price (AUD). Hosted on Kaggle but the *origin* is Australian marketplace listings — this satisfies the "Australian used-car market" requirement your UK plate data couldn't.
- **Australia Car Market dataset** (second public AU listings set) as a secondary source — combining two sources is itself a selling point ("extract, clean and combine data from a range of internal and external sources").

### Live, refreshing sources (this is what makes it *operated*, not archived)
- **NSW FuelCheck API** — genuinely open government API, real-time fuel prices. Directly evidences the "APIs or external data sources" criterion and gives the market-monitor page live data.
- **Queensland vehicle registration open data (data.qld.gov.au)** — current new-registration and
  transfer activity by make/model. It must not be labelled as total fleet composition.
- **BITRE Road Vehicles Australia** (annual national fleet report, successor to the ABS Motor Vehicle Census) — fleet age and composition context.
- **RBA statistical tables** — G1 CPI for real-AUD context and F1 cash-rate history.

### Compliance rule (non-negotiable)
No scraping of carsales, Gumtree, Drive, or any ToS-protected marketplace. Interviewing at carsales with a repo that scrapes carsales is an auto-reject. Document this decision in the README — it *demonstrates judgement*, which is itself a hiring signal for a data-services company.

### Data quality layer (the ad asks for it explicitly)
- Deduplication rules (same vehicle listed twice across sources), outlier handling (documented, not silent), missing-value policy per column.
- Validation as code: dbt tests or Great Expectations suites, run in CI on every refresh.
- A visible **Data Quality page** in the dashboard: row counts, freshness, failed-test log. RedBook sells data reliability; showing you think in those terms is worth more than another model.

### Known limitation — document, don't hide
Public listings data lacks true `condition` and `variant` granularity. State this openly in the README, proxy what you can (age × odometer interaction, engine/badge parsing from model strings), and show wider prediction intervals where uncertainty is higher. Honest limitation-handling is a differentiator, not a weakness.

---

## Phase 2 — Database & pipeline architecture (Weeks 1–2)

- **Snowflake for production**, with PostgreSQL retained as a secretless local/PR compatibility backend. This adds warehouse governance, managed-access RBAC and real cloud-warehouse CI evidence while preserving the Postgres signal named in the ad.
- Layered model: `raw` → `staging` → `core`/`marts`, with a **Kimball star schema** in core: `fact_listing`, `dim_vehicle` (make/model/variant/body/fuel/transmission), `dim_location`, `dim_year`. Listing observation time remains the fact's snapshot date.
- **dbt** for transformations + tests; lineage graph in the docs.
- **Orchestration: GitHub Actions on a monthly schedule** (plus on-demand). Airflow is overkill here and GitHub Actions doubles as your "modern development workflows including GitHub" evidence: PRs, protected main, CI running dbt tests, tagged releases.
- Every monthly refresh produces a **changelog entry**: rows ingested, tests passed/failed, model metrics on new data. Twelve weeks in, this changelog is your proof of operation.

---

## Phase 3 — Valuation & residual value modelling (Weeks 2–3)

1. **Hedonic pricing model** on log(price): regularised linear baseline → LightGBM. Features: make, model, badge/variant proxy, year/age, odometer, body, fuel, transmission, drivetrain, location, age×km interaction.
2. **Depreciation curves by segment**: price retention vs age for the major make/model groups. Visual, intuitive, and the single most RedBook-shaped artefact in the project.
3. **Residual value estimates**: predicted 3-year retained-value % by model group, with uncertainty bands. This directly fills the "residual value / depreciation" gap your friend identified as fatal in the plate project.
4. **Explainability**: SHAP global + per-valuation. Mirrors the explainability story you built for Plate-Value Intelligence — continuity across projects is a good narrative.
5. **Honest evaluation**: MAE and MdAPE overall *and by segment* (cheap cars vs premium, high-km vs low-km), out-of-time validation split, calibration of prediction intervals. No perfect scores anywhere. Write one paragraph in the README on why out-of-time splits matter for pricing — that paragraph is interview gold.

---

## Phase 4 — Data products (Weeks 3–4)

The ad's core sentence: *"Build and own dashboards and data products end-to-end."* Build two surfaces:

### A. Dashboard (Streamlit, live URL)
1. **Instant Valuation** — select make/model/year/km/location → predicted retail range + confidence band + SHAP-based "why".
2. **Depreciation Explorer** — retention curves, compare models side by side.
3. **Market Monitor** — fleet composition trends (QLD rego data), fuel price context (FuelCheck live), real vs nominal price movements.
4. **Data Quality & Pipeline Health** — freshness, test results, refresh history.

### B. Valuation API (FastAPI)
`POST /valuation` with vehicle parameters → point estimate + range + drivers. Auto-generated OpenAPI docs. This deliberately mirrors the shape of RedBook's commercial valuation APIs — you're demonstrating you understand *their product category*, not just modelling.

---

## Phase 5 — AI-assisted delivery evidence (continuous)

Your friend scored this criterion 1/10 on the current CV, and the ad is unusually explicit about it. You genuinely work this way — the gap is documentation, so document it:

- `docs/AI_DELIVERY_LOG.md`: per-PR notes — what Claude Code / Copilot generated (tests, refactors, dbt models, docstrings), what you reviewed/corrected, estimated time saved.
- PR descriptions tagged `AI-assisted:` with one line of specifics.
- A README section: "How AI-assisted workflows shaped delivery" — honest and specific. Quantify time saved only when it was actually measured.

CV bullet this unlocks: *"Ran an AI-assisted development workflow (Claude Code, GitHub Copilot) with per-PR documentation of generated tests and refactors, materially reducing delivery time — process documented publicly in the repo."*

---

## Phase 6 — Operation & verification (ongoing, minimum 3 months)

This phase **is** the project. It's what separates you from every candidate with an archived repo, and it directly implements your existing strategy (live-operated lakehouse, MCP gateway, A/B testing projects all specified as kept-live).

- Monthly refresh runs on schedule; changelog grows.
- **Model monitoring page**: monthly MAE on fresh data, drift indicators, retrain decisions logged.
- **Documented UAT**: recruit 3–5 real users (friends shopping for cars, community contacts). They file GitHub issues; you ship fixes; the issue → PR → release trail is public. This answers every question in your friend's section 7 (who used it, what changed after feedback, what was the support process).
- Uptime + a `STATUS.md` or badge.

---

## Phase 7 — CV & narrative integration

### CV restructure
Replace the five anonymous clients with a section titled **`INDEPENDENT DATA PRODUCTS — public & live-operated`** containing 2–3 flagship entries (AutoLens AU lead, Plate-Value Intelligence honestly retitled, one more). Real employment (Australian Intercultural Society, Star Community) stays as employment. Every date sourced from the Truth Sheet.

### AutoLens AU headline entry (future template; do not publish before verification)
> **AutoLens AU — Australian Vehicle Pricing & Residual Value Platform** · Independent public data product, live since [month] 2026 · github.com/ozzy2438/autolens-au · [demo URL]
> - Designed, built and operate an end-to-end Australian used-vehicle pricing product: Snowflake + dbt pipeline (managed RBAC, Kimball star schema) combining ~17k AU listings with live government sources (NSW FuelCheck API, QLD registration data), refreshed monthly via GitHub Actions with automated data-quality tests.
> - Hedonic valuation model (LightGBM, SHAP explainability) with segment-level MAE/MdAPE reporting, depreciation curves and 3-year residual-value estimates by model group; out-of-time validation.
> - Shipped a 4-page Streamlit dashboard and a RedBook-style FastAPI valuation endpoint; documented UAT with external users and public model-monitoring/changelog trail.
> - AI-assisted delivery workflow (Claude Code, Copilot) documented per-PR in the repo.

### Interview story (one arc, VicRoads lessons applied)
Context ("I was rejected by carsales for lacking automotive-domain evidence — so I built the evidence, publicly") → role ("I own every layer; here's what that means operationally") → decisions ("why Snowflake production plus Postgres compatibility, why no scraping, why out-of-time splits") → outcome ("live for N months, N refresh cycles, N external users, here's what their feedback changed"). The rejection-to-build story, told straight, reads as exactly the resourceful, low-drama contractor they want. Honesty here is not the safe option — it's the *impressive* option.

---

## Phase 8 — Where to aim it

- **carsales/RedBook**: after ~6–8 weeks of live operation, have your friend ask the manager the exact question your friend drafted ("was the main gap direct automotive experience, or the consulting background?"). Then apply to the next relevant opening with the new CV — carsales posts data roles regularly.
- **Same ecosystem, same project pays off**: AutoGrab (AU vehicle valuation APIs — near-perfect fit), Cox Automotive Australia / Manheim, Pickles, Datium Insights, carma, Eagers Automotive, asset finance (Angle Auto Finance, Metro Finance, Allied Credit), motor insurers (Suncorp, IAG — vehicle total-loss valuation teams).

---

## Timeline & effort

| Week | Focus | Output |
|---|---|---|
| 0 (1 day) | Truth Sheet + date fixes | Single source of career truth |
| 1 | Data acquisition, Snowflake/Postgres compatibility, staging models | Raw + staged data, repo scaffolded, CI running |
| 2 | Star schema, dbt tests, GitHub Actions refresh | Working pipeline with quality gates |
| 3 | Valuation model, depreciation, residual value | Evaluated models, honest metrics |
| 4 | Dashboard + API, deploy | Live URLs |
| 5 | Monitoring, UAT recruitment, AI delivery log polish, CV rewrite | Operating product + new CV |
| 6–14 | Operate: monthly refreshes, user feedback, changelog | Verifiable operational history |

~15–20 hrs/week for weeks 1–5; ~2–3 hrs/month thereafter.

## Definition of done
- [ ] Live dashboard + API URLs, ≥3 monthly refresh cycles logged
- [ ] All metrics honest, segmented, out-of-time validated; zero perfect scores anywhere in the portfolio
- [ ] AI delivery log with ≥10 documented PRs
- [ ] ≥3 external UAT users with public issue→fix trail
- [ ] CV, LinkedIn, GitHub, Truth Sheet fully consistent (dates included)
- [ ] README states "independent public project" in the first paragraph
