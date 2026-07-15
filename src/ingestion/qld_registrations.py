"""Queensland Vehicle Registrations data loader.

Source: https://www.data.qld.gov.au/dataset/vehicle-registrations
License: Creative Commons Attribution 4.0

This dataset contains registration information for all vehicles,
trailers, caravans and motorcycles registered in Queensland, including:
- Vehicle make, year, colour, category
- Body shape, fuel type
- Registration suburb

Update frequency: Annually (October typically)
Used for: Fleet composition analysis by make/model to contextualise
          pricing trends and market share.
"""

import logging
from pathlib import Path
from typing import Optional

import httpx
import pandas as pd
from sqlalchemy import text

from config.settings import DATA_DIR
from config.database import get_engine

logger = logging.getLogger(__name__)

# QLD Open Data Portal endpoints
QLD_REGO_DATASET_URL = "https://www.data.qld.gov.au/dataset/vehicle-registrations"
QLD_LIGHT_VEHICLES_URLS = [
    "https://www.data.qld.gov.au/dataset/vehicle-registrations/resource/",
]

# New registrations by year (more regularly updated)
QLD_NEW_REGO_URL = (
    "https://www.data.qld.gov.au/dataset/new-vehicle-registrations-by-year"
    "/resource/e6531fe2-a5aa-4a93-b954-465e679def78"
)


def download_qld_registrations(
    output_dir: Optional[Path] = None,
    resource_url: Optional[str] = None,
) -> Path:
    """Download QLD vehicle registration data from open data portal.
    
    Uses the CKAN API to fetch data in CSV format.
    """
    output_dir = output_dir or DATA_DIR / "raw" / "qld_rego"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the datastore API for direct data access
    api_url = "https://www.data.qld.gov.au/api/3/action/datastore_search"
    
    all_records = []
    offset = 0
    limit = 10000  # Max records per request
    
    logger.info("Downloading QLD registration data...")
    
    with httpx.Client(timeout=60.0) as client:
        while True:
            params = {
                "limit": limit,
                "offset": offset,
            }
            if resource_url:
                params["resource_id"] = resource_url.split("/")[-1]
            
            response = client.get(api_url, params=params)
            
            if response.status_code != 200:
                logger.warning(f"QLD API returned {response.status_code}, stopping")
                break
            
            data = response.json()
            records = data.get("result", {}).get("records", [])
            
            if not records:
                break
            
            all_records.extend(records)
            offset += limit
            
            if len(records) < limit:
                break
    
    if all_records:
        df = pd.DataFrame(all_records)
        output_path = output_dir / "qld_registrations.csv"
        df.to_csv(output_path, index=False)
        logger.info(f"Downloaded {len(df)} QLD registration records to {output_path}")
        return output_path
    else:
        logger.warning("No QLD registration records downloaded")
        return output_dir / "qld_registrations.csv"


def load_qld_registrations(filepath: Optional[Path] = None) -> pd.DataFrame:
    """Load and standardise QLD vehicle registration data.
    
    Returns:
        DataFrame with fleet composition data (make, model, year, body, fuel type, count).
    """
    if filepath is None:
        filepath = DATA_DIR / "raw" / "qld_rego" / "qld_registrations.csv"
    
    if not filepath.exists():
        logger.warning(f"QLD registration data not found at {filepath}")
        return pd.DataFrame()
    
    logger.info(f"Loading QLD registrations from {filepath}")
    df = pd.read_csv(filepath, low_memory=False)
    
    # Standardise column names (QLD data uses UPPER_CASE)
    df.columns = df.columns.str.lower().str.strip()
    
    # Map common column names
    rename_map = {
        "make": "make",
        "model": "model",
        "year_of_manufacture": "year",
        "body_shape": "body_type",
        "fuel_type": "fuel_type",
        "colour": "colour",
        "vehicle_type": "vehicle_category",
    }
    
    # Only rename columns that exist
    existing_renames = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=existing_renames)
    
    # Add metadata
    df["source"] = "qld_open_data_registrations"
    df["ingested_at"] = pd.Timestamp.now(tz="UTC")
    
    logger.info(f"Loaded {len(df)} QLD registration records")
    return df


def compute_fleet_composition(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate registration data into fleet composition summary.
    
    Groups by make/model/year/body/fuel to show fleet distribution.
    This is used in the Market Monitor dashboard page.
    """
    if df.empty:
        return pd.DataFrame()
    
    group_cols = ["make", "model", "year", "body_type", "fuel_type"]
    available_cols = [c for c in group_cols if c in df.columns]
    
    if not available_cols:
        logger.warning("No grouping columns available for fleet composition")
        return df
    
    composition = (
        df.groupby(available_cols, dropna=False)
        .size()
        .reset_index(name="registration_count")
    )
    
    # Calculate market share
    total = composition["registration_count"].sum()
    composition["market_share_pct"] = (
        composition["registration_count"] / total * 100
    ).round(4)
    
    return composition.sort_values("registration_count", ascending=False)


def load_to_raw_schema(df: pd.DataFrame) -> int:
    """Load QLD registration data to PostgreSQL raw schema."""
    engine = get_engine()
    
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.commit()
    
    df.to_sql(
        "raw_qld_registrations",
        engine,
        schema="raw",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )
    
    logger.info(f"Loaded {len(df)} QLD registration records to raw.raw_qld_registrations")
    return len(df)


def run_qld_ingestion(download: bool = False) -> dict:
    """Execute QLD registration data ingestion."""
    stats = {"status": "success", "rows": 0}
    
    if download:
        download_qld_registrations()
    
    df = load_qld_registrations()
    if df.empty:
        stats["status"] = "no_data"
        return stats
    
    rows = load_to_raw_schema(df)
    stats["rows"] = rows
    
    # Also compute and store fleet composition
    composition = compute_fleet_composition(df)
    if not composition.empty:
        engine = get_engine()
        composition.to_sql(
            "raw_fleet_composition",
            engine,
            schema="raw",
            if_exists="replace",
            index=False,
        )
        stats["composition_rows"] = len(composition)
    
    return stats
