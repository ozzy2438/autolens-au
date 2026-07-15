"""Hedonic vehicle-pricing model, calibrated intervals, and SHAP explanations."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config.settings import MODEL_DIR, model_config

logger = logging.getLogger(__name__)

NUMERIC_FEATURES = ["age", "kilometres", "doors", "seats", "cylinders", "age_km_interaction"]
CATEGORICAL_FEATURES = [
    "brand",
    "model",
    "variant",
    "body_type",
    "fuel_type",
    "transmission",
    "drive_type",
    "condition",
    "state",
]


@dataclass
class ValuationModelBundle:
    """Persisted production artifact and the evidence needed to interpret it."""

    pipeline: Pipeline
    interval_log_error: float
    confidence_level: float
    version: str
    trained_at: str
    validation_strategy: str
    trained_through_snapshot: str | None
    segment_medians_aud: dict[str, float]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create reproducible model features without using price information."""
    frame = df.copy()
    manufacture_year = pd.to_numeric(frame["year"], errors="coerce")
    reference_year = pd.Series(datetime.now(UTC).year, index=frame.index, dtype="float64")
    for snapshot_column in ("snapshot_date", "listing_snapshot_date"):
        if snapshot_column in frame.columns:
            snapshot_year = pd.to_datetime(frame[snapshot_column], errors="coerce").dt.year
            reference_year = snapshot_year.fillna(reference_year).astype("float64")
            break

    frame["age"] = (reference_year - manufacture_year).clip(lower=0, upper=50)
    frame["kilometres"] = pd.to_numeric(frame.get("kilometres"), errors="coerce")
    frame["age_km_interaction"] = frame["age"] * frame["kilometres"].fillna(0) / 10000

    if "location" in frame.columns:
        frame["state"] = (
            frame["location"]
            .astype("string")
            .str.extract(r"(?i)\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\b", expand=False)
        )
    else:
        frame["state"] = "Unknown"

    for column in CATEGORICAL_FEATURES:
        if column not in frame.columns:
            frame[column] = "Unknown"
        frame[column] = frame[column].astype("string").str.strip().str.title()
        frame[column] = frame[column].fillna("Unknown").replace("", "Unknown")

    brand_map = {
        "Mercedesbenz": "Mercedes-Benz",
        "Mercedes Benz": "Mercedes-Benz",
        "Bmw": "BMW",
        "Vw": "Volkswagen",
        "Landrover": "Land Rover",
    }
    frame["brand"] = frame["brand"].replace(brand_map)

    for column in NUMERIC_FEATURES:
        if column not in frame.columns:
            frame[column] = np.nan
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def build_preprocessor() -> ColumnTransformer:
    """Build the shared preprocessing pipeline."""
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
            (
                "encoder",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False, max_categories=50),
            ),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def prepare_training_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Filter invalid records and return model features with log-price target."""
    frame = engineer_features(df)
    prices = pd.to_numeric(frame["price"], errors="coerce")
    years = pd.to_numeric(frame["year"], errors="coerce")
    reference_year = datetime.now(UTC).year
    mask = (
        prices.notna()
        & prices.between(1000, 500000, inclusive="neither")
        & years.notna()
        & years.between(1980, reference_year + 1)
    )
    frame = frame.loc[mask].copy()
    target = np.log1p(prices.loc[mask]).astype(float)
    features = frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    if features.empty:
        raise ValueError("No valid vehicle listings are available for training")
    logger.info("Training data: %d samples, %d features", len(features), len(features.columns))
    return features, target


def train_baseline_model(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Train a regularised linear baseline on log price."""
    pipeline = Pipeline([("preprocessor", build_preprocessor()), ("model", Ridge(alpha=1.0))])
    pipeline.fit(X, y)
    return pipeline


