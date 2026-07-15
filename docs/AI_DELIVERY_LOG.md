# AutoLens AU — AI-Assisted Delivery Log

> This document records how AI tools (Claude Code, GitHub Copilot) contributed
> to the development of AutoLens AU. Each entry links to a specific PR or commit
> and describes what was generated, what was reviewed/corrected, and estimated
> time savings.

## Summary

| Metric | Value |
|--------|-------|
| Total PRs with AI assistance | 10+ (ongoing) |
| Estimated time saved | ~40% of development hours |
| Primary tools | Claude Code, GitHub Copilot |
| Quality gate | All AI output reviewed, tested, and validated |

---

## Log Entries

### Entry 001 — Project Scaffolding
- **Date:** 2026-07-15
- **PR/Commit:** Initial infrastructure commit
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
- **PR/Commit:** dbt project setup
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
- **PR/Commit:** API implementation
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
- **PR/Commit:** Unit test infrastructure
- **AI Tool:** GitHub Copilot
- **What was generated:**
  - Test file structure and fixtures
  - Basic assertion patterns for model evaluation
  - pytest configuration
- **What was reviewed/corrected:**
  - Added domain-specific test cases (Australian price ranges)
  - Fixed edge cases in depreciation curve tests
  - Added integration test scenarios
- **Time saved:** ~5 hours (test suite ~1h vs estimated ~1 day manual)

### Entry 005 — Streamlit Dashboard Pages
- **Date:** 2026-07-15
- **PR/Commit:** Dashboard implementation
- **AI Tool:** Claude Code
- **What was generated:**
  - Multi-page Streamlit structure
  - Plotly chart component library
  - Data Quality monitoring page layout
- **What was reviewed/corrected:**
  - Customised colour scheme and layout for vehicle pricing context
  - Added proper placeholder data representing Australian market
  - Refined user interaction flows
- **Time saved:** ~3 hours

---

## How This Workflow Operates

1. **Task Scoping**: Define what needs to be built (human decision)
2. **AI Generation**: Use Claude Code or Copilot for initial code generation
3. **Review & Correct**: Every line reviewed; domain logic verified
4. **Test**: AI output must pass existing test suite
5. **Document**: This log entry created
6. **Commit**: Tagged PR description notes AI assistance

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
