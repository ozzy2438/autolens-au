"""Tests for calibrated valuation artifacts and model-backed explanations."""

from datetime import UTC, datetime

import lightgbm as lgb
import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from src.api.schemas import ValuationRequest
from src.api.valuation_engine import ValuationEngine
from src.models.hedonic_model import (
    ValuationModelBundle,
    build_preprocessor,
    calibrate_prediction_interval,
    explain_prediction,
    predict_price,
    prepare_training_data,
)


@pytest.fixture(scope="module")
def calibrated_bundle() -> ValuationModelBundle:
    rows = 80
    raw = pd.DataFrame(
        {
            "brand": ["Toyota" if index % 2 == 0 else "Mazda" for index in range(rows)],
            "model": ["RAV4" if index % 2 == 0 else "CX-5" for index in range(rows)],
            "variant": ["GX" if index % 3 else "Sport" for index in range(rows)],
            "year": [2016 + index % 8 for index in range(rows)],
            "kilometres": [15000 + index * 1700 for index in range(rows)],
            "body_type": ["SUV"] * rows,
            "fuel_type": ["Petrol"] * rows,
            "transmission": ["Automatic"] * rows,
            "drive_type": ["AWD"] * rows,
            "condition": ["Used"] * rows,
            "location": ["Melbourne VIC"] * rows,
            "doors": [5] * rows,
            "seats": [5] * rows,
            "cylinders": [4] * rows,
            "snapshot_date": ["2026-07-01"] * rows,
        }
    )
    raw["price"] = (
        52000
        - (2026 - raw["year"]) * 3200
        - raw["kilometres"] * 0.07
        + np.where(raw["brand"] == "Toyota", 1800, 0)
    )
    features, target = prepare_training_data(raw)
    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            (
                "model",
                lgb.LGBMRegressor(
                    n_estimators=30,
                    learning_rate=0.1,
                    min_child_samples=5,
                    random_state=42,
                    verbose=-1,
                ),
            ),
        ]
    )
    pipeline.fit(features.iloc[:60], target.iloc[:60])
    interval = calibrate_prediction_interval(
        pipeline,
        features.iloc[60:70],
        target.iloc[60:70],
    )
    return ValuationModelBundle(
        pipeline=pipeline,
        interval_log_error=interval,
        confidence_level=0.8,
        version="test",
        trained_at=datetime.now(UTC).isoformat(),
        validation_strategy="random_holdout_single_snapshot",
        trained_through_snapshot="2026-07-01",
        segment_medians_aud={"toyota|rav4": 32000.0},
    )


def _vehicle() -> dict[str, object]:
    return {
        "brand": "Toyota",
        "model": "RAV4",
        "variant": "GX",
        "year": 2020,
        "kilometres": 60000,
        "body_type": "SUV",
        "fuel_type": "Petrol",
        "transmission": "Automatic",
        "drive_type": "AWD",
        "condition": "Used",
        "location": "Melbourne VIC",
        "doors": 5,
        "seats": 5,
        "cylinders": 4,
    }


def test_prediction_uses_artifact_calibration(calibrated_bundle: ValuationModelBundle) -> None:
    prediction = predict_price(calibrated_bundle, _vehicle())

    assert prediction["lower_bound"] < prediction["point_estimate"]
    assert prediction["upper_bound"] > prediction["point_estimate"]
    assert prediction["confidence_level"] == 0.8


def test_explanation_is_generated_by_tree_shap(
    calibrated_bundle: ValuationModelBundle,
) -> None:
    drivers = explain_prediction(calibrated_bundle, _vehicle())

    assert drivers
    assert all("TreeSHAP" in str(driver["description"]) for driver in drivers)
    assert all(float(driver["impact_aud"]) != 0 for driver in drivers)


def test_valuation_engine_uses_segment_median_and_shap(
    calibrated_bundle: ValuationModelBundle,
) -> None:
    engine = ValuationEngine()
    engine.model = calibrated_bundle
    result = engine.valuate(
        ValuationRequest(
            brand="Toyota",
            model="RAV4",
            variant="GX",
            year=2020,
            kilometres=60000,
            body_type="SUV",
            fuel_type="Petrol",
            transmission="Automatic",
            drive_type="AWD",
            location="Melbourne VIC",
        )
    )

    assert result.segment_median_aud == 32000.0
    assert result.price_drivers
