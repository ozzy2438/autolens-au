# AutoLens AU — Development Commands
.PHONY: help install dev requirements requirements-check test lint format run-api run-dashboard pipeline dbt-run dbt-test setup-db

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	uv sync --frozen

dev: ## Install development dependencies
	uv sync --frozen --extra dev --extra dbt
	pre-commit install

requirements: ## Export Streamlit Cloud dependencies from uv.lock
	uv export --frozen --no-dev --no-hashes --no-emit-project --no-header --output-file requirements.txt

requirements-check: ## Verify requirements.txt matches uv.lock
	@tmp=$$(mktemp); trap 'rm -f "$$tmp"' EXIT; \
	uv export --frozen --no-dev --no-hashes --no-emit-project --no-header --output-file "$$tmp" >/dev/null; \
	diff -u requirements.txt "$$tmp"

test: ## Run test suite
	pytest tests/ -v --cov=src --cov-report=term-missing

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-integration: ## Run integration tests
	pytest tests/integration/ -v

lint: ## Run linters
	ruff format --check src/ config/ scripts/ tests/
	ruff check src/ config/ scripts/ tests/
	mypy src/ config/ scripts/

format: ## Format code
	ruff format src/ config/ scripts/ tests/
	ruff check --fix src/ config/ scripts/ tests/

run-api: ## Start FastAPI server
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

run-dashboard: ## Start Streamlit dashboard
	streamlit run src/dashboard/app.py

pipeline: ## Run full data pipeline
	python scripts/run_pipeline.py

dbt-run: ## Run dbt models
	cd dbt_autolens && dbt run

dbt-test: ## Run dbt tests
	cd dbt_autolens && dbt test

dbt-build: ## Build models and run all dbt tests
	cd dbt_autolens && dbt build

dbt-docs: ## Generate dbt documentation
	cd dbt_autolens && dbt docs generate && dbt docs serve

setup-db: ## Initialize database schema
	python scripts/setup_database.py

train: ## Train valuation model
	python scripts/train_model.py

refresh: ## Run monthly refresh (pipeline + retrain if needed)
	python scripts/run_pipeline.py --monthly-refresh
	python scripts/train_model.py --check-drift

clean: ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage
	rm -rf dbt_autolens/target dbt_autolens/logs
