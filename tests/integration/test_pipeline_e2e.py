"""Integration tests for the full pipeline."""

import os

import pytest

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
