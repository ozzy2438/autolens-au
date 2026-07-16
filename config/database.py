"""Lazy database connection and session management."""

from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from config.settings import db_config


def _snowflake_private_key() -> bytes | None:
    """Return a Snowflake-compatible DER key without persisting secret material."""
    key_data: bytes | None = None
    if db_config.snowflake_private_key:
        key_data = db_config.snowflake_private_key.replace("\\n", "\n").encode()
    elif db_config.snowflake_private_key_path:
        key_data = Path(db_config.snowflake_private_key_path).expanduser().read_bytes()

    if key_data is None:
        return None

    passphrase = (
        db_config.snowflake_private_key_passphrase.encode()
        if db_config.snowflake_private_key_passphrase
        else None
    )
    private_key = serialization.load_pem_private_key(key_data, password=passphrase)
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _snowflake_connection() -> tuple[Any, dict[str, Any]]:
    """Build a key-pair-first Snowflake URL and connector arguments."""
    if not db_config.snowflake_account or not db_config.snowflake_user:
        raise ValueError("SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER are required")

    url_parameters: dict[str, str] = {
        "account": db_config.snowflake_account,
        "user": db_config.snowflake_user,
        "database": db_config.snowflake_database,
        "schema": db_config.snowflake_schema,
        "warehouse": db_config.snowflake_warehouse,
        "role": db_config.snowflake_role,
    }
    private_key = _snowflake_private_key()
    connect_args: dict[str, Any] = {
        "session_parameters": {"QUERY_TAG": db_config.snowflake_query_tag}
    }
    if private_key is not None:
        connect_args["private_key"] = private_key
    elif db_config.snowflake_password:
        url_parameters["password"] = db_config.snowflake_password
    else:
        raise ValueError(
            "SNOWFLAKE_PRIVATE_KEY, SNOWFLAKE_PRIVATE_KEY_PATH, or SNOWFLAKE_PASSWORD is required"
        )
    return URL(**url_parameters), connect_args


@lru_cache(maxsize=4)
def get_engine(database_url: str | None = None) -> Engine:
    """Create and cache an engine only when database access is requested."""
    connect_args: dict[str, Any] = {}
    target: Any = database_url or db_config.url
    if database_url is None and db_config.resolved_backend == "snowflake":
        target, connect_args = _snowflake_connection()

    return create_engine(
        target,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=False,
        connect_args=connect_args,
    )


def clear_engine_cache() -> None:
    """Clear cached engines; primarily useful when tests change database URLs."""
    get_engine.cache_clear()


def ensure_raw_schema(connection: Connection) -> None:
    """Create the raw schema on backends whose runtime role owns schema setup.

    Snowflake schemas are provisioned by ``infra/snowflake/bootstrap.sql`` and the
    runtime roles deliberately hold no CREATE SCHEMA privilege, so creation is
    skipped there.
    """
    if connection.dialect.name == "snowflake":
        return
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=get_engine(),
    )
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_connection(database_url: str | None = None) -> bool:
    """Return whether the configured database accepts a simple query."""
    try:
        with get_engine(database_url).connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
