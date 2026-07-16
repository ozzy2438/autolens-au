# AutoLens AU — AI-Assisted Delivery Log

> This document records how AI tools (Claude Code, GitHub Copilot) contributed
> to the development of AutoLens AU. Each entry links to a specific PR or commit
> and describes what was generated, what was reviewed/corrected, and estimated
> time savings.

## Summary

| Metric | Value |
|--------|-------|
| Total PRs with AI assistance | 4 (3 merged, 1 active Snowflake platform PR) |
| Initial delivery units | 8 direct-to-main commits |
| Estimated time saved | Not independently measured |
| Primary tools | Claude Code, GitHub Copilot, OpenAI Codex |
| Quality gate | Blocking Ruff, mypy, pytest and seed-backed dbt build |

The entries below are retrospective disclosures for direct commits, not PR records. Their original
time-saved figures are self-reported estimates. CI was failing and the product had not completed a
data refresh or model training run when this audit began.

---

## Log Entries

### Entry 001 — Project Scaffolding
- **Date:** 2026-07-15
- **Commit:** `b56a8a7`
- **AI Tool:** Claude Code
- **What was generated:**
  - Project directory structure
  - pyproject.toml with dependencies
  - Makefile with common commands
  - .gitignore comprehensive rules
  - GitHub Actions workflow templates
- **What was reviewed/corrected:**
  - Adjusted dependency versions to latest stable
  - Customised GitHub Actions to match Neon Postgres setup
  - Added project-specific paths and configurations
- **Time saved:** ~3 hours (boilerplate generation)

### Entry 002 — dbt Model Generation
- **Date:** 2026-07-15
- **Commit:** `9467bd5`
- **AI Tool:** Claude Code
- **What was generated:**
  - Staging model SQL (stg_listings, stg_fuel_prices, stg_qld_registrations)
  - Core dimension models (dim_vehicle, dim_location, dim_date)
  - schema.yml with test definitions
- **What was reviewed/corrected:**
  - Adjusted column types for actual Kaggle data schema
  - Fixed location extraction regex for Australian state codes
  - Added vehicle_segment classification logic (domain knowledge)
- **Time saved:** ~4 hours (SQL boilerplate + schema documentation)

### Entry 003 — FastAPI Endpoint Scaffolding
- **Date:** 2026-07-15
- **Commit:** `86a9cd2`
- **AI Tool:** Claude Code + Copilot
- **What was generated:**
  - Pydantic schemas (request/response models)
  - FastAPI app structure with lifespan management
  - OpenAPI documentation metadata
- **What was reviewed/corrected:**
  - Refined validation rules (Australian-specific constraints)
  - Added proper error handling for model-not-loaded state
  - Customised example values for Australian vehicles
- **Time saved:** ~2 hours

### Entry 004 — Test Suite Scaffolding
- **Date:** 2026-07-15
- **Commit:** `9c59399`
- **AI Tool:** GitHub Copilot
- **What was generated:**
  - Test file structure and fixtures
  - Basic assertion patterns for model evaluation
  - pytest configuration
- **What was reviewed/corrected:**
  - Added domain-specific test cases (Australian price ranges)
  - Added depreciation edge-case coverage; one retention baseline test still failed at audit time
  - Added integration test scenarios
- **Time saved:** ~5 hours (test suite ~1h vs estimated ~1 day manual)

### Entry 005 — Streamlit Dashboard Pages
- **Date:** 2026-07-15
- **Commit:** `86a9cd2`
- **AI Tool:** Claude Code
- **What was generated:**
  - Multi-page Streamlit structure
  - Plotly chart component library
  - Data Quality monitoring page layout
- **What was reviewed/corrected:**
  - Customised colour scheme and layout for vehicle pricing context
  - Added placeholder market data for layout development; it was removed from user-facing output
    during audit remediation because it could be mistaken for observed data
  - Refined user interaction flows
- **Time saved:** ~3 hours

