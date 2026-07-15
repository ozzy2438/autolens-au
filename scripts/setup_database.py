"""Database setup script.

Creates the PostgreSQL schemas and tables required for AutoLens AU.
Schemas: raw, staging, core
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


SCHEMA_SQL = """
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
        for statement in _sql_statements(SCHEMA_SQL):
            conn.execute(text(statement))
        conn.commit()

    logger.info("Database setup complete!")
    logger.info("Schemas created: raw, staging, core")
    logger.info("Raw tables created for listings, fuel, QLD activity, CPI, RBA rates and BITRE")


if __name__ == "__main__":
    setup_database()
