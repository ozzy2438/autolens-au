"""Residual Value estimation for Australian vehicles.

Residual Value = Predicted retained value at a future time point.
This is the core commercial product that companies like RedBook sell.

Methodology:
- Uses fitted depreciation curves to project forward
- Estimates 3-year residual value % for each model group
- Provides uncertainty bands (wider where data is sparse)

Key metrics:
- Residual Value % = Predicted future price / Current price * 100
- Applied at the make/model/age cohort level
"""

import logging

import numpy as np
import pandas as pd

from src.models.depreciation import (
    compute_retention_curve,
    fit_depreciation_model,
)

logger = logging.getLogger(__name__)

# Default projection horizons
DEFAULT_HORIZONS = [1, 2, 3, 5]  # Years ahead


def estimate_residual_value(
    current_price: float,
    current_age: int,
    decay_rate: float,
    horizon_years: int = 3,
    uncertainty_factor: float = 0.1,
) -> dict:
    """Estimate residual value for a single vehicle.

    Args:
        current_price: Current estimated market value (AUD)
        current_age: Current vehicle age in years
        decay_rate: Fitted exponential decay rate for this segment
        horizon_years: Years into future to project
        uncertainty_factor: Base uncertainty (wider for sparse segments)

    Returns:
        Dictionary with residual value estimates and uncertainty bands.
    """
    # Projected value using exponential decay
    # V(t+h) = V(t) * exp(-lambda * h)
    retention_factor = np.exp(-decay_rate * horizon_years)
    projected_value = current_price * retention_factor

    # Residual value percentage
    rv_pct = retention_factor * 100

    # Uncertainty increases with:
    # - Longer projection horizon
    # - Higher vehicle age (less data for old cars)
    # - Higher base uncertainty (sparse segments)
    age_uncertainty = min(0.02 * current_age, 0.15)  # Up to 15% from age
    horizon_uncertainty = 0.03 * horizon_years  # 3% per year projected
    total_uncertainty = uncertainty_factor + age_uncertainty + horizon_uncertainty

    lower_bound = projected_value * (1 - total_uncertainty)
    upper_bound = projected_value * (1 + total_uncertainty)

    return {
        "current_price_aud": round(current_price, 0),
        "current_age_years": current_age,
        "projection_horizon_years": horizon_years,
        "projected_value_aud": round(projected_value, 0),
        "residual_value_pct": round(rv_pct, 2),
        "lower_bound_aud": round(lower_bound, 0),
        "upper_bound_aud": round(upper_bound, 0),
        "uncertainty_pct": round(total_uncertainty * 100, 2),
        "confidence_level": 0.80,
    }


def compute_segment_residual_values(
    df: pd.DataFrame,
    segment_col: str = "brand",
    horizon_years: int = 3,
    min_samples: int = 30,
) -> pd.DataFrame:
    """Compute residual value estimates for all segments.

    Returns a DataFrame with 3-year (or custom horizon) residual value
    estimates and uncertainty bands for each segment.
    """
    segments = df[segment_col].value_counts()
    segments = segments[segments >= min_samples].index.tolist()

    results = []

    for segment in segments:
        segment_df = df[df[segment_col] == segment]

        # Fit depreciation model for this segment
        curve = compute_retention_curve(segment_df, segment_col, segment)
        if curve.empty or len(curve) < 3:
            continue

        fit_result = fit_depreciation_model(curve, model_type="exponential")

        if fit_result["status"] != "success":
            continue

        decay_rate = fit_result["params"]["decay_rate"]

        # Calculate uncertainty factor based on data density
        n_samples = len(segment_df)
        uncertainty_factor = max(0.05, 0.20 - 0.001 * n_samples)  # More data = less uncertainty

        # Compute RV for a typical 3-year-old vehicle
        median_price_new = segment_df[segment_df["age"] <= 1]["price"].median()
        if pd.isna(median_price_new):
            median_price_new = segment_df["price"].median()

        rv_estimate = estimate_residual_value(
            current_price=median_price_new,
            current_age=0,
            decay_rate=decay_rate,
            horizon_years=horizon_years,
            uncertainty_factor=uncertainty_factor,
        )

        rv_estimate["segment"] = segment
        rv_estimate["segment_type"] = segment_col
        rv_estimate["sample_count"] = n_samples
        rv_estimate["decay_rate"] = round(decay_rate, 4)
        rv_estimate["model_r_squared"] = fit_result["r_squared"]

        results.append(rv_estimate)

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values("residual_value_pct", ascending=False)

    logger.info(f"Computed residual values for {len(results_df)} segments")
    return results_df


def residual_value_summary(rv_df: pd.DataFrame) -> dict:
    """Generate summary statistics for residual value analysis."""
    if rv_df.empty:
        return {"status": "no_data"}

    return {
        "segments_analysed": len(rv_df),
        "median_rv_pct": round(rv_df["residual_value_pct"].median(), 2),
        "best_rv_segment": rv_df.iloc[0]["segment"],
        "best_rv_pct": rv_df.iloc[0]["residual_value_pct"],
        "worst_rv_segment": rv_df.iloc[-1]["segment"],
        "worst_rv_pct": rv_df.iloc[-1]["residual_value_pct"],
        "mean_uncertainty_pct": round(rv_df["uncertainty_pct"].mean(), 2),
    }
