"""ABS Economic Data loader (CPI, RBA rates).

Sources:
- ABS Consumer Price Index: for deflating nominal vehicle prices to real AUD
- RBA Interest Rates: for understanding financing cost context

Used to:
- Adjust historical prices for inflation
- Provide economic context in the Market Monitor dashboard
- Enable "real vs nominal" price movement analysis
"""

import logging
from datetime import datetime
from typing import Optional

import httpx
import pandas as pd
from sqlalchemy import text

from config.settings import DATA_DIR
from config.database import get_engine

logger = logging.getLogger(__name__)

# ABS API endpoints (Time Series data)
ABS_CPI_URL = "https://api.data.abs.gov.au/data/CPI/1.10001.10.50.Q"
ABS_STAT_BASE = "https://api.data.abs.gov.au"

# RBA Statistical Tables
RBA_RATES_URL = "https://www.rba.gov.au/statistics/tables/csv/f1-data.csv"


def fetch_abs_cpi() -> pd.DataFrame:
    """Fetch Consumer Price Index data from ABS.
    
    Returns quarterly CPI (All Groups, Weighted Average of Eight Capital Cities).
    Used for deflating vehicle prices to real terms.
    """
    logger.info("Fetching ABS CPI data...")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                ABS_CPI_URL,
                headers={"Accept": "application/json"},
                params={"format": "jsondata"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        logger.warning(f"ABS API request failed: {e}. Using fallback CPI values.")
        return _get_fallback_cpi()
    
    # Parse ABS SDMX-JSON response
    try:
        observations = data["dataSets"][0]["observations"]
        time_periods = [
            dim["id"] 
            for dim in data["structure"]["dimensions"]["observation"][0]["values"]
        ]
        
        records = []
        for idx, period in enumerate(time_periods):
            key = str(idx)
            if key in observations:
                records.append({
                    "period": period,
                    "cpi_index": observations[key][0],
                })
        
        df = pd.DataFrame(records)
        df["period_date"] = pd.to_datetime(df["period"])
        df["source"] = "abs_cpi"
        df["fetched_at"] = pd.Timestamp.now(tz="UTC")
        
        logger.info(f"Fetched {len(df)} CPI observations")
        return df
    except (KeyError, IndexError) as e:
        logger.warning(f"Failed to parse ABS response: {e}. Using fallback.")
        return _get_fallback_cpi()


def _get_fallback_cpi() -> pd.DataFrame:
    """Fallback CPI values for when ABS API is unavailable.
    
    Based on published ABS CPI data (All Groups, Weighted Average).
    Base period: 2011-12 = 100.0
    """
    # Key quarterly CPI values (approximate, from published ABS data)
    data = [
        ("2020-Q1", 116.6), ("2020-Q2", 114.4), ("2020-Q3", 116.2), ("2020-Q4", 117.2),
        ("2021-Q1", 118.8), ("2021-Q2", 119.8), ("2021-Q3", 120.9), ("2021-Q4", 122.2),
        ("2022-Q1", 124.4), ("2022-Q2", 126.1), ("2022-Q3", 128.4), ("2022-Q4", 130.8),
        ("2023-Q1", 132.6), ("2023-Q2", 133.7), ("2023-Q3", 135.2), ("2023-Q4", 136.1),
        ("2024-Q1", 137.4), ("2024-Q2", 138.5), ("2024-Q3", 139.4), ("2024-Q4", 140.0),
        ("2025-Q1", 141.2), ("2025-Q2", 142.1), ("2025-Q3", 142.8), ("2025-Q4", 143.5),
        ("2026-Q1", 144.2), ("2026-Q2", 144.8),
    ]
    
    df = pd.DataFrame(data, columns=["period", "cpi_index"])
    df["period_date"] = pd.PeriodIndex(df["period"], freq="Q").to_timestamp()
    df["source"] = "abs_cpi_fallback"
    df["fetched_at"] = pd.Timestamp.now(tz="UTC")
    
    return df


def deflate_prices(
    prices: pd.Series,
    price_dates: pd.Series,
    base_period: str = "2023-Q4",
) -> pd.Series:
    """Deflate nominal prices to real AUD using CPI.
    
    Args:
        prices: Series of nominal prices in AUD
        price_dates: Series of dates corresponding to prices
        base_period: CPI reference period (prices expressed in this period's dollars)
        
    Returns:
        Series of real (inflation-adjusted) prices.
    """
    cpi_df = fetch_abs_cpi()
    
    if cpi_df.empty:
        logger.warning("No CPI data available, returning nominal prices")
        return prices
    
    # Get base period CPI
    base_cpi = cpi_df.loc[
        cpi_df["period"] == base_period, "cpi_index"
    ].iloc[0] if base_period in cpi_df["period"].values else cpi_df["cpi_index"].iloc[-1]
    
    # Map each price date to its quarter's CPI
    price_quarters = pd.PeriodIndex(price_dates, freq="Q")
    cpi_mapping = dict(zip(
        pd.PeriodIndex(cpi_df["period"], freq="Q"),
        cpi_df["cpi_index"]
    ))
    
    price_cpi = price_quarters.map(lambda q: cpi_mapping.get(q, base_cpi))
    
    # Real price = Nominal price * (Base CPI / Period CPI)
    real_prices = prices * (base_cpi / price_cpi)
    
    return real_prices


def load_economic_data_to_db() -> dict:
    """Load all economic context data to database."""
    engine = get_engine()
    stats = {}
    
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        conn.commit()
    
    # Load CPI
    cpi_df = fetch_abs_cpi()
    if not cpi_df.empty:
        cpi_df.to_sql(
            "raw_cpi",
            engine,
            schema="raw",
            if_exists="replace",
            index=False,
        )
        stats["cpi_rows"] = len(cpi_df)
    
    return stats
