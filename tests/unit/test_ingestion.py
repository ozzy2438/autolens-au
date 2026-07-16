"""Tests for canonical listing ingestion and temporal lineage."""

from datetime import date

import pandas as pd
import pytest

from src.ingestion.kaggle_loader import (
    _raw_listing_upsert_statements,
    add_lineage,
    deduplicate_listings,
    load_primary_dataset,
    load_secondary_dataset,
)


def test_primary_dataset_maps_and_cleans_canonical_schema(tmp_path):
    source = tmp_path / "primary.csv"
    pd.DataFrame(
        {
            "Brand": ["Toyota"],
            "Year": ["2020"],
            "Model": ["Camry"],
            "Kilometres": ["45,000 km"],
            "Price": ["$35,000"],
            "UsedOrNew": ["Used"],
            "BodyType": ["Sedan"],
        }
    ).to_csv(source, index=False)

    result = load_primary_dataset(source, snapshot_date="2026-07-01")

    assert result.loc[0, "kilometres"] == 45000
    assert result.loc[0, "price"] == 35000
    assert result.loc[0, "snapshot_date"] == date(2026, 7, 1)
    assert result.loc[0, "source"] == "kaggle_au_vehicle_prices"
    assert len(result.loc[0, "listing_fingerprint"]) == 64


def test_secondary_dataset_maps_documented_kaggle_columns(tmp_path):
    source = tmp_path / "secondary.csv"
    pd.DataFrame(
        {
            "ID": ["CAR-1"],
            "Name": ["Mazda CX-5 Maxx"],
            "Price": ["31,500"],
            "Brand": ["Mazda"],
            "Model": ["CX-5"],
            "Variant": ["Maxx"],
            "Year": [2019],
            "Gearbox": ["Automatic"],
            "Type": ["SUV"],
            "Fuel": ["Petrol"],
            "Status": ["Used"],
            "Kilometers": ["68,000"],
            "Seating Capacity": [5],
        }
    ).to_csv(source, index=False)

    result = load_secondary_dataset(source, snapshot_date="2026-07-01")

    assert result.loc[0, "source_record_id"] == "CAR-1"
    assert result.loc[0, "model"] == "CX-5"
    assert result.loc[0, "variant"] == "Maxx"
    assert result.loc[0, "body_type"] == "SUV"
    assert result.loc[0, "kilometres"] == 68000
    assert result.loc[0, "source"] == "kaggle_au_car_market"


def test_secondary_dataset_rejects_schema_drift(tmp_path):
    source = tmp_path / "secondary.csv"
    pd.DataFrame({"Brand": ["Mazda"], "Price": [30000]}).to_csv(source, index=False)

    with pytest.raises(ValueError, match="missing required canonical columns"):
        load_secondary_dataset(source)


def test_fingerprint_is_stable_across_snapshots():
    canonical = pd.DataFrame(
        {
            "brand": ["Toyota"],
            "model": ["Camry"],
            "year": [2020],
            "kilometres": [45000],
            "price": [35000],
        }
    )

    first = add_lineage(canonical, "source-a", "2026-07-01")
    second = add_lineage(canonical, "source-a", "2026-08-01")

    assert first.loc[0, "listing_fingerprint"] == second.loc[0, "listing_fingerprint"]
    assert first.loc[0, "snapshot_date"] != second.loc[0, "snapshot_date"]


def test_deduplication_keeps_most_complete_cross_source_record():
    sparse = pd.DataFrame(
        {
            "brand": ["Toyota"],
            "model": ["Camry"],
            "year": [2020],
            "kilometres": [45000],
            "price": [35000],
        }
    )
    complete = sparse.assign(body_type="Sedan", fuel_type="Petrol")
    first = add_lineage(sparse, "source-a", "2026-07-01")
    second = add_lineage(complete, "source-b", "2026-07-01")

    result = deduplicate_listings(pd.concat([first, second], ignore_index=True))

    assert len(result) == 1
    assert result.loc[0, "source"] == "source-b"
    assert result.loc[0, "body_type"] == "Sedan"


def test_snowflake_upsert_statements_avoid_postgresql_only_sql():
    statements = _raw_listing_upsert_statements("snowflake")
    joined = " ".join(statements)

    assert statements[0] == (
        "CREATE TABLE IF NOT EXISTS raw.raw_listings LIKE raw._raw_listings_batch"
    )
    assert "CREATE UNIQUE INDEX" not in joined
    assert "INCLUDING DEFAULTS" not in joined
    assert "AS existing" not in joined
    # Unquoted DDL stores uppercase identifiers, so quoted-lowercase
    # column references would not resolve on Snowflake.
    assert '"brand"' not in joined
    assert statements[-1] == "DROP TABLE raw._raw_listings_batch"


def test_postgresql_upsert_statements_keep_snapshot_unique_index():
    statements = _raw_listing_upsert_statements("postgresql")

    assert "(LIKE raw._raw_listings_batch INCLUDING DEFAULTS)" in statements[0]
    assert '"listing_fingerprint"' in " ".join(statements)
    assert statements[-1] == (
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_raw_listings_snapshot "
        "ON raw.raw_listings (listing_fingerprint, snapshot_date)"
    )


def test_upsert_statements_reject_unknown_dialects():
    with pytest.raises(ValueError, match="Unsupported database dialect"):
        _raw_listing_upsert_statements("sqlite")


def test_upsert_statements_replace_matching_snapshot_rows_for_both_dialects():
    for dialect in ("postgresql", "snowflake"):
        statements = _raw_listing_upsert_statements(dialect)
        delete = next(s for s in statements if s.startswith("DELETE FROM raw.raw_listings"))
        insert = next(s for s in statements if s.startswith("INSERT INTO raw.raw_listings"))

        assert "listing_fingerprint = batch.listing_fingerprint" in delete
        assert "snapshot_date = batch.snapshot_date" in delete
        assert "SELECT" in insert and "FROM raw._raw_listings_batch" in insert
