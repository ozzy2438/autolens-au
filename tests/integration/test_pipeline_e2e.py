"""Integration tests for the full pipeline."""

import os

import pandas as pd
import pytest
from sqlalchemy import text

HAS_TEST_DATABASE = bool(os.getenv("DATABASE_URL") or os.getenv("SNOWFLAKE_ACCOUNT"))


class TestPipelineIntegration:
    """End-to-end pipeline tests (require database connection)."""

    @pytest.mark.skipif(
        not HAS_TEST_DATABASE,
        reason="No configured test database — skip database integration tests",
    )
    def test_database_connection(self):
        """Database should be reachable."""
        from config.database import test_connection

        assert test_connection() is True

    @pytest.mark.skipif(
        not HAS_TEST_DATABASE,
        reason="No configured test database — skip database integration tests",
    )
    def test_schema_setup(self):
        """Database schemas should be creatable."""
        from sqlalchemy import text

        from config.database import get_engine

        engine = get_engine()
        with engine.connect() as conn:
            if engine.dialect.name == "snowflake":
                schemas = {
                    row[0]
                    for row in conn.execute(
                        text(
                            "SELECT schema_name FROM information_schema.schemata "
                            "WHERE schema_name IN ('RAW', 'STAGING', 'CORE', 'MARTS')"
                        )
                    )
                }
                assert schemas == {"RAW", "STAGING", "CORE", "MARTS"}
            else:
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
            conn.commit()

    @pytest.mark.skipif(
        not HAS_TEST_DATABASE,
        reason="No configured test database — skip database integration tests",
    )
    def test_dashboard_queries_match_source_schema(self):
        """Every read-only dashboard query should execute against the canonical raw schema."""
        from config.database import get_engine
        from scripts.setup_database import _sql_statements, schema_sql_for
        from src.dashboard.data_access import (
            get_bitre_vehicle_makes,
            get_economic_context,
            get_latest_fuel_prices,
            get_listing_catalog,
            get_listing_data,
            get_listing_price_trends,
            get_qld_activity,
            get_source_health,
        )

        engine = get_engine()
        with engine.begin() as connection:
            for statement in _sql_statements(schema_sql_for(engine.dialect.name)):
                connection.execute(text(statement))

        assert len(get_source_health()) == 6
        assert get_listing_catalog().empty
        assert get_listing_data().empty
        assert get_qld_activity().empty
        assert get_bitre_vehicle_makes().empty
        assert get_latest_fuel_prices().empty
        assert all(frame.empty for frame in get_economic_context())
        assert get_listing_price_trends().empty

    @pytest.mark.skipif(
        not HAS_TEST_DATABASE,
        reason="No configured test database — skip database integration tests",
    )
    def test_listing_snapshots_are_idempotent_and_append_only(self):
        """A rerun replaces one snapshot while a later snapshot is retained."""
        from config.database import get_engine
        from src.ingestion.kaggle_loader import add_lineage, load_to_raw_schema

        canonical = pd.DataFrame(
            {
                "brand": ["Toyota"],
                "model": ["Camry"],
                "year": [2020],
                "kilometres": [45000],
                "price": [35000],
            }
        )
        engine = get_engine()
        july = add_lineage(canonical, "integration_test", "2026-07-01")
        august = add_lineage(canonical, "integration_test", "2026-08-01")

        load_to_raw_schema(july, engine=engine)
        load_to_raw_schema(july, engine=engine)
        load_to_raw_schema(august, engine=engine)

        with engine.connect() as connection:
            count = connection.execute(
                text("SELECT count(*) FROM raw.raw_listings WHERE source = 'integration_test'")
            ).scalar_one()
        assert count == 2

    def test_api_health_endpoint(self):
        """API health endpoint should respond."""
        from fastapi.testclient import TestClient

        from src.api.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
