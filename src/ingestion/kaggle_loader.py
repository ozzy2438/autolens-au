"""Validated loaders for the two public Australian vehicle datasets on Kaggle."""

import hashlib
import logging
import re
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config.database import ensure_raw_schema, get_engine
from config.settings import DATA_DIR

logger = logging.getLogger(__name__)

PRIMARY_DATASET = "nelgiriyewithana/australian-vehicle-prices"
SECONDARY_DATASET = "lainguyn123/australia-car-market-data"

DOMAIN_COLUMNS = [
    "source_record_id",
    "brand",
    "year",
    "model",
    "variant",
    "vehicle_type",
    "title",
    "condition",
    "transmission",
    "engine",
    "drive_type",
    "fuel_type",
    "fuel_consumption",
    "kilometres",
    "colour",
    "location",
    "cylinders",
    "body_type",
    "doors",
    "seats",
    "price",
]
LINEAGE_COLUMNS = ["source", "listing_fingerprint", "snapshot_date", "ingested_at"]
RAW_COLUMNS = DOMAIN_COLUMNS + LINEAGE_COLUMNS
REQUIRED_COLUMNS = {"brand", "model", "year", "price"}

PRIMARY_MAPPING = {
    "brand": "brand",
    "year": "year",
    "model": "model",
    "carsuv": "vehicle_type",
    "title": "title",
    "usedornew": "condition",
    "transmission": "transmission",
    "engine": "engine",
    "drivetype": "drive_type",
    "fueltype": "fuel_type",
    "fuelconsumption": "fuel_consumption",
    "kilometres": "kilometres",
    "colourextint": "colour",
    "location": "location",
    "cylindersinengine": "cylinders",
    "bodytype": "body_type",
    "doors": "doors",
    "seats": "seats",
    "price": "price",
}

SECONDARY_MAPPING = {
    "id": "source_record_id",
    "name": "title",
    "price": "price",
    "brand": "brand",
    "model": "model",
    "variant": "variant",
    "series": "series",
    "year": "year",
    "gearbox": "transmission",
    "type": "body_type",
    "fuel": "fuel_type",
    "status": "condition",
    "kilometers": "kilometres",
    "kilometres": "kilometres",
    "cc": "engine",
    "color": "colour",
    "colour": "colour",
    "seatingcapacity": "seats",
}


