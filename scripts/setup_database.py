"""Database setup script.

Creates the raw tables required for AutoLens AU. PostgreSQL local development
also creates its schemas; Snowflake schemas and grants are account-bootstrap
objects managed by ``infra/snowflake/bootstrap.sql``.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from config.database import get_engine, test_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


POSTGRES_SCHEMA_SQL = """
-- Create schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;

-- Raw layer: raw_listings
CREATE TABLE IF NOT EXISTS raw.raw_listings (
    source_record_id TEXT,
    brand VARCHAR(100),
    year INTEGER,
    model VARCHAR(200),
    variant VARCHAR(200),
    vehicle_type VARCHAR(50),
    title TEXT,
    condition VARCHAR(50),
    transmission VARCHAR(50),
    engine VARCHAR(100),
    drive_type VARCHAR(50),
    fuel_type VARCHAR(50),
    fuel_consumption VARCHAR(50),
    kilometres NUMERIC,
    colour VARCHAR(200),
    location VARCHAR(200),
    cylinders INTEGER,
    body_type VARCHAR(100),
    doors INTEGER,
    seats INTEGER,
    price NUMERIC,
    source VARCHAR(100),
    listing_fingerprint VARCHAR(64),
    snapshot_date DATE,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Raw layer: fuel prices
CREATE TABLE IF NOT EXISTS raw.raw_fuel_prices (
    stationcode VARCHAR(50),
    fueltype VARCHAR(50),
    price NUMERIC,
    lastupdated TIMESTAMP,
    name VARCHAR(200),
    suburb VARCHAR(100),
    state VARCHAR(10),
    latitude NUMERIC,
    longitude NUMERIC,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source VARCHAR(100)
);

-- Raw layer: QLD new-registration and transfer activity
CREATE TABLE IF NOT EXISTS raw.raw_qld_registration_activity (
    activity_month DATE,
    make VARCHAR(100),
    model VARCHAR(200),
    badge VARCHAR(200),
    body_shape VARCHAR(100),
    fuel_type VARCHAR(50),
    transaction_type VARCHAR(50),
    activity_count BIGINT,
    source_resource_id UUID,
    source VARCHAR(100),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Raw layer: CPI data
CREATE TABLE IF NOT EXISTS raw.raw_cpi (
    period VARCHAR(20),
    cpi_index NUMERIC,
    period_date DATE,
    source VARCHAR(50),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Raw layer: RBA cash-rate target
CREATE TABLE IF NOT EXISTS raw.raw_rba_cash_rate (
    period_date DATE,
    cash_rate_target_pct NUMERIC,
    source VARCHAR(50),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Raw layer: BITRE registered vehicles by make
CREATE TABLE IF NOT EXISTS raw.raw_bitre_vehicle_makes (
    make VARCHAR(100),
    reference_year INTEGER,
    registered_vehicles BIGINT,
    source VARCHAR(100),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_listings_brand ON raw.raw_listings(brand);
CREATE INDEX IF NOT EXISTS idx_listings_year ON raw.raw_listings(year);
CREATE INDEX IF NOT EXISTS idx_listings_price ON raw.raw_listings(price);
CREATE UNIQUE INDEX IF NOT EXISTS uq_raw_listings_snapshot
    ON raw.raw_listings(listing_fingerprint, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_fuel_station ON raw.raw_fuel_prices(stationcode);
CREATE INDEX IF NOT EXISTS idx_rego_activity_make
    ON raw.raw_qld_registration_activity(make);
"""

SNOWFLAKE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw.raw_listings (
    source_record_id TEXT,
    brand VARCHAR(100),
    year INTEGER,
    model VARCHAR(200),
    variant VARCHAR(200),
    vehicle_type VARCHAR(50),
    title TEXT,
    condition VARCHAR(50),
    transmission VARCHAR(50),
    engine VARCHAR(100),
    drive_type VARCHAR(50),
    fuel_type VARCHAR(50),
    fuel_consumption VARCHAR(50),
    kilometres NUMERIC,
    colour VARCHAR(200),
    location VARCHAR(200),
    cylinders INTEGER,
    body_type VARCHAR(100),
    doors INTEGER,
    seats INTEGER,
    price NUMERIC,
    source VARCHAR(100),
    listing_fingerprint VARCHAR(64),
    snapshot_date DATE,
    ingested_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS raw.raw_fuel_prices (
    stationcode VARCHAR(50),
    fueltype VARCHAR(50),
    price NUMERIC,
    lastupdated TIMESTAMP_NTZ,
    name VARCHAR(200),
    suburb VARCHAR(100),
    state VARCHAR(10),
    latitude NUMERIC,
    longitude NUMERIC,
    fetched_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    source VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS raw.raw_qld_registration_activity (
    activity_month DATE,
    make VARCHAR(100),
    model VARCHAR(200),
    badge VARCHAR(200),
    body_shape VARCHAR(100),
    fuel_type VARCHAR(50),
    transaction_type VARCHAR(50),
    activity_count BIGINT,
    source_resource_id VARCHAR(36),
    source VARCHAR(100),
    fetched_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS raw.raw_cpi (
    period VARCHAR(20),
    cpi_index NUMERIC,
    period_date DATE,
    source VARCHAR(50),
    fetched_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS raw.raw_rba_cash_rate (
    period_date DATE,
    cash_rate_target_pct NUMERIC,
    source VARCHAR(50),
    fetched_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS raw.raw_bitre_vehicle_makes (
    make VARCHAR(100),
    reference_year INTEGER,
    registered_vehicles BIGINT,
    source VARCHAR(100),
    fetched_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);
"""

# Backwards-compatible constant used by the PostgreSQL integration suite.
SCHEMA_SQL = POSTGRES_SCHEMA_SQL

# Free-text columns are widened to an unbounded string type after creation. The raw
# layer must accept messy source values verbatim (e.g. a dealer name landing in the
# listings "Car/Suv" field) and defer cleaning to staging; a bounded VARCHAR makes
# Snowflake reject the whole load with a truncation error. Applying this as an
# idempotent migration converges tables that were first created with narrow widths.
TEXT_COLUMNS: dict[str, tuple[str, ...]] = {
    "raw_listings": (
        "brand",
        "model",
        "variant",
        "vehicle_type",
        "condition",
        "transmission",
        "engine",
        "drive_type",
        "fuel_type",
        "fuel_consumption",
        "colour",
        "location",
        "body_type",
        "source",
    ),
    "raw_fuel_prices": ("stationcode", "fueltype", "name", "suburb", "state", "source"),
    "raw_qld_registration_activity": (
        "make",
        "model",
        "badge",
        "body_shape",
        "fuel_type",
        "transaction_type",
        "source",
    ),
    "raw_cpi": ("period", "source"),
    "raw_rba_cash_rate": ("source",),
    "raw_bitre_vehicle_makes": ("make", "source"),
}


def widen_text_columns_sql(dialect_name: str) -> list[str]:
    """Return idempotent statements widening raw free-text columns to TEXT."""
    if dialect_name == "snowflake":
        clause = "SET DATA TYPE VARCHAR"  # unbounded (VARCHAR(16777216))
    elif dialect_name == "postgresql":
        clause = "TYPE TEXT"
    else:
        raise ValueError(f"Unsupported database dialect: {dialect_name}")
    return [
        f"ALTER TABLE IF EXISTS raw.{table} ALTER COLUMN {column} {clause}"
        for table, columns in TEXT_COLUMNS.items()
        for column in columns
    ]


def schema_sql_for(dialect_name: str) -> str:
    """Return setup DDL for a supported SQLAlchemy dialect."""
    if dialect_name == "snowflake":
        return SNOWFLAKE_SCHEMA_SQL
    if dialect_name == "postgresql":
        return POSTGRES_SCHEMA_SQL
    raise ValueError(f"Unsupported database dialect: {dialect_name}")


def _sql_statements(script: str) -> list[str]:
    """Split the setup script while retaining statements preceded by comments."""
    statements: list[str] = []
    for chunk in script.split(";"):
        statement = "\n".join(
            line for line in chunk.splitlines() if not line.strip().startswith("--")
        ).strip()
        if statement:
            statements.append(statement)
    return statements


def setup_database():
    """Initialize database schemas and tables."""
    logger.info("Testing database connection...")
    if not test_connection():
        logger.error("Cannot connect to database. Check your .env configuration.")
        sys.exit(1)

    logger.info("Database connection successful. Creating schemas and tables...")

    engine = get_engine()
    with engine.connect() as conn:
        # Execute each statement separately
        for statement in _sql_statements(schema_sql_for(engine.dialect.name)):
            conn.execute(text(statement))
        # Converge free-text columns to an unbounded type (also fixes tables first
        # created with narrow widths).
        for statement in widen_text_columns_sql(engine.dialect.name):
            conn.execute(text(statement))
        conn.commit()

    logger.info("Database setup complete!")
    logger.info("Database backend: %s", engine.dialect.name)
    logger.info("Raw tables created for listings, fuel, QLD activity, CPI, RBA rates and BITRE")


if __name__ == "__main__":
    setup_database()
