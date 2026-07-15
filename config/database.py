"""Lazy database connection and session management."""

from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from config.settings import db_config


@lru_cache(maxsize=4)
def get_engine(database_url: str | None = None) -> Engine:
    """Create and cache an engine only when database access is requested."""
    return create_engine(
        database_url or db_config.url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=False,
    )


def clear_engine_cache() -> None:
    """Clear cached engines; primarily useful when tests change database URLs."""
    get_engine.cache_clear()


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