def _normalise_header(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _parse_numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.replace(r"[^0-9.-]", "", regex=True)
    return pd.to_numeric(cleaned.replace("", pd.NA), errors="coerce")


def _validate_required_columns(df: pd.DataFrame, dataset_name: str) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        msg = f"{dataset_name} is missing required canonical columns: {', '.join(missing)}"
        raise ValueError(msg)


def _canonicalise(
    df: pd.DataFrame,
    mapping: dict[str, str],
    dataset_name: str,
) -> pd.DataFrame:
    renamed = df.rename(
        columns={col: mapping.get(_normalise_header(col), col) for col in df.columns}
    )

    if dataset_name == "secondary":
        if "model" not in renamed and "series" in renamed:
            renamed["model"] = renamed["series"]
        if "model" in renamed and "series" in renamed:
            renamed["model"] = renamed["model"].fillna(renamed["series"])
        if "body_type" in renamed:
            renamed["vehicle_type"] = renamed["body_type"]
        renamed["location"] = "Australia"

    _validate_required_columns(renamed, dataset_name)
    canonical = renamed.reindex(columns=DOMAIN_COLUMNS).copy()

    for column in ("year", "kilometres", "cylinders", "doors", "seats", "price"):
        canonical[column] = _parse_numeric(canonical[column])

    for column in set(DOMAIN_COLUMNS) - {
        "year",
        "kilometres",
        "cylinders",
        "doors",
        "seats",
        "price",
    }:
        canonical[column] = canonical[column].astype("string").str.strip()
        canonical[column] = canonical[column].replace("", pd.NA)

    return canonical


def _fingerprint_row(row: pd.Series) -> str:
    identity_columns = ["brand", "model", "year", "kilometres", "price"]
    identity = "|".join(
        "" if pd.isna(row[col]) else str(row[col]).strip().lower() for col in identity_columns
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def add_lineage(
    df: pd.DataFrame,
    source: str,
    snapshot_date: date | str | None = None,
) -> pd.DataFrame:
    """Add stable identity and temporal lineage to a canonical listing frame."""
    snapshot = pd.Timestamp(snapshot_date or datetime.now(UTC).date()).date()
    result = df.copy()
    result["source"] = source
    result["listing_fingerprint"] = result.apply(_fingerprint_row, axis=1)
    result["snapshot_date"] = snapshot
    result["ingested_at"] = pd.Timestamp.now(tz="UTC")
    return result.reindex(columns=RAW_COLUMNS)


def download_kaggle_dataset(dataset_id: str, output_dir: Path | None = None) -> Path:
    """Download and unzip one Kaggle dataset using environment credentials."""
    output_dir = output_dir or DATA_DIR / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    api.dataset_download_files(dataset_id, path=str(output_dir), unzip=True)
    logger.info("Downloaded %s to %s", dataset_id, output_dir)
    return output_dir


def _resolve_csv(directory: Path, preferred_names: list[str], search_term: str) -> Path:
    for name in preferred_names:
        candidate = directory / name
        if candidate.exists():
            return candidate
    matches = sorted(path for path in directory.glob("*.csv") if search_term in path.name.lower())
    if not matches:
        raise FileNotFoundError(f"No CSV matching '{search_term}' found in {directory}")
    return matches[0]


def load_primary_dataset(
    filepath: Path | None = None,
    snapshot_date: date | str | None = None,
) -> pd.DataFrame:
    """Load and validate the Australian Vehicle Prices dataset."""
    filepath = filepath or _resolve_csv(
        DATA_DIR / "raw",
        ["Australian Vehicle Prices.csv"],
        "vehicle",
    )
    canonical = _canonicalise(pd.read_csv(filepath, low_memory=False), PRIMARY_MAPPING, "primary")
    result = add_lineage(canonical, "kaggle_au_vehicle_prices", snapshot_date)
    logger.info("Loaded %s primary listings", len(result))
    return result


def load_secondary_dataset(
    filepath: Path | None = None,
    snapshot_date: date | str | None = None,
) -> pd.DataFrame:
    """Load and validate the Australia Car Market dataset."""
    if filepath is None:
        try:
            filepath = _resolve_csv(
                DATA_DIR / "raw",
                ["australia_car_market.csv", "Australia Car Market.csv"],
                "market",
            )
        except FileNotFoundError:
            logger.warning("Secondary Kaggle CSV not found; continuing with the primary source")
            return pd.DataFrame(columns=RAW_COLUMNS)

    canonical = _canonicalise(
        pd.read_csv(filepath, low_memory=False), SECONDARY_MAPPING, "secondary"
    )
    result = add_lineage(canonical, "kaggle_au_car_market", snapshot_date)
    logger.info("Loaded %s secondary listings", len(result))
    return result


def deduplicate_listings(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the most complete copy of the same listing within one snapshot."""
    dedup_cols = ["brand", "model", "year", "kilometres", "price", "snapshot_date"]
    available_cols = [column for column in dedup_cols if column in df.columns]
    if not available_cols:
        return df.copy()

    scored = df.copy()
    completeness_columns = [column for column in DOMAIN_COLUMNS if column in scored.columns]
    scored["_completeness"] = scored[completeness_columns].notna().sum(axis=1)
    scored = scored.sort_values("_completeness", ascending=False)
    result = scored.drop_duplicates(subset=available_cols, keep="first")
    return result.drop(columns="_completeness").reset_index(drop=True)


def _raw_listing_upsert_statements(dialect: str) -> list[str]:
    """Build the batch-to-canonical upsert statements for the active SQL dialect."""
    added_columns = (
        "source_record_id TEXT",
        "variant TEXT",
        "listing_fingerprint TEXT",
        "snapshot_date DATE",
    )
    alter_statements = [
        f"ALTER TABLE raw.raw_listings ADD COLUMN IF NOT EXISTS {column}"
        for column in added_columns
    ]
    if dialect == "snowflake":
        # Snowflake has no CREATE INDEX on standard tables, takes LIKE without
        # parentheses, rejects an alias on the DELETE target, and stores the
        # batch table's unquoted identifiers in uppercase, so quoted-lowercase
        # column references would not resolve.
        columns = ", ".join(RAW_COLUMNS)
        return [
            "CREATE TABLE IF NOT EXISTS raw.raw_listings LIKE raw._raw_listings_batch",
            *alter_statements,
            "DELETE FROM raw.raw_listings "
            "USING raw._raw_listings_batch AS batch "
            "WHERE raw.raw_listings.listing_fingerprint = batch.listing_fingerprint "
            "AND raw.raw_listings.snapshot_date = batch.snapshot_date",
            f"INSERT INTO raw.raw_listings ({columns}) "  # noqa: S608
            f"SELECT {columns} FROM raw._raw_listings_batch",
            "DROP TABLE raw._raw_listings_batch",
        ]
    quoted_columns = ", ".join(f'"{column}"' for column in RAW_COLUMNS)
    return [
        "CREATE TABLE IF NOT EXISTS raw.raw_listings "
        "(LIKE raw._raw_listings_batch INCLUDING DEFAULTS)",
        *alter_statements,
        "DELETE FROM raw.raw_listings AS existing "
        "USING raw._raw_listings_batch AS batch "
        "WHERE existing.listing_fingerprint = batch.listing_fingerprint "
        "AND existing.snapshot_date = batch.snapshot_date",
        f"INSERT INTO raw.raw_listings ({quoted_columns}) "  # noqa: S608
        f"SELECT {quoted_columns} FROM raw._raw_listings_batch",
        "DROP TABLE raw._raw_listings_batch",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_raw_listings_snapshot "
        "ON raw.raw_listings (listing_fingerprint, snapshot_date)",
    ]


def load_to_raw_schema(
    df: pd.DataFrame,
    table_name: str = "raw_listings",
    engine: Engine | None = None,
) -> int:
    """Upsert a snapshot batch while preserving all earlier snapshots."""
    if df.empty:
        return 0
    if table_name != "raw_listings":
        raise ValueError("Only the canonical raw_listings table is supported")

    database = engine or get_engine()
    batch_table = "_raw_listings_batch"

    with database.begin() as connection:
        ensure_raw_schema(connection)
        df.reindex(columns=RAW_COLUMNS).to_sql(
            batch_table,
            connection,
            schema="raw",
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=1000,
        )
        for statement in _raw_listing_upsert_statements(connection.dialect.name):
            connection.execute(text(statement))

    logger.info("Loaded %s listings into raw.raw_listings", len(df))
    return len(df)


def run_ingestion(
    download: bool = False,
    snapshot_date: date | str | None = None,
) -> dict[str, int | str]:
    """Download, canonicalise, deduplicate, and persist both listing sources."""
    if download:
        download_kaggle_dataset(PRIMARY_DATASET)
        download_kaggle_dataset(SECONDARY_DATASET)

    primary = load_primary_dataset(snapshot_date=snapshot_date)
    secondary = load_secondary_dataset(snapshot_date=snapshot_date)
    combined = deduplicate_listings(pd.concat([primary, secondary], ignore_index=True))
    loaded_rows = load_to_raw_schema(combined)
    snapshot = str(pd.Timestamp(snapshot_date or datetime.now(UTC).date()).date())

    return {
        "status": "success",
        "snapshot_date": snapshot,
        "primary_rows": len(primary),
        "secondary_rows": len(secondary),
        "loaded_rows": loaded_rows,
    }
