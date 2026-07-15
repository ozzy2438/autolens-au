"""Integration tests for the full pipeline."""

import os

import pandas as pd
import pytest
from sqlalchemy import text

HAS_TEST_DATABASE = bool(os.getenv("DATABASE_URL"))


class TestPipelineIntegration:
    """End-to-end pipeline tests (require database connection)."""

    @pytest.mark.skipif(
        not HAS_TEST_DATABASE,
        reason="No DATABASE_URL — skip database integration tests",
    )
    def test_database_connection(self):
        """Database should be reachable."""
        from config.database import test_connection

        assert test_connection() is True

    @pytest.mark.skipif(
        not HAS_TEST_DATABASE,
        reason="No DATABASE_URL — skip database integration tests",
    )
    def test_schema_setup(self):
        """Database schemas should be creatable."""
        from sqlalchemy import text

        from config.database import get_engine

        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
            conn.commit()

    @pytest.mark.skipif(
        not HAS_TEST_DATABASE,
        reason="No DATABASE_URL — skip database integration tests",
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
