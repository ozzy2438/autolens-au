"""Train, evaluate, calibrate, and monitor the AutoLens AU valuation model."""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import MODEL_DIR, model_config
from src.models.evaluation import (
    compute_drift_metrics,
    evaluate_by_price_segment,
    evaluate_model,
    evaluate_prediction_intervals,
    out_of_time_split,
)
from src.models.hedonic_model import (
    ValuationModelBundle,
    calibrate_prediction_interval,
    load_model,
    prediction_bounds,
    prepare_training_data,
    save_model,
    train_baseline_model,
    train_lgbm_model,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _load_training_frame() -> pd.DataFrame:
    """Load canonical listing snapshots from PostgreSQL or the local Kaggle cache."""
    from config.database import get_engine

    try:
        frame = pd.read_sql("SELECT * FROM raw.raw_listings", get_engine())
    except Exception as database_error:
        logger.warning(
            "Database read failed: %s; trying the canonical local loader", database_error
        )
        from src.ingestion.kaggle_loader import load_primary_dataset, load_secondary_dataset

        primary = load_primary_dataset()
        secondary = load_secondary_dataset()
        frame = pd.concat([primary, secondary], ignore_index=True)
    if frame.empty:
        raise ValueError("No training data is available; run data ingestion first")
    return frame


def _validation_split(
    metadata: pd.DataFrame,
) -> tuple[pd.Index, pd.Index, str]:
    """Prefer genuine snapshot OOT; clearly label a single-snapshot fallback."""
    try:
        train_meta, test_meta = out_of_time_split(metadata)
        if len(train_meta) < 100 or len(test_meta) < 100:
            raise ValueError("Snapshot holdout is too small for stable evaluation")
        return train_meta.index, test_meta.index, "snapshot_out_of_time"
    except ValueError as error:
        logger.warning(
            "Genuine OOT unavailable (%s); using a random single-snapshot holdout", error
        )
        train_index, test_index = train_test_split(
            metadata.index,
            test_size=model_config.test_size,
            random_state=model_config.random_state,
        )
        return pd.Index(train_index), pd.Index(test_index), "random_holdout_single_snapshot"


def _latest_snapshot(metadata: pd.DataFrame) -> str | None:
    if "snapshot_date" not in metadata.columns:
        return None
    snapshots = pd.to_datetime(metadata["snapshot_date"], errors="coerce", utc=True).dropna()
    return snapshots.max().date().isoformat() if not snapshots.empty else None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def train_model() -> dict[str, Any]:
    """Train both models and persist a calibrated LightGBM artifact with metrics."""
    frame = _load_training_frame()
    features, target_log = prepare_training_data(frame)
    metadata = frame.loc[features.index]
    development_index, test_index, validation_strategy = _validation_split(metadata)

    fit_index, calibration_index = train_test_split(
        development_index,
        test_size=0.2,
        random_state=model_config.random_state,
    )
    X_fit, y_fit = features.loc[fit_index], target_log.loc[fit_index]
    X_calibration = features.loc[calibration_index]
    y_calibration = target_log.loc[calibration_index]
    X_test, y_test = features.loc[test_index], target_log.loc[test_index]

    baseline = train_baseline_model(X_fit, y_fit)
    lgbm = train_lgbm_model(X_fit, y_fit)
    interval_log_error = calibrate_prediction_interval(
        lgbm,
        X_calibration,
        y_calibration,
        confidence_level=model_config.prediction_interval,
    )

    baseline_predictions = np.expm1(baseline.predict(X_test))
    lgbm_log_predictions = lgbm.predict(X_test)
    lgbm_predictions = np.expm1(lgbm_log_predictions)
    actual_prices = np.expm1(y_test.to_numpy())
    lower_bounds, upper_bounds = prediction_bounds(lgbm_log_predictions, interval_log_error)

    baseline_metrics = evaluate_model(actual_prices, baseline_predictions)
    lgbm_metrics = evaluate_model(actual_prices, lgbm_predictions)
    interval_metrics = evaluate_prediction_intervals(
        actual_prices,
        lower_bounds,
        upper_bounds,
        target_coverage=model_config.prediction_interval,
    )
    segment_metrics = evaluate_by_price_segment(actual_prices, lgbm_predictions).to_dict(
        orient="records"
    )

    trained_at = datetime.now(UTC).isoformat()
    trained_through_snapshot = _latest_snapshot(metadata.loc[development_index])
    segment_frame = frame.loc[development_index].copy()
    segment_frame["brand"] = segment_frame["brand"].astype("string").str.strip().str.casefold()
    segment_frame["model"] = segment_frame["model"].astype("string").str.strip().str.casefold()
    segment_frame["price"] = pd.to_numeric(segment_frame["price"], errors="coerce")
    segment_medians = (
        segment_frame.dropna(subset=["brand", "model", "price"])
        .groupby(["brand", "model"])["price"]
        .median()
    )
    bundle = ValuationModelBundle(
        pipeline=lgbm,
        interval_log_error=interval_log_error,
        confidence_level=model_config.prediction_interval,
        version=model_config.version,
        trained_at=trained_at,
        validation_strategy=validation_strategy,
        trained_through_snapshot=trained_through_snapshot,
        segment_medians_aud={
            f"{brand}|{model}": float(median) for (brand, model), median in segment_medians.items()
        },
    )
    model_path = save_model(bundle)

    metrics: dict[str, Any] = {
        "model_version": model_config.version,
        "trained_at": trained_at,
        "trained_through_snapshot": trained_through_snapshot,
        "validation_strategy": validation_strategy,
        "baseline_metrics": baseline_metrics,
        "lgbm_metrics": lgbm_metrics,
        "prediction_interval_metrics": interval_metrics,
        "interval_log_error_quantile": interval_log_error,
        "segment_metrics": segment_metrics,
        "fit_samples": len(X_fit),
        "calibration_samples": len(X_calibration),
        "test_samples": len(X_test),
        "artifact": model_path.name,
    }
    _write_json(MODEL_DIR / "latest_metrics.json", metrics)
    logger.info(
        "Training complete: MAE=$%.0f, MdAPE=%.1f%%, interval coverage=%.1f%% (%s)",
        lgbm_metrics["overall"]["mae"],
        lgbm_metrics["overall"]["mdape"],
        interval_metrics["actual_coverage"] * 100,
        validation_strategy,
    )
    return metrics


def check_drift() -> bool:
    """Evaluate the current artifact only on snapshots newer than its baseline."""
    metrics_path = MODEL_DIR / "latest_metrics.json"
    if not metrics_path.exists() or not model_config.model_path.exists():
        logger.info("No measured baseline artifact exists; training is required")
        return True

    baseline = json.loads(metrics_path.read_text(encoding="utf-8"))
    try:
        model = load_model()
    except (OSError, TypeError, ValueError):
        logger.warning("Stored artifact is incompatible or unreadable; retraining is required")
        return True
    trained_through = model.trained_through_snapshot
    if trained_through is None:
        logger.info("Artifact has no snapshot boundary; waiting for a later snapshot")
        return False

    frame = _load_training_frame()
    snapshot_dates = pd.to_datetime(frame["snapshot_date"], errors="coerce", utc=True)
    fresh = frame.loc[snapshot_dates > pd.Timestamp(trained_through, tz="UTC")].copy()
    if fresh.empty:
        report: dict[str, Any] = {
            "status": "no_new_snapshot",
            "drift_detected": False,
            "trained_through_snapshot": trained_through,
            "evaluated_at": datetime.now(UTC).isoformat(),
        }
        _write_json(MODEL_DIR / "latest_drift.json", report)
        logger.info("No snapshot newer than %s; drift was not claimed or measured", trained_through)
        return False

    features, target_log = prepare_training_data(fresh)
    predictions = np.expm1(model.pipeline.predict(features))
    actual = np.expm1(target_log.to_numpy())
    current_metrics = evaluate_model(actual, predictions)
    report = compute_drift_metrics(
        current_metrics,
        baseline["lgbm_metrics"],
        threshold=model_config.drift_threshold,
    )
    report.update(
        {
            "status": "evaluated",
            "evaluated_rows": len(features),
            "trained_through_snapshot": trained_through,
            "latest_evaluated_snapshot": _latest_snapshot(fresh),
        }
    )
    _write_json(MODEL_DIR / "latest_drift.json", report)
    logger.info("Drift result: %s", report)
    return bool(report["drift_detected"])


def main() -> int:
    parser = argparse.ArgumentParser(description="AutoLens AU model training and monitoring")
    parser.add_argument("--check-drift", action="store_true", help="Evaluate newer snapshots")
    parser.add_argument("--force-retrain", action="store_true", help="Force model retraining")
    args = parser.parse_args()
    try:
        should_train = args.force_retrain or not args.check_drift or check_drift()
        if should_train:
            train_model()
    except Exception:
        logger.exception("Model workflow failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
