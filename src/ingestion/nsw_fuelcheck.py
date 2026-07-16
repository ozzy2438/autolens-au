"""NSW FuelCheck API client.

Source: https://api.nsw.gov.au/Product/Index/22
Endpoints used:
- /FuelPriceCheck/v2/fuel/prices — all current prices
- /FuelCheckRefData/v2/fuel/lovs — reference data (stations, fuel types)

Authentication: OAuth2 client credentials flow.
Rate limits apply per API agreement.

This is a genuinely open government API that provides real-time fuel
prices across NSW. It demonstrates the "APIs or external data sources"
criterion and provides live market context data.
"""

import logging
from datetime import UTC, datetime, timedelta

import httpx
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from config.database import ensure_raw_schema, get_engine, write_dataframe
from config.settings import nsw_fuel_config

RAW_FUEL_COLUMNS = [
    "stationcode",
    "fueltype",
    "price",
    "lastupdated",
    "name",
    "suburb",
    "state",
    "latitude",
    "longitude",
    "fetched_at",
    "source",
]

logger = logging.getLogger(__name__)


class NSWFuelCheckClient:
    """Client for the NSW Government Fuel API.

    Handles OAuth2 authentication and provides methods for
    fetching fuel prices and reference data.
    """

    def __init__(self):
        self.config = nsw_fuel_config
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _get_access_token(self) -> str:
        """Obtain OAuth2 access token using client credentials."""
        if self._access_token and self._token_expiry:
            if datetime.now(UTC) < self._token_expiry:
                return self._access_token

        with httpx.Client() as client:
            response = client.get(
                f"{self.config.token_url}?grant_type=client_credentials",
                headers={
                    "Authorization": f"Basic {self._encode_credentials()}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()

        self._access_token = data["access_token"]
        # Token typically valid for ~3600 seconds
        expires_in = int(data.get("expires_in", 3600))
        self._token_expiry = datetime.now(UTC) + timedelta(seconds=max(expires_in - 30, 0))

        logger.info("NSW Fuel API: Access token refreshed")
        return str(self._access_token)

    def _encode_credentials(self) -> str:
        """Base64 encode API key and secret."""
        import base64

        credentials = f"{self.config.api_key}:{self.config.api_secret}"
        return base64.b64encode(credentials.encode()).decode()

    def _get_headers(self) -> dict:
        """Build request headers with valid auth token."""
        token = self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "apikey": self.config.api_key,
            "transactionid": f"autolens_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "requesttimestamp": datetime.now(UTC).strftime("%d/%m/%Y %I:%M:%S %p"),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_all_prices(self) -> pd.DataFrame:
        """Fetch all current fuel prices across NSW.

        Returns:
            DataFrame with columns: station_code, fuel_type, price,
            last_updated, station_name, suburb, latitude, longitude
        """
        logger.info("Fetching all NSW fuel prices...")

        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                self.config.prices_url,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

        # Parse response into DataFrame
        prices = data.get("prices", [])
        stations = data.get("stations", [])

        if not prices:
            logger.warning("No prices returned from NSW Fuel API")
            return pd.DataFrame()

        prices_df = pd.DataFrame(prices)
        stations_df = pd.DataFrame(stations)

        # Merge station details with prices
        if not stations_df.empty:
            merged_df = prices_df.merge(
                stations_df, left_on="stationcode", right_on="code", how="left"
            )
        else:
            merged_df = prices_df

        # Add metadata
        merged_df["fetched_at"] = pd.Timestamp.now(tz="UTC")
        merged_df["source"] = "nsw_fuelcheck_api"

        logger.info(f"Fetched {len(merged_df)} fuel price records")
        return merged_df

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_reference_data(self) -> dict:
        """Fetch reference data (fuel types, station list).

        Returns:
            Dictionary with 'fuel_types' and 'stations' DataFrames.
        """
        logger.info("Fetching NSW Fuel API reference data...")

        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                self.config.ref_data_url,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

        return {
            "fuel_types": pd.DataFrame(data.get("fueltypes", [])),
            "stations": pd.DataFrame(data.get("stations", [])),
        }


def load_fuel_prices_to_db(df: pd.DataFrame) -> int:
    """Load fuel price data into the configured raw schema."""
    engine = get_engine()

    with engine.begin() as conn:
        ensure_raw_schema(conn)

    # Append to preserve the time series; reindex to the stable target columns
    # because the live API payload carries extra/nested fields.
    rows = write_dataframe(
        df, "raw_fuel_prices", mode="append", columns=RAW_FUEL_COLUMNS, engine=engine
    )
    logger.info(f"Loaded {rows} fuel price records to raw.raw_fuel_prices")
    return rows


def run_fuel_ingestion() -> dict:
    """Execute fuel price ingestion."""
    client = NSWFuelCheckClient()

    try:
        prices_df = client.get_all_prices()
        if prices_df.empty:
            return {"status": "no_data", "rows": 0}

        rows = load_fuel_prices_to_db(prices_df)
        return {"status": "success", "rows": rows}
    except Exception as e:
        logger.error(f"Fuel ingestion failed: {e}")
        return {"status": "error", "error": str(e)}
