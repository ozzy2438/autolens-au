"""Unit tests for authoritative reference-data loaders."""

from datetime import date

import httpx
import pandas as pd
import pytest

from scripts.setup_database import SCHEMA_SQL, _sql_statements
from src.ingestion.abs_economic import deflate_prices, parse_rba_series
from src.ingestion.bitre_vehicles import parse_bitre_vehicle_makes
from src.ingestion.qld_registrations import (
    discover_qld_resource_ids,
    fetch_qld_registration_activity,
)

RESOURCE_ID = "70b4944a-ad95-417c-9041-09151302a08e"


def _qld_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("package_show"):
        return httpx.Response(
            200,
            json={
                "success": True,
                "result": {
                    "resources": [
                        {
                            "id": RESOURCE_ID,
                            "name": "VEHICLE_REGISTRATION_NEW_AND_TRANSFERS_01",
                            "format": "CSV",
                            "state": "active",
                            "datastore_active": True,
                        },
                        {
                            "id": "not-a-uuid",
                            "name": "VEHICLE_REGISTRATION_NEW_AND_TRANSFERS_OLD",
                            "format": "CSV",
                            "state": "active",
                            "datastore_active": True,
                        },
                    ]
                },
            },
        )
    if request.url.path.endswith("datastore_search_sql"):
        assert '"RECORD_DATE"::timestamp' in request.url.params["sql"]
        return httpx.Response(
            200,
            json={
                "success": True,
                "result": {
                    "records": [
                        {
                            "activity_month": "2026-01-01T00:00:00",
                            "MAKE": "TOYOTA",
                            "MODEL": "RAV4",
                            "BADGE": "GX",
                            "BODY_SHAPE": "WAGON",
                            "FUEL_TYPE": "PETROL",
                            "TRANSACTION_TYPE": "NEW",
                            "activity_count": "14",
                        }
                    ]
                },
            },
        )
    return httpx.Response(404)


def test_qld_resource_discovery_and_aggregation() -> None:
    with httpx.Client(transport=httpx.MockTransport(_qld_handler)) as client:
        assert discover_qld_resource_ids(client) == [RESOURCE_ID]
        result = fetch_qld_registration_activity(since=date(2026, 1, 1), client=client)

    assert result.loc[0, "activity_count"] == 14
    assert result.loc[0, "make"] == "TOYOTA"
    assert result.loc[0, "source_resource_id"] == RESOURCE_ID


def test_rba_series_parser_and_deflation() -> None:
    content = "\n".join(
        [
            "RBA statistical table",
            "Series ID,GCPIAG",
            "31-Dec-2023,100.0",
            "31-Mar-2024,110.0",
            "not-a-date,ignored",
        ]
    )
    cpi = parse_rba_series(content, "GCPIAG", "cpi_index")
    cpi["period"] = cpi["period_date"].dt.to_period("Q").astype(str)
    real = deflate_prices(
        pd.Series([11000.0]),
        pd.Series([pd.Timestamp("2024-03-31")]),
        base_period="2023Q4",
        cpi_df=cpi,
    )
    assert real.iloc[0] == pytest.approx(10000.0)


def test_rba_series_parser_rejects_missing_series() -> None:
    with pytest.raises(ValueError, match="is missing"):
        parse_rba_series("Series ID,OTHER\n31-Mar-2024,1.0", "GCPIAG", "cpi_index")


def test_bitre_table_7_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    workbook_table = pd.DataFrame(
        {
            "Make": ["Toyota", "Mazda", "Total"],
            2025: ["1,000", "500", "1,500"],
            2024: ["900", "450", "1,350"],
            "Unnamed: 3": [None, None, None],
        }
    )
    monkeypatch.setattr(pd, "read_excel", lambda *_args, **_kwargs: workbook_table)

    result = parse_bitre_vehicle_makes(b"workbook")

    assert len(result) == 4
    assert set(result["make"]) == {"Toyota", "Mazda"}
    assert result["registered_vehicles"].sum() == 2850


def test_database_setup_does_not_drop_commented_statements() -> None:
    statements = _sql_statements(SCHEMA_SQL)
    assert statements[0] == "CREATE SCHEMA IF NOT EXISTS raw"
    assert any("raw.raw_qld_registration_activity" in statement for statement in statements)
    assert len(statements) >= 15
