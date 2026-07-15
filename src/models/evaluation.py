"""Model evaluation and monitoring for AutoLens AU.

Evaluation philosophy (from README):
- No perfect scores anywhere
- Segment-level reporting (cheap vs premium, high-km vs low-km)
- Out-of-time validation (train on past, test on future)
- Calibrated prediction intervals
- Honest limitation documentation

Why out-of-time splits matter for pricing:
Vehicle prices are non-stationary: market conditions shift, new models
launch, supply chains fluctuate. A random holdout split can leak temporal
information. Out-of-time splits simulate the actual production scenario:
train on historical data, evaluate on future data.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logger = logging.getLogger(__name__)


def median_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Median Absolute Percentage Error (MdAPE).
    
    More robust than MAPE for skewed price distributions.
    Less sensitive to outliers in the lower price range.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    
    # Exclude zero/near-zero actuals
    mask = y_true > 100
    y_true = y_true[mask]
    y_pred = y_pred[mask]
    
    if len(y_true) == 0:
        return float("nan")
    
    ape = np.abs((y_true - y_pred) / y_true) * 100
    return float(np.median(ape))


def evaluate_model(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    segment_labels: Optional[pd.Series] = None,
) -> Dict:
    """Comprehensive model evaluation with segment breakdowns.
    
    Returns overall metrics plus segment-level performance.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    
    # Overall metrics
    metrics = {
        "overall": {
            "mae": round(mean_absolute_error(y_true, y_pred), 2),
            "rmse": round(np.sqrt(mean_squared_error(y_true, y_pred)), 2),
            "r2": round(r2_score(y_true, y_pred), 4),
            "mdape": round(median_absolute_percentage_error(y_true, y_pred), 2),
            "n_samples": len(y_true),
            "mean_actual": round(float(np.mean(y_true)), 2),
            "mean_predicted": round(float(np.mean(y_pred)), 2),
        }
    }
    
    # Segment-level metrics
    if segment_labels is not None:
        metrics["segments"] = {}
        for segment in segment_labels.unique():
            mask = segment_labels == segment
            if mask.sum() < 10:  # Skip segments with too few samples
                continue
            
            seg_true = y_true[mask]
            seg_pred = y_pred[mask]
            
            metrics["segments"][segment] = {
                "mae": round(mean_absolute_error(seg_true, seg_pred), 2),
                "mdape": round(median_absolute_percentage_error(seg_true, seg_pred), 2),
                "n_samples": int(mask.sum()),
                "mean_price": round(float(np.mean(seg_true)), 2),
            }
    
    return metrics


def evaluate_by_price_segment(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    bins: Optional[List[float]] = None,
) -> pd.DataFrame:
    """Evaluate model performance across price segments.
    
    Segments: Budget (<$15k), Mid ($15k-$40k), Premium ($40k-$80k), Luxury (>$80k)
    """
    if bins is None:
        bins = [0, 15000, 40000, 80000, float("inf")]
    labels = ["Budget (<$15k)", "Mid ($15k-$40k)", "Premium ($40k-$80k)", "Luxury (>$80k)"]
    
    segments = pd.cut(y_true, bins=bins, labels=labels[:len(bins)-1])
    
    results = []
    for segment in segments.unique():
        if pd.isna(segment):
            continue
        mask = segments == segment
        seg_true = y_true[mask]
        seg_pred = y_pred[mask]
        
        results.append({
            "segment": str(segment),
            "n_samples": int(mask.sum()),
            "mae": round(mean_absolute_error(seg_true, seg_pred), 0),
            "mdape": round(median_absolute_percentage_error(seg_true, seg_pred), 2),
            "mean_actual": round(float(np.mean(seg_true)), 0),
        })
    
    return pd.DataFrame(results)


def evaluate_prediction_intervals(
    y_true: np.ndarray,
    lower_bounds: np.ndarray,
    upper_bounds: np.ndarray,
    target_coverage: float = 0.80,
) -> Dict:
    """Evaluate calibration of prediction intervals.
    
    A well-calibrated 80% PI should contain approximately 80% of actuals.
    """
    y_true = np.asarray(y_true)
    lower_bounds = np.asarray(lower_bounds)
    upper_bounds = np.asarray(upper_bounds)
    
    # Coverage: proportion of actuals within bounds
    in_bounds = (y_true >= lower_bounds) & (y_true <= upper_bounds)
    actual_coverage = float(np.mean(in_bounds))
    
    # Average interval width (as % of actual)
    interval_width = upper_bounds - lower_bounds
    relative_width = np.median(interval_width / y_true) * 100
    
    return {
        "target_coverage": target_coverage,
        "actual_coverage": round(actual_coverage, 4),
        "is_calibrated": abs(actual_coverage - target_coverage) < 0.05,
        "median_relative_width_pct": round(relative_width, 2),
        "n_samples": len(y_true),
    }


def out_of_time_split(
    df: pd.DataFrame,
    date_col: str = "year",
    train_cutoff: int = 2021,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split data by time for out-of-time validation.
    
    Train on listings from before cutoff year,
    test on listings from cutoff year onward.
    
    This simulates the production scenario: predict future prices
    based on historical patterns.
    """
    train = df[df[date_col] <= train_cutoff].copy()
    test = df[df[date_col] > train_cutoff].copy()
    
    logger.info(
        f"Out-of-time split: train={len(train)} (<=year {train_cutoff}), "
        f"test={len(test)} (>year {train_cutoff})"
    )
    
    return train, test


def compute_drift_metrics(
    current_metrics: Dict,
    baseline_metrics: Dict,
    threshold: float = 0.05,
) -> Dict:
    """Detect model performance drift.
    
    Compares current evaluation metrics against baseline.
    Drift threshold: 5% MAE degradation triggers retrain alert.
    """
    current_mae = current_metrics.get("overall", {}).get("mae", 0)
    baseline_mae = baseline_metrics.get("overall", {}).get("mae", 0)
    
    if baseline_mae == 0:
        return {"status": "no_baseline", "drift_detected": False}
    
    mae_change = (current_mae - baseline_mae) / baseline_mae
    
    return {
        "baseline_mae": baseline_mae,
        "current_mae": current_mae,
        "mae_change_pct": round(mae_change * 100, 2),
        "drift_detected": mae_change > threshold,
        "threshold_pct": threshold * 100,
        "recommendation": "RETRAIN" if mae_change > threshold else "MONITOR",
        "evaluated_at": datetime.now().isoformat(),
    }
