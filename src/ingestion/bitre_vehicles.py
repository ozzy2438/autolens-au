"""BITRE Road Vehicles Australia workbook loader."""

import logging
from datetime import UTC, datetime
from io import BytesIO

import httpx
import pandas as pd
from sqlalchemy.engine import Engine
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config.database import ensure_raw_schema, get_engine, write_dataframe

RAW_BITRE_COLUMNS = [
    "make",
    "reference_year",
    "registered_vehicles",
    "source",
    "fetched_at",
]

logger = logging.getLogger(__name__)

BITRE_WORKBOOK_URL = (
    "https://www.bitre.gov.au/sites/default/files/documents/"
    "BITRE-Road-Vehicles-Australia-January-2025.xlsx"
)
BITRE_SOURCE = "bitre_road_vehicles_australia_january_2025_table_7"


def parse_bitre_vehicle_makes(content: bytes) -> pd.DataFrame:
    """Parse make-level registrations from Table 7 of the BITRE workbook."""
    table = pd.read_excel(BytesIO(content), sheet_name="Table 7", header=7)
    table = table.loc[:, ~table.columns.astype(str).str.startswith("Unnamed")]
    if "Make" not in table.columns:
        raise ValueError("BITRE Table 7 schema changed: Make column is missing")

    year_columns = [column for column in table.columns if str(column).isdigit()]
    if not year_columns:
        raise ValueError("BITRE Table 7 schema changed: no year columns found")

    table = table[table["Make"].notna()].copy()
    table["Make"] = table["Make"].astype("string").str.strip()
    table = table[table["Make"].str.casefold() != "total"]
    result = table.melt(
        id_vars="Make",
        value_vars=year_columns,
        var_name="reference_year",
        value_name="registered_vehicles",
    ).rename(columns={"Make": "make"})
    result["reference_year"] = pd.to_numeric(result["reference_year"], errors="raise").astype(
        "int64"
    )
    result["registered_vehicles"] = pd.to_numeric(
        result["registered_vehicles"].astype("string").str.replace(",", "", regex=False),
        errors="coerce",
    )
    result = result.dropna(subset=["registered_vehicles"])
    if result.empty:
        raise ValueError("BITRE Table 7 has no numeric vehicle counts")
    result["registered_vehicles"] = result["registered_vehicles"].astype("int64")
    result["source"] = BITRE_SOURCE
    result["fetched_at"] = pd.Timestamp(datetime.now(UTC))
    return result.reset_index(drop=True)


@retry(
    retry=retry_if_exception_type(httpx.HTTPError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=5, max=30),
    reraise=True,
)
def _download_workbook(client: httpx.Client) -> bytes:
    """Fetch the workbook with retries; bitre.gov.au is slow from datacenter IPs."""
    response = client.get(BITRE_WORKBOOK_URL)
    response.raise_for_status()
    return response.content


def fetch_bitre_vehicle_makes(client: httpx.Client | None = None) -> pd.DataFrame:
    """Download and parse the published BITRE workbook."""
    owns_client = client is None
    # The workbook is only ~150 KB, but the site intermittently stalls when serving
    # CI runners: keep connects short and allow a long read before each retry.
    http_client = client or httpx.Client(
        timeout=httpx.Timeout(connect=10.0, read=180.0, write=30.0, pool=10.0),
        follow_redirects=True,
        headers={"User-Agent": "autolens-au/1.0 (public data ingestion)"},
    )
    try:
        return parse_bitre_vehicle_makes(_download_workbook(http_client))
    finally:
        if owns_client:
            http_client.close()


def load_to_raw_schema(df: pd.DataFrame, engine: Engine | None = None) -> int:
    """Replace the published BITRE reference table in the configured database."""
    if df.empty:
        return 0
    target_engine = engine or get_engine()
    with target_engine.begin() as connection:
        ensure_raw_schema(connection)
    rows = write_dataframe(
        df,
        "raw_bitre_vehicle_makes",
        mode="replace",
        columns=RAW_BITRE_COLUMNS,
        engine=target_engine,
    )
    logger.info("Loaded %d BITRE make/year rows", rows)
    return rows


def run_bitre_ingestion() -> dict[str, int | str]:
    """Fetch and persist BITRE vehicle registration counts."""
    makes = fetch_bitre_vehicle_makes()
    rows = load_to_raw_schema(makes)
    return {"status": "success" if rows else "no_data", "rows": rows}
