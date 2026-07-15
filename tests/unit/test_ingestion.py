"""Tests for canonical listing ingestion and temporal lineage."""

from datetime import date

import pandas as pd
import pytest

from src.ingestion.kaggle_loader import (
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
