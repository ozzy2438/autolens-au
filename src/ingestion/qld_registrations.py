"""Queensland new-registration and transfer activity loader.

The current Queensland Open Data package is partitioned across several CKAN
DataStore resources.  Resources are discovered from package metadata rather
than hard-coding a resource UUID, and aggregation happens in CKAN so the
pipeline does not download millions of row-level records.
"""

import logging
import re
from datetime import UTC, date, datetime

import httpx
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config.database import get_engine

logger = logging.getLogger(__name__)

QLD_CKAN_BASE = "https://www.data.qld.gov.au/api/3/action"
QLD_PACKAGE_ID = "vehicle-registration-new-and-transfers-test"
QLD_SOURCE = "qld_open_data_registration_activity"
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _get_json(client: httpx.Client, endpoint: str, **params: str) -> dict:
    response = client.get(f"{QLD_CKAN_BASE}/{endpoint}", params=params)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"QLD CKAN {endpoint} request was unsuccessful")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"QLD CKAN {endpoint} returned an invalid result")
    return result


def discover_qld_resource_ids(client: httpx.Client) -> list[str]:
    """Return active CSV/DataStore resources in the current QLD package."""
    package = _get_json(client, "package_show", id=QLD_PACKAGE_ID)
    resource_ids: list[str] = []
    for resource in package.get("resources", []):
        resource_id = str(resource.get("id", ""))
        name = str(resource.get("name", "")).upper()
        data_format = str(resource.get("format", "")).upper()
        if (
            resource.get("state") == "active"
            and resource.get("datastore_active") is True
            and data_format == "CSV"
            and "VEHICLE_REGISTRATION_NEW_AND_TRANSFERS" in name
            and UUID_PATTERN.fullmatch(resource_id)
        ):
            resource_ids.append(resource_id)

    if not resource_ids:
        raise RuntimeError("No active QLD registration activity resources were discovered")
    return resource_ids


def _default_since() -> date:
    return date(datetime.now(UTC).year - 2, 1, 1)


def fetch_qld_registration_activity(
    since: date | None = None,
    client: httpx.Client | None = None,
) -> pd.DataFrame:
    """Fetch monthly QLD new-registration/transfer counts from CKAN."""
    since = since or _default_since()
    if since > date.today():
        raise ValueError("since cannot be in the future")

    owns_client = client is None
    http_client = client or httpx.Client(timeout=90.0)
    frames: list[pd.DataFrame] = []
    try:
        for resource_id in discover_qld_resource_ids(http_client):
            # Both dynamic values are validated before interpolation. CKAN's SQL
            # endpoint does not expose parameter binding.
            if not UUID_PATTERN.fullmatch(resource_id):
                raise ValueError("Invalid QLD CKAN resource identifier")
            since_iso = since.isoformat()
            # Some partitions expose RECORD_DATE as timestamp and others as text.
            # The published text values are ISO dates, so one explicit cast keeps
            # the same query valid across the full package.
            sql = f'''SELECT date_trunc('month', "RECORD_DATE"::timestamp) AS "activity_month",
                "MAKE", "MODEL", "BADGE", "BODY_SHAPE", "FUEL_TYPE", "TRANSACTION_TYPE",
                count(*) AS "activity_count"
                FROM "{resource_id}"
                WHERE "RECORD_DATE"::date >= '{since_iso}'::date
                GROUP BY 1, 2, 3, 4, 5, 6, 7'''  # noqa: S608
            result = _get_json(http_client, "datastore_search_sql", sql=sql)
            records = result.get("records", [])
            if records:
                frame = pd.DataFrame(records)
                frame["source_resource_id"] = resource_id
                frames.append(frame)
    finally:
        if owns_client:
            http_client.close()

    if not frames:
        return pd.DataFrame(
            columns=[
                "activity_month",
                "make",
                "model",
                "badge",
                "body_shape",
                "fuel_type",
                "transaction_type",
                "activity_count",
                "source_resource_id",
                "source",
                "fetched_at",
            ]
        )

    activity = pd.concat(frames, ignore_index=True).rename(
        columns={
            "MAKE": "make",
            "MODEL": "model",
            "BADGE": "badge",
            "BODY_SHAPE": "body_shape",
            "FUEL_TYPE": "fuel_type",
            "TRANSACTION_TYPE": "transaction_type",
        }
    )
    activity["activity_month"] = pd.to_datetime(activity["activity_month"], utc=True)
    activity["activity_count"] = pd.to_numeric(activity["activity_count"], errors="raise").astype(
        "int64"
    )
    activity["source"] = QLD_SOURCE
    activity["fetched_at"] = pd.Timestamp.now(tz="UTC")
    return activity


def load_to_raw_schema(df: pd.DataFrame, engine: Engine | None = None) -> int:
    """Replace the bounded, authoritative QLD activity window in PostgreSQL."""
    if df.empty:
        return 0
    target_engine = engine or get_engine()
    with target_engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
    df.to_sql(
        "raw_qld_registration_activity",
        target_engine,
        schema="raw",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )
    logger.info("Loaded %d QLD registration activity rows", len(df))
    return len(df)


def run_qld_ingestion(since: date | None = None) -> dict[str, int | str]:
    """Fetch and persist QLD registration activity."""
    activity = fetch_qld_registration_activity(since=since)
    if activity.empty:
        return {"status": "no_data", "rows": 0}
    rows = load_to_raw_schema(activity)
    return {
        "status": "success",
        "rows": rows,
        "resources": int(activity["source_resource_id"].nunique()),
    }