### Entry 006 — Senior Audit Remediation
- **Date:** 2026-07-15
- **PR:** [#1](https://github.com/ozzy2438/autolens-au/pull/1)
- **AI Tool:** OpenAI Codex
- **What was generated:**
  - Honest pre-launch status and removal of synthetic dashboard/model claims
  - Blocking CI/dbt gates, canonical source loaders and append-only snapshots
  - Calibrated model bundle, TreeSHAP integration and snapshot-aware drift workflow
  - DB/artifact-backed Streamlit products and measured monthly delivery workflows
- **What was reviewed/corrected:**
  - Live source schemas were tested against current QLD, BITRE and RBA publications
  - QLD `RECORD_DATE` type differences and BITRE comma-formatted counts were found in live checks
    and corrected before commit
  - Every pushed delivery unit was followed through GitHub Actions; environment-only mypy failures
    were fixed in follow-up commits rather than ignored
  - Production/UAT/calendar claims remain explicitly blocked until their evidence exists
- **Time saved:** Not independently measured; no numeric saving is claimed

### Entry 007 — Deployment Evidence Follow-up
- **Date:** 2026-07-15
- **PR:** [#2](https://github.com/ozzy2438/autolens-au/pull/2)
- **AI Tool:** OpenAI Codex
- **What was generated:**
  - GitHub Release-backed Streamlit model/metrics retrieval with digest verification
  - Deterministic `uv.lock` → `requirements.txt` export and blocking CI drift check
  - Scheduled API/dashboard point-in-time health workflow and JSON evidence
- **What was reviewed/corrected:**
  - GitHub's `latest` endpoint excludes prereleases, so model releases are selected from the
    release list by the workflow's `model-*` tag contract
  - Partial/corrupt release pairs are rejected before either destination is replaced
  - Unconfigured endpoints record `not_configured` and never imply an uptime percentage
- **Time saved:** Not independently measured; no numeric saving is claimed

### Entry 008 — Container Delivery Preflight
- **Date:** 2026-07-15
- **PR:** [#3](https://github.com/ozzy2438/autolens-au/pull/3)
- **AI Tool:** OpenAI Codex
- **What was generated:**
  - A model-release preflight gate separated from the GHCR publish job
  - An explicit job summary when calibrated artifacts are not yet available
- **What was reviewed/corrected:**
  - The original fail-closed gate correctly prevented an invalid image but marked every pre-model
    main build red; the new gate keeps publishing blocked while treating the absent prerequisite as
    an intentional skip rather than a delivery failure
- **Time saved:** Not independently measured; no numeric saving is claimed

### Entry 009 — Snowflake Platform Provisioning
- **Date:** 2026-07-15
- **PR:** [#4](https://github.com/ozzy2438/autolens-au/pull/4)
- **AI Tool:** OpenAI Codex
- **What was generated:**
  - Idempotent Snowflake warehouse/database/managed-schema bootstrap and least-privilege role tree
  - Key-pair SQLAlchemy and dbt integrations for pipeline, CI, Streamlit and FastAPI runtimes
  - Isolated Snowflake CI build plus production Monthly Refresh configuration
  - Snowflake permission, secret, deployment and key-rotation runbook
- **What was reviewed/corrected:**
  - Every positive and negative permission boundary was executed with secondary roles disabled
  - Separate CI and pipeline service keys replaced human `ACCOUNTADMIN` workflow access
  - PostgreSQL remains as the secretless/fork-safe PR compatibility gate
  - The real Snowflake build loaded 6 seeds and passed 47/47 models and tests before publication
  - Repository history and tracked files were scanned to confirm no supplied credential was stored
- **Time saved:** Not independently measured; no numeric saving is claimed

### Entry 010 — Snowflake Listing Upsert Compatibility
- **Date:** 2026-07-16
- **PR:** fix/snowflake-listing-upsert
- **AI Tool:** Claude Code
- **What was generated:**
  - Dialect-aware `raw_listings` upsert statement builder (Snowflake `LIKE`, alias-free `DELETE`,
    unquoted identifiers, no index; PostgreSQL behaviour unchanged)
  - Shared `ensure_raw_schema` helper that skips `CREATE SCHEMA` on Snowflake, where schemas are
    bootstrap-owned and runtime roles hold no schema-creation privilege
  - Unit tests asserting the emitted SQL per dialect and the schema-creation guard
- **What was reviewed/corrected:**
  - Confirmed the PR #4 validation had exercised direct writes but not this loader path, which
    still emitted PostgreSQL-only DDL and would have failed the first credentialled refresh
  - Verified quoting semantics: unquoted lowercase identifiers resolve to uppercase on Snowflake,
    so the Snowflake branch emits unquoted column lists
- **Time saved:** Not independently measured; no numeric saving is claimed

### Entry 011 — Snowflake Cost Guardrail and Decision Record
- **Date:** 2026-07-16
- **PR:** infra/snowflake-resource-monitor
- **AI Tool:** Claude Code
- **What was generated:**
  - Idempotent `AUTOLENS_MONITOR` resource-monitor SQL bound to `AUTOLENS_WH` with
    notify/suspend triggers and a documented default credit quota
  - SNOWFLAKE.md operating section for applying and tuning the monitor
  - README "Why Snowflake" decision record framing the PostgreSQL-compatible /
    Snowflake-operated architecture honestly, including the non-zero operating cost
- **What was reviewed/corrected:**
  - Kept the credit ceiling out of the access-control bootstrap so budget and RBAC
    stay separate and independently reviewable
  - Corrected the residual "$0 operating cost" framing now that a warehouse is billed
- **Time saved:** Not independently measured; no numeric saving is claimed
### Entry 012 — Snowflake Ingestion Write Path
- **Date:** 2026-07-16
- **PR:** fix/snowflake-pandas-write
- **AI Tool:** Claude Code
- **What was generated:**
  - `write_dataframe` / `stringify_temporal_columns` helpers making the raw writes Snowflake-safe:
    the four context loaders go through `write_dataframe` (ISO strings + truncate-and-append into
    pre-typed tables); the listings loader reuses the same temporal-stringify helper to stage its
    own append-only upsert batch
  - Required/best-effort source policy so a government-source outage degrades rather than blocks
  - `scripts/check_snowflake_ingest.py` plus a CI step that runs the real pandas -> Snowflake write
    against AUTOLENS_AU_CI, and unit tests for the write dispatch, temporal stringify and policy
- **What was reviewed/corrected:**
  - Diagnosed the first credentialled refresh failing at listing load with
    `Binding data in type (timestamp) is not supported`; confirmed dbt seeds never exercised this path
  - Preserved PostgreSQL behaviour and the pre-created Snowflake DDL types by truncating on replace
- **Time saved:** Not independently measured; no numeric saving is claimed

### Entry 013 — Context-Source Fixes and Streamlit-First Deployment
- **Date:** 2026-07-16
- **PR:** fix/context-source-resilience
- **AI Tool:** Claude Code
- **What was generated:**
  - String-normalised NSW FuelCheck price/station merge (reproduced the live ValueError locally
    before fixing; verified 10,591 real price rows after)
  - Retry/backoff and granular timeouts for the BITRE workbook download (verified live: 93 makes)
  - Dashboard entry-script bootstrap (sys.path + st.secrets->environment bridge), the
    `AUTOLENS_APP_SVC` service-user SQL template, and the Streamlit Cloud deployment guide
- **What was reviewed/corrected:**
  - Confirmed both first-refresh source failures root-caused from run logs, not guessed
  - Key material generated locally only; never committed — the repo carries a placeholder template
- **Time saved:** Not independently measured; no numeric saving is claimed


---

## How This Workflow Operates

1. **Task Scoping**: Define what needs to be built (human decision)
2. **AI Generation**: Use Claude Code or Copilot for initial code generation
3. **Review & Correct**: Every line reviewed; domain logic verified
4. **Test**: AI output must pass local and GitHub Actions quality gates before merge
5. **Document**: This log entry created
6. **Commit**: PR description and this log identify the assistance and human corrections

## What AI Does Well Here
- Boilerplate generation (project structure, configs)
- SQL template creation (dbt models, schema definitions)
- API scaffolding (FastAPI routes, Pydantic models)
- Test skeleton creation
- Documentation formatting

## What Requires Human Expertise
- Domain logic (vehicle pricing, depreciation models)
- Data quality rules (what constitutes an outlier in AU market)
- Architecture decisions (why Kimball, why not scraping)
- Evaluation methodology (out-of-time splits, interval calibration)
- Business context (how RedBook/carsales actually operates)
