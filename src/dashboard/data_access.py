"""Read-only data and artifact access shared by Streamlit pages."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from config.database import get_engine
from config.settings import MODEL_DIR, PROJECT_ROOT

REFRESH_STATUS_PATH = PROJECT_ROOT / "docs" / "operations" / "latest_refresh.json"


class DashboardDataError(RuntimeError):
    """Raised when a dashboard dataset is not available or queryable."""


def _query(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    try:
        with get_engine().connect() as connection:
            return pd.read_sql_query(text(sql), connection, params=params)
    except SQLAlchemyError as error:
        raise DashboardDataError(str(error)) from error


def load_refresh_status(path: Path = REFRESH_STATUS_PATH) -> dict[str, Any]:
    """Load the workflow-owned refresh record; return an explicit pending state."""
    if not path.exists():
        return {"status": "not_run", "completed_at": None, "sources": {}, "dbt": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise DashboardDataError("Refresh status must be a JSON object")
        return payload
    except (OSError, json.JSONDecodeError) as error:
        raise DashboardDataError(f"Refresh status is unreadable: {error}") from error


def load_model_metrics(path: Path | None = None) -> dict[str, Any]:
    """Load only measured metrics emitted by the training workflow."""
    metrics_path = path or MODEL_DIR / "latest_metrics.json"
    if not metrics_path.exists():
        return {}
    try:
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise DashboardDataError("Model metrics must be a JSON object")
        return payload
    except (OSError, json.JSONDecodeError) as error:
        raise DashboardDataError(f"Model metrics are unreadable: {error}") from error


def get_listing_data() -> pd.DataFrame:
    """Return the latest canonical listing snapshot for modelled products."""
    return _query(
        """
        SELECT brand, model, variant, year, kilometres, body_type, fuel_type,
               transmission, drive_type, condition, location, doors, seats,
               cylinders, price, snapshot_date
        FROM raw.raw_listings
        WHERE snapshot_date = (SELECT max(snapshot_date) FROM raw.raw_listings)
          AND price IS NOT NULL
          AND year IS NOT NULL
        """
    )


def get_listing_catalog() -> pd.DataFrame:
    """Return available brand/model pairs from the latest snapshot."""
    return _query(
        """
        SELECT initcap(trim(brand)) AS brand, initcap(trim(model)) AS model,
               count(*) AS listing_count
        FROM raw.raw_listings
        WHERE snapshot_date = (SELECT max(snapshot_date) FROM raw.raw_listings)
          AND brand IS NOT NULL AND model IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1, listing_count DESC, 2
        """
    )


def get_qld_activity() -> pd.DataFrame:
    """Return monthly QLD new-registration/transfer activity by make."""
    return _query(
        """
        SELECT activity_month, initcap(trim(make)) AS make,
               lower(transaction_type) AS transaction_type,
               cast(sum(activity_count) AS bigint) AS activity_count
        FROM raw.raw_qld_registration_activity
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
        """
    )


def get_bitre_vehicle_makes() -> pd.DataFrame:
    """Return national registered-vehicle counts by make and reference year."""
    return _query(
        """
        SELECT initcap(trim(make)) AS make, reference_year, registered_vehicles
        FROM raw.raw_bitre_vehicle_makes
        ORDER BY reference_year, registered_vehicles DESC
        """
    )


def get_latest_fuel_prices() -> pd.DataFrame:
    """Return the latest observation per NSW station/fuel combination in AUD/L."""
    return _query(
        """
        WITH ranked AS (
            SELECT fueltype, price, lastupdated, stationcode, name, suburb,
                   row_number() OVER (
                       PARTITION BY stationcode, fueltype ORDER BY lastupdated DESC, fetched_at DESC
                   ) AS observation_rank
            FROM raw.raw_fuel_prices
            WHERE price IS NOT NULL
        )
        SELECT fueltype AS fuel_type, avg(price) / 100.0 AS average_aud_per_litre,
               min(price) / 100.0 AS minimum_aud_per_litre,
               max(price) / 100.0 AS maximum_aud_per_litre,
               count(*) AS station_count, max(lastupdated) AS latest_observation
        FROM ranked
        WHERE observation_rank = 1
        GROUP BY fueltype
        ORDER BY average_aud_per_litre
        """
    )


def get_economic_context() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return CPI and cash-rate histories from official RBA tables."""
    cpi = _query(
        """
        SELECT period_date, cpi_index
        FROM raw.raw_cpi
        ORDER BY period_date
        """
    )
    cash_rate = _query(
        """
        SELECT period_date, cash_rate_target_pct
        FROM raw.raw_rba_cash_rate
        ORDER BY period_date
        """
    )
    return cpi, cash_rate


def get_listing_price_trends() -> pd.DataFrame:
    """Return snapshot medians in nominal and latest-CPI Australian dollars."""
    listings = _query(
        """
        SELECT snapshot_date, percentile_cont(0.5) WITHIN GROUP (ORDER BY price)
               AS median_price_aud, count(*) AS listing_count
        FROM raw.raw_listings
        WHERE price IS NOT NULL
        GROUP BY snapshot_date
        ORDER BY snapshot_date
        """
    )
    if listings.empty:
        return listings
    cpi, _cash_rate = get_economic_context()
    if cpi.empty:
        listings["real_median_price_aud"] = pd.NA
        return listings

    listing_dates = pd.to_datetime(listings["snapshot_date"])
    cpi_dates = pd.to_datetime(cpi["period_date"])
    left = listings.assign(snapshot_date=listing_dates).sort_values("snapshot_date")
    right = cpi.assign(period_date=cpi_dates).sort_values("period_date")
    merged = pd.merge_asof(
        left,
        right,
        left_on="snapshot_date",
        right_on="period_date",
        direction="backward",
    )
    latest_cpi = float(right["cpi_index"].iloc[-1])
    merged["real_median_price_aud"] = merged["median_price_aud"] * latest_cpi / merged["cpi_index"]
    return merged


SOURCE_TABLES = {
    "Listings": ("raw.raw_listings", "ingested_at"),
    "NSW fuel": ("raw.raw_fuel_prices", "fetched_at"),
    "QLD activity": ("raw.raw_qld_registration_activity", "fetched_at"),
    "BITRE vehicles": ("raw.raw_bitre_vehicle_makes", "fetched_at"),
    "CPI": ("raw.raw_cpi", "fetched_at"),
    "RBA cash rate": ("raw.raw_rba_cash_rate", "fetched_at"),
}


def get_source_health() -> pd.DataFrame:
    """Return database row counts and freshness for an allowlisted table set."""
    rows: list[dict[str, Any]] = []
    for source, (table_name, timestamp_column) in SOURCE_TABLES.items():
        try:
            health = _query(
                f"SELECT count(*) AS row_count, max({timestamp_column}) AS freshest_at "  # noqa: S608
                f"FROM {table_name}"
            ).iloc[0]
            rows.append(
                {
                    "source": source,
                    "row_count": int(health["row_count"]),
                    "freshest_at": health["freshest_at"],
                    "status": "available",
                }
            )
        except DashboardDataError:
            rows.append(
                {
                    "source": source,
                    "row_count": 0,
                    "freshest_at": None,
                    "status": "unavailable",
                }
            )
    return pd.DataFrame(rows)
