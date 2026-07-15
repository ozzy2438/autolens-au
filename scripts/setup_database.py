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
    brand VARCHAR(100),
    year INTEGER,
    model VARCHAR(200),
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

-- Raw layer: QLD registrations
CREATE TABLE IF NOT EXISTS raw.raw_qld_registrations (
    make VARCHAR(100),
    model VARCHAR(200),
    year INTEGER,
    body_type VARCHAR(100),
    fuel_type VARCHAR(50),
    colour VARCHAR(50),
    vehicle_category VARCHAR(100),
    source VARCHAR(100),
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Raw layer: CPI data
CREATE TABLE IF NOT EXISTS raw.raw_cpi (
    period VARCHAR(20),
    cpi_index NUMERIC,
    period_date DATE,
    source VARCHAR(50),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_listings_brand ON raw.raw_listings(brand);
CREATE INDEX IF NOT EXISTS idx_listings_year ON raw.raw_listings(year);
CREATE INDEX IF NOT EXISTS idx_listings_price ON raw.raw_listings(price);
CREATE INDEX IF NOT EXISTS idx_fuel_station ON raw.raw_fuel_prices(stationcode);
CREATE INDEX IF NOT EXISTS idx_rego_make ON raw.raw_qld_registrations(make);
"""


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
        for statement in SCHEMA_SQL.split(";"):
            statement = statement.strip()
            if statement and not statement.startswith("--"):
                conn.execute(text(statement))
        conn.commit()

    logger.info("Database setup complete!")
    logger.info("Schemas created: raw, staging, core")
    logger.info(
        "Tables created: raw.raw_listings, raw.raw_fuel_prices, raw.raw_qld_registrations, raw.raw_cpi"
    )


if __name__ == "__main__":
    setup_database()
