"""Tests for dual PostgreSQL/Snowflake database configuration."""

from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from config.database import (
    _snowflake_private_key,
    ensure_raw_schema,
    stringify_temporal_columns,
    write_dataframe,
)
from config.settings import DatabaseConfig, db_config
from scripts.setup_database import POSTGRES_SCHEMA_SQL, SNOWFLAKE_SCHEMA_SQL, schema_sql_for


def test_database_backend_defaults_to_postgresql(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_BACKEND", raising=False)
    monkeypatch.delenv("SNOWFLAKE_ACCOUNT", raising=False)

    assert DatabaseConfig().resolved_backend == "postgresql"


def test_database_backend_is_inferred_from_snowflake_account(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_BACKEND", raising=False)
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "example-account")

    assert DatabaseConfig().resolved_backend == "snowflake"


def test_private_key_environment_accepts_escaped_newlines(monkeypatch) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    monkeypatch.setattr(db_config, "snowflake_private_key", pem.replace("\n", "\\n"))
    monkeypatch.setattr(db_config, "snowflake_private_key_path", "")
    monkeypatch.setattr(db_config, "snowflake_private_key_passphrase", "")

    der = _snowflake_private_key()

    assert der is not None
    serialization.load_der_private_key(der, password=None)


def test_setup_ddl_is_selected_by_database_dialect() -> None:
    assert schema_sql_for("postgresql") == POSTGRES_SCHEMA_SQL
    assert schema_sql_for("snowflake") == SNOWFLAKE_SCHEMA_SQL


class _RecordingConnection:
    """Minimal stand-in exposing the dialect name and executed statements."""

    def __init__(self, dialect_name: str) -> None:
        self.dialect = SimpleNamespace(name=dialect_name)
        self.statements: list[str] = []

    def execute(self, statement) -> None:
        self.statements.append(str(statement))


def test_ensure_raw_schema_creates_schema_on_postgresql() -> None:
    connection = _RecordingConnection("postgresql")

    ensure_raw_schema(connection)

    assert connection.statements == ["CREATE SCHEMA IF NOT EXISTS raw"]


def test_ensure_raw_schema_is_skipped_on_snowflake() -> None:
    connection = _RecordingConnection("snowflake")

    ensure_raw_schema(connection)

    assert connection.statements == []


def test_stringify_temporal_columns_renders_dates_and_datetimes():
    frame = pd.DataFrame(
        {
            "snapshot_date": [date(2026, 7, 1)],
            "ingested_at": [pd.Timestamp("2026-07-01T00:00:00Z")],
            "price": [35000],
            "brand": ["Toyota"],
        }
    )

    result = stringify_temporal_columns(frame)

    assert result["snapshot_date"].iloc[0] == "2026-07-01"
    assert result["ingested_at"].iloc[0].startswith("2026-07-01")
    # Non-temporal columns are untouched.
    assert result["price"].iloc[0] == 35000
    assert result["brand"].iloc[0] == "Toyota"


def test_write_dataframe_postgresql_uses_requested_mode_and_reindex(monkeypatch):
    calls: list[dict] = []

    def fake_to_sql(self, name, con, **kwargs):
        calls.append({"name": name, "columns": list(self.columns), "kwargs": kwargs})
        return len(self)

    monkeypatch.setattr(pd.DataFrame, "to_sql", fake_to_sql, raising=True)
    frame = pd.DataFrame({"brand": ["Toyota"], "dropped": ["x"]})
    engine = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    rows = write_dataframe(
        frame, "raw_fuel_prices", mode="replace", columns=["brand", "missing"], engine=engine
    )

    assert rows == 1
    assert calls[-1]["name"] == "raw_fuel_prices"
    assert calls[-1]["kwargs"]["if_exists"] == "replace"
    # Reindex drops source drift and adds the declared-but-absent column.
    assert calls[-1]["columns"] == ["brand", "missing"]


def test_write_dataframe_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported write mode"):
        write_dataframe(pd.DataFrame({"a": [1]}), "raw_x", mode="upsert")


def test_write_dataframe_empty_frame_is_a_noop():
    assert write_dataframe(pd.DataFrame({"a": []}), "raw_x", mode="append") == 0
