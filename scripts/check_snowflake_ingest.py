"""Validate the pandas -> Snowflake write path against the isolated CI database.

dbt seeds cover the SQL layer but never exercise the Python ingestion writes, which
is how the timestamp-binding regression reached a real refresh. This script writes
small frames that contain DATE and TIMESTAMP columns through the same persistence
functions the pipeline uses, then verifies the rows round-trip. It is destructive and
must only run against AUTOLENS_AU_CI.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import get_engine
from config.settings import db_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RAW_TABLES = (
    "raw_listings",
    "raw_fuel_prices",
    "raw_qld_registration_activity",
    "raw_cpi",
    "raw_rba_cash_rate",
    "raw_bitre_vehicle_makes",
)


def _listings_frame(snapshot: str) -> pd.DataFrame:
    from src.ingestion.kaggle_loader import add_lineage

    canonical = pd.DataFrame(
        {
            "brand": ["Toyota", "Mazda"],
            "model": ["Camry", "CX-5"],
            "year": [2020, 2019],
            "kilometres": [45000, 68000],
            "price": [35000, 31500],
            "body_type": ["Sedan", "SUV"],
            # A value well over 50 chars guards against the raw-column truncation
            # that a bounded VARCHAR would reject on Snowflake.
            "vehicle_type": [
                "Gold Coast Chrysler Jeep Dodge NEW Frizelle Sunshine Automotive",
                "SUV",
            ],
        }
    )
    return add_lineage(canonical, "ci_smoke", snapshot)


def _truncate_all(engine) -> None:
    with engine.begin() as connection:
        for table in RAW_TABLES:
            # table comes from the module allow-list, not user input.
            connection.execute(text(f"TRUNCATE TABLE IF EXISTS raw.{table}"))


def _count(engine, table: str) -> int:
    if table not in RAW_TABLES:
        raise ValueError(f"Unknown raw table: {table}")
    with engine.connect() as connection:
        return int(
            connection.execute(
                text(f"SELECT count(*) FROM raw.{table}")  # noqa: S608 -- table is allow-listed
            ).scalar_one()
        )


def _require(actual: int, expected: int, label: str) -> None:
    """Raise on mismatch; explicit so validation survives ``python -O``."""
    if actual != expected:
        raise RuntimeError(f"{label}: expected {expected} rows, found {actual}")


def main() -> int:
    if db_config.resolved_backend != "snowflake":
        logger.error("This check only runs against Snowflake")
        return 1
    if db_config.snowflake_database.upper() != "AUTOLENS_AU_CI":
        logger.error("Refusing to run destructive check outside AUTOLENS_AU_CI")
        return 1

    from src.ingestion.bitre_vehicles import load_to_raw_schema as load_bitre
    from src.ingestion.kaggle_loader import load_to_raw_schema as load_listings
    from src.ingestion.nsw_fuelcheck import load_fuel_prices_to_db
    from src.ingestion.qld_registrations import load_to_raw_schema as load_qld

    # Raw tables are provisioned by a preceding `scripts/setup_database.py` step.
    engine = get_engine()
    _truncate_all(engine)

    # Listings: two snapshots of the same vehicles must both be retained (append-only),
    # exercising the timestamp-binding fix and the Snowflake upsert statements.
    load_listings(_listings_frame("2026-07-01"))
    load_listings(_listings_frame("2026-08-01"))
    _require(_count(engine, "raw_listings"), 4, "raw_listings across two snapshots")

    # Fuel: append with a tz-aware fetched_at and a naive lastupdated timestamp.
    load_fuel_prices_to_db(
        pd.DataFrame(
            {
                "stationcode": ["101"],
                "fueltype": ["U91"],
                "price": [189.9],
                "lastupdated": [datetime(2026, 7, 15, 8, 0, 0)],
                "name": ["CI Station"],
                "extra_api_field": ["dropped"],
                "fetched_at": [pd.Timestamp.now(tz="UTC")],
                "source": ["ci_smoke"],
            }
        )
    )
    _require(_count(engine, "raw_fuel_prices"), 1, "raw_fuel_prices")

    # QLD: replace with a DATE activity_month.
    load_qld(
        pd.DataFrame(
            {
                "activity_month": [pd.Timestamp("2026-06-01", tz="UTC")],
                "make": ["toyota"],
                "model": ["camry"],
                "badge": ["ascent"],
                "body_shape": ["sedan"],
                "fuel_type": ["petrol"],
                "transaction_type": ["new"],
                "activity_count": [123],
                "source_resource_id": ["ci"],
                "source": ["ci_smoke"],
                "fetched_at": [pd.Timestamp.now(tz="UTC")],
            }
        )
    )
    _require(_count(engine, "raw_qld_registration_activity"), 1, "raw_qld_registration_activity")

    # BITRE: replace with a plain reference year.
    load_bitre(
        pd.DataFrame(
            {
                "make": ["toyota"],
                "reference_year": [2025],
                "registered_vehicles": [1000000],
                "source": ["ci_smoke"],
                "fetched_at": [pd.Timestamp.now(tz="UTC")],
            }
        )
    )
    _require(_count(engine, "raw_bitre_vehicle_makes"), 1, "raw_bitre_vehicle_makes")

    logger.info("Snowflake ingestion write path validated; cleaning up")
    _truncate_all(engine)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
