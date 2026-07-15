"""Integration tests for the full pipeline."""

import pytest
from pathlib import Path


class TestPipelineIntegration:
    """End-to-end pipeline tests (require database connection)."""
    
    @pytest.mark.skipif(
        not Path(".env").exists(),
        reason="No .env file — skip integration tests"
    )
    def test_database_connection(self):
        """Database should be reachable."""
        from config.database import test_connection
        assert test_connection() is True
    
    @pytest.mark.skipif(
        not Path(".env").exists(),
        reason="No .env file — skip integration tests"
    )
    def test_schema_setup(self):
        """Database schemas should be creatable."""
        from config.database import get_engine
        from sqlalchemy import text
        
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