def train_lgbm_model(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Train the primary LightGBM model on log price."""
    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("model", lgb.LGBMRegressor(**model_config.lgbm_params)),
        ]
    )
    pipeline.fit(X, y)
    return pipeline


def calibrate_prediction_interval(
    model: Pipeline,
    X_calibration: pd.DataFrame,
    y_calibration_log: pd.Series,
    confidence_level: float = 0.80,
) -> float:
    """Fit a split-conformal absolute log-error quantile on held-out data."""
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1")
    if X_calibration.empty:
        raise ValueError("Calibration data is empty")
    residuals = np.abs(np.asarray(y_calibration_log) - model.predict(X_calibration))
    # Finite-sample conformal quantile, capped at 1.0 for small calibration sets.
    quantile_level = min(1.0, np.ceil((len(residuals) + 1) * confidence_level) / len(residuals))
    return float(np.quantile(residuals, quantile_level, method="higher"))


def prediction_bounds(
    log_predictions: np.ndarray,
    interval_log_error: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert symmetric log-error calibration into positive AUD bounds."""
    predictions = np.asarray(log_predictions, dtype=float)
    lower = np.maximum(0, np.expm1(predictions - interval_log_error))
    upper = np.expm1(predictions + interval_log_error)
    return lower, upper


def _model_input(vehicle_data: dict[str, Any]) -> pd.DataFrame:
    frame = engineer_features(pd.DataFrame([vehicle_data]))
    return frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES]


def predict_price(
    model: ValuationModelBundle | Pipeline,
    vehicle_data: dict[str, Any],
    return_interval: bool = True,
) -> dict[str, float | str]:
    """Generate a point estimate and, for calibrated bundles, an interval."""
    pipeline = model.pipeline if isinstance(model, ValuationModelBundle) else model
    log_prediction = float(pipeline.predict(_model_input(vehicle_data))[0])
    point_estimate = float(np.expm1(log_prediction))
    result: dict[str, float | str] = {
        "point_estimate": round(point_estimate, 0),
        "currency": "AUD",
    }
    if return_interval:
        if not isinstance(model, ValuationModelBundle):
            raise ValueError("Prediction intervals require a calibrated model bundle")
        lower, upper = prediction_bounds(
            np.array([log_prediction]),
            model.interval_log_error,
        )
        result.update(
            {
                "lower_bound": round(float(lower[0]), 0),
                "upper_bound": round(float(upper[0]), 0),
                "confidence_level": model.confidence_level,
            }
        )
    return result


def _feature_label(encoded_name: str) -> str:
    clean = encoded_name.removeprefix("num__").removeprefix("cat__")
    return clean.replace("_", " ").title()


def explain_prediction(
    model: ValuationModelBundle,
    vehicle_data: dict[str, Any],
    top_n: int = 5,
) -> list[dict[str, float | str]]:
    """Return actual local TreeSHAP contributions for one valuation."""
    features = _model_input(vehicle_data)
    preprocessor: ColumnTransformer = model.pipeline.named_steps["preprocessor"]
    estimator: lgb.LGBMRegressor = model.pipeline.named_steps["model"]
    transformed = preprocessor.transform(features)
    explanation = shap.TreeExplainer(estimator)(transformed)
    values = np.asarray(explanation.values)[0]
    encoded_names = preprocessor.get_feature_names_out()
    point_estimate = float(np.expm1(estimator.predict(transformed)[0]))

    order = np.argsort(np.abs(values))[::-1][:top_n]
    drivers: list[dict[str, float | str]] = []
    for index in order:
        shap_value = float(values[index])
        impact_aud = point_estimate * (float(np.exp(shap_value)) - 1)
        label = _feature_label(str(encoded_names[index]))
        drivers.append(
            {
                "feature": label,
                "impact_aud": round(impact_aud, 2),
                "direction": "positive" if shap_value >= 0 else "negative",
                "description": f"Local TreeSHAP contribution from {label}",
            }
        )
    return drivers


def save_model(model: ValuationModelBundle, version: str | None = None) -> Path:
    """Persist a versioned calibrated artifact and update the latest pointer."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    version = version or model.version
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    versioned_path = MODEL_DIR / f"hedonic_model_v{version}_{timestamp}.joblib"
    latest_path = MODEL_DIR / "hedonic_model_latest.joblib"
    joblib.dump(model, versioned_path)
    joblib.dump(model, latest_path)
    logger.info("Model saved: %s", versioned_path)
    return versioned_path


def load_model(path: Path | None = None) -> ValuationModelBundle:
    """Load and validate the current calibrated artifact."""
    model_path = path or model_config.model_path
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found at {model_path}")
    model = joblib.load(model_path)
    if not isinstance(model, ValuationModelBundle):
        raise TypeError("Model artifact predates calibrated bundle format; retraining is required")
    return model
