"""Kaggle dataset loader for Australian Vehicle Prices.

Sources:
- Primary: nelgiriyewithana/australian-vehicle-prices (~16,700 listings)
- Secondary: lainguyn123/australia-car-market-data

Compliance: These are publicly available research datasets on Kaggle.
No ToS-protected marketplace scraping is performed.
"""

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from config.database import get_engine
from config.settings import DATA_DIR

logger = logging.getLogger(__name__)

# Dataset identifiers
PRIMARY_DATASET = "nelgiriyewithana/australian-vehicle-prices"
SECONDARY_DATASET = "lainguyn123/australia-car-market-data"

# Expected columns in primary dataset
PRIMARY_COLUMNS = [
    "Brand",
    "Year",
    "Model",
    "Car/Suv",
    "Title",
    "UsedOrNew",
    "Transmission",
    "Engine",
    "DriveType",
    "FuelType",
    "FuelConsumption",
    "Kilometres",
    "ColourExtInt",
    "Location",
    "CylindersinEngine",
    "BodyType",
    "Doors",
    "Seats",
    "Price",
]


def download_kaggle_dataset(dataset_id: str, output_dir: Path | None = None) -> Path:
    """Download a dataset from Kaggle using the Kaggle API.

    Requires KAGGLE_USERNAME and KAGGLE_KEY environment variables.
    """
    output_dir = output_dir or DATA_DIR / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(dataset_id, path=str(output_dir), unzip=True)
        logger.info(f"Downloaded dataset: {dataset_id} to {output_dir}")
    except Exception as e:
        logger.error(f"Failed to download {dataset_id}: {e}")
        raise

    return output_dir


def load_primary_dataset(filepath: Path | None = None) -> pd.DataFrame:
    """Load and perform initial cleaning of the primary AU vehicle prices dataset.

    Returns:
        DataFrame with standardised column names and basic type corrections.
    """
    if filepath is None:
        filepath = DATA_DIR / "raw" / "Australian Vehicle Prices.csv"

    logger.info(f"Loading primary dataset from {filepath}")

    df = pd.read_csv(filepath, low_memory=False)

    # Standardise column names
    column_mapping = {
        "Brand": "brand",
        "Year": "year",
        "Model": "model",
        "Car/Suv": "vehicle_type",
        "Title": "title",
        "UsedOrNew": "condition",
        "Transmission": "transmission",
        "Engine": "engine",
        "DriveType": "drive_type",
        "FuelType": "fuel_type",
        "FuelConsumption": "fuel_consumption",
        "Kilometres": "kilometres",
        "ColourExtInt": "colour",
        "Location": "location",
        "CylindersinEngine": "cylinders",
        "BodyType": "body_type",
        "Doors": "doors",
        "Seats": "seats",
        "Price": "price",
    }
    df = df.rename(columns=column_mapping)

    # Basic type corrections
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["kilometres"] = pd.to_numeric(
        df["kilometres"].astype(str).str.replace(",", "").str.replace(" km", ""), errors="coerce"
    )
    df["price"] = pd.to_numeric(
        df["price"].astype(str).str.replace(",", "").str.replace("$", ""), errors="coerce"
    )
    df["doors"] = pd.to_numeric(df["doors"], errors="coerce")
    df["seats"] = pd.to_numeric(df["seats"], errors="coerce")
    df["cylinders"] = pd.to_numeric(df["cylinders"], errors="coerce")

    # Add metadata
    df["source"] = "kaggle_au_vehicle_prices"
    df["ingested_at"] = pd.Timestamp.now(tz="UTC")

    logger.info(f"Loaded {len(df)} records from primary dataset")
    return df


def load_secondary_dataset(filepath: Path | None = None) -> pd.DataFrame:
    """Load secondary Australian Car Market dataset.

    This provides additional listings for cross-validation and coverage.
    """
    if filepath is None:
        filepath = DATA_DIR / "raw" / "australia_car_market.csv"

    if not filepath.exists():
        logger.warning(f"Secondary dataset not found at {filepath}, skipping")
        return pd.DataFrame()

    logger.info(f"Loading secondary dataset from {filepath}")
    df = pd.read_csv(filepath, low_memory=False)

    # Standardise to match primary schema (mapping depends on actual columns)
    df["source"] = "kaggle_au_car_market"
    df["ingested_at"] = pd.Timestamp.now(tz="UTC")

    logger.info(f"Loaded {len(df)} records from secondary dataset")
    return df


def deduplicate_listings(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate vehicle listings across sources.

    Deduplication strategy:
    - Same brand + model + year + kilometres + price = likely duplicate
    - Keep the record with more complete data (fewer nulls)
    """
    dedup_cols = ["brand", "model", "year", "kilometres", "price"]
    available_cols = [c for c in dedup_cols if c in df.columns]

    if not available_cols:
        logger.warning("No deduplication columns found, returning as-is")
        return df

    before_count = len(df)

    # Score completeness
    df["_completeness"] = df.notna().sum(axis=1)

    # Sort by completeness (descending) and drop duplicates keeping first (most complete)
    df = df.sort_values("_completeness", ascending=False)
    df = df.drop_duplicates(subset=available_cols, keep="first")
    df = df.drop(columns=["_completeness"])

    after_count = len(df)
    logger.info(
        f"Deduplication: {before_count} -> {after_count} records ({before_count - after_count} removed)"
    )

    return df


def load_to_raw_schema(df: pd.DataFrame, table_name: str = "raw_listings") -> int:
    """Load DataFrame into PostgreSQL raw schema.

    Returns:
        Number of rows loaded.
    """
    engine = get_engine()

    # Ensure raw schema exists
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.commit()

    # Write to database
    df.to_sql(
        table_name,
        engine,
        schema="raw",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )

    logger.info(f"Loaded {len(df)} rows to raw.{table_name}")
    return len(df)


def run_ingestion(download: bool = False) -> dict:
    """Execute full ingestion pipeline.

    Args:
        download: If True, download fresh data from Kaggle.

    Returns:
        Dictionary with ingestion statistics.
    """
    stats = {"primary_rows": 0, "secondary_rows": 0, "total_after_dedup": 0}

    if download:
        download_kaggle_dataset(PRIMARY_DATASET)
        download_kaggle_dataset(SECONDARY_DATASET)

    # Load datasets
    primary_df = load_primary_dataset()
    stats["primary_rows"] = len(primary_df)

    secondary_df = load_secondary_dataset()
    stats["secondary_rows"] = len(secondary_df)

    # Combine
    if not secondary_df.empty:
        # Align columns before concat
        combined_df = pd.concat([primary_df, secondary_df], ignore_index=True, sort=False)
    else:
        combined_df = primary_df

    # Deduplicate
    combined_df = deduplicate_listings(combined_df)
    stats["total_after_dedup"] = len(combined_df)

    # Load to database
    load_to_raw_schema(combined_df)

    logger.info(f"Ingestion complete: {stats}")
    return stats
