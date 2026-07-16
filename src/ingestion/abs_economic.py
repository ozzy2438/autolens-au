"""Official RBA economic-series loader for CPI and the cash-rate target."""

import csv
import logging
from io import StringIO

import httpx
import pandas as pd
from sqlalchemy.engine import Engine

from config.database import ensure_raw_schema, get_engine

logger = logging.getLogger(__name__)

RBA_CPI_URL = "https://www.rba.gov.au/statistics/tables/csv/g1-data.csv"
RBA_CASH_RATE_URL = "https://www.rba.gov.au/statistics/tables/csv/f1-data.csv"
RBA_CPI_SERIES_ID = "GCPIAG"
RBA_CASH_RATE_SERIES_ID = "FIRMMCRTD"


def parse_rba_series(content: str, series_id: str, value_name: str) -> pd.DataFrame:
    """Extract one dated series from an RBA statistical-table CSV."""
    rows = list(csv.reader(StringIO(content)))
    series_row_index = next(
        (index for index, row in enumerate(rows) if row and row[0].strip() == "Series ID"),
        None,
    )
    if series_row_index is None:
        raise ValueError("RBA CSV schema changed: Series ID row is missing")

    series_row = rows[series_row_index]
    try:
        series_column = series_row.index(series_id)
    except ValueError as error:
        raise ValueError(f"RBA series {series_id} is missing") from error

    observations: list[dict[str, object]] = []
    for row in rows[series_row_index + 1 :]:
        if len(row) <= series_column or not row[0].strip():
            continue
        period_date = pd.to_datetime(row[0].strip(), dayfirst=True, errors="coerce")
        value = pd.to_numeric(row[series_column].strip(), errors="coerce")
        if pd.notna(period_date) and pd.notna(value):
            observations.append({"period_date": period_date, value_name: float(value)})

    if not observations:
        raise ValueError(f"RBA series {series_id} has no observations")
    return pd.DataFrame(observations).sort_values("period_date").reset_index(drop=True)


def _fetch_rba_series(
    url: str,
    series_id: str,
    value_name: str,
    client: httpx.Client | None = None,
) -> pd.DataFrame:
    owns_client = client is None
    http_client = client or httpx.Client(timeout=60.0, follow_redirects=True)
    try:
        response = http_client.get(url)
        response.raise_for_status()
        return parse_rba_series(response.text, series_id, value_name)
    finally:
        if owns_client:
            http_client.close()


def fetch_abs_cpi(client: httpx.Client | None = None) -> pd.DataFrame:
    """Fetch ABS CPI as republished in the RBA G1 statistical table."""
    frame = _fetch_rba_series(RBA_CPI_URL, RBA_CPI_SERIES_ID, "cpi_index", client)
    frame["period"] = frame["period_date"].dt.to_period("Q").astype(str)
    frame["source"] = f"rba_g1_{RBA_CPI_SERIES_ID}"
    frame["fetched_at"] = pd.Timestamp.now(tz="UTC")
    return frame[["period", "cpi_index", "period_date", "source", "fetched_at"]]


def fetch_rba_cash_rate(client: httpx.Client | None = None) -> pd.DataFrame:
    """Fetch the RBA cash-rate target from the F1 statistical table."""
    frame = _fetch_rba_series(
        RBA_CASH_RATE_URL,
        RBA_CASH_RATE_SERIES_ID,
        "cash_rate_target_pct",
        client,
    )
    frame["source"] = f"rba_f1_{RBA_CASH_RATE_SERIES_ID}"
    frame["fetched_at"] = pd.Timestamp.now(tz="UTC")
    return frame


def deflate_prices(
    prices: pd.Series,
    price_dates: pd.Series,
    base_period: str = "2023Q4",
    cpi_df: pd.DataFrame | None = None,
) -> pd.Series:
    """Express nominal prices in the selected quarter's Australian dollars."""
    cpi = fetch_abs_cpi() if cpi_df is None else cpi_df
    if cpi.empty:
        raise ValueError("CPI data is empty")

    base = pd.Period(base_period, freq="Q")
    mapping = dict(zip(pd.PeriodIndex(cpi["period"], freq="Q"), cpi["cpi_index"], strict=True))
    if base not in mapping:
        raise ValueError(f"Base CPI period {base_period} is unavailable")

    price_quarters = pd.PeriodIndex(pd.to_datetime(price_dates), freq="Q")
    missing = sorted({str(period) for period in price_quarters if period not in mapping})
    if missing:
        raise ValueError(f"CPI is unavailable for price periods: {', '.join(missing)}")
    price_cpi = pd.Series([mapping[period] for period in price_quarters], index=prices.index)
    return prices.astype(float) * (float(mapping[base]) / price_cpi.astype(float))


def load_economic_data_to_db(engine: Engine | None = None) -> dict[str, int | str]:
    """Fetch and replace the authoritative RBA CPI and cash-rate tables."""
    target_engine = engine or get_engine()
    with target_engine.begin() as connection:
        ensure_raw_schema(connection)

    cpi = fetch_abs_cpi()
    cash_rate = fetch_rba_cash_rate()
    cpi.to_sql("raw_cpi", target_engine, schema="raw", if_exists="replace", index=False)
    cash_rate.to_sql(
        "raw_rba_cash_rate",
        target_engine,
        schema="raw",
        if_exists="replace",
        index=False,
    )
    logger.info("Loaded %d CPI and %d cash-rate observations", len(cpi), len(cash_rate))
    return {
        "status": "success",
        "cpi_rows": len(cpi),
        "cash_rate_rows": len(cash_rate),
    }
