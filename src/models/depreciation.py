"""Depreciation curve analysis for Australian vehicles.

Methodology:
- Fit price retention curves by segment (make/model group)
- Compare depreciation rates across vehicle categories
- Generate visual-friendly curve data for dashboard

Key insight for interviews:
Depreciation is the single largest cost of vehicle ownership.
Modelling it accurately is RedBook's core business value proposition.
"""

import logging
from typing import cast

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

logger = logging.getLogger(__name__)


def exponential_decay(age: np.ndarray, initial_value: float, decay_rate: float) -> np.ndarray:
    """Exponential depreciation model: V(t) = V0 * exp(-lambda * t)

    This is the standard parametric depreciation model.
    Most vehicles follow approximate exponential decay with:
    - Steep initial depreciation (year 1-3)
    - Flattening curve (year 5+)
    - Floor effect (base metal/utility value)
    """
    return cast(np.ndarray, initial_value * np.exp(-decay_rate * age))


def power_decay(age: np.ndarray, initial_value: float, exponent: float) -> np.ndarray:
    """Power-law depreciation: V(t) = V0 * (1 + t)^(-alpha)

    Better fits some premium segments where early depreciation is steeper.
    """
    return initial_value * np.power(1 + age, -exponent)


def compute_retention_curve(
    df: pd.DataFrame,
    segment_col: str = "brand",
    segment_value: str | None = None,
    max_age: int = 20,
) -> pd.DataFrame:
    """Compute price retention curve for a vehicle segment.

    Price retention = median price at age N / median price when new (age 0-1)

    Args:
        df: DataFrame with 'age' and 'price' columns
        segment_col: Column to segment by (brand, model, body_type)
        segment_value: Specific segment to analyse (None = all data)
        max_age: Maximum vehicle age to include

    Returns:
        DataFrame with age, median_price, retention_pct, sample_count
    """
    if segment_value:
        mask = df[segment_col] == segment_value
        df = df[mask]

    # Filter valid age range
    df = df[(df["age"] >= 0) & (df["age"] <= max_age) & (df["price"] > 0)]

    if df.empty:
        logger.warning(f"No data for segment: {segment_col}={segment_value}")
        return pd.DataFrame()

    # Compute median price by age
    curve_data = df.groupby("age")["price"].agg(["median", "mean", "count", "std"]).reset_index()
    curve_data.columns = ["age", "median_price", "mean_price", "sample_count", "price_std"]

    # Anchor retention to the youngest observed age bucket. Mixing age 0 and 1 medians
    # can make the age-0 point exceed 100%, which is misleading in the dashboard.
    reference_age = curve_data["age"].min()
    new_price = curve_data.loc[curve_data["age"] == reference_age, "median_price"].iloc[0]
    if pd.isna(new_price) or new_price <= 0:
        new_price = curve_data["median_price"].max()

    curve_data["retention_pct"] = (curve_data["median_price"] / new_price * 100).round(2)
    curve_data["segment"] = segment_value or "All"

    return curve_data


def fit_depreciation_model(
    curve_data: pd.DataFrame,
    model_type: str = "exponential",
) -> dict:
    """Fit parametric depreciation model to observed retention curve.

    Returns:
        Dictionary with fitted parameters, R-squared, and predictions.
    """
    age = curve_data["age"].values.astype(float)
    price = curve_data["median_price"].values.astype(float)

    # Remove zeros/nans
    valid = (price > 0) & ~np.isnan(price) & ~np.isnan(age)
    age = age[valid]
    price = price[valid]

    if len(age) < 3:
        return {"status": "insufficient_data", "n_points": len(age)}

    try:
        if model_type == "exponential":
            popt, pcov = curve_fit(
                exponential_decay,
                age,
                price,
                p0=[price[0], 0.15],  # Initial guess
                bounds=([0, 0.01], [price[0] * 2, 1.0]),
                maxfev=5000,
            )
            fitted = exponential_decay(age, *popt)
            params = {"initial_value": popt[0], "decay_rate": popt[1]}

        elif model_type == "power":
            popt, pcov = curve_fit(
                power_decay,
                age,
                price,
                p0=[price[0], 0.5],
                bounds=([0, 0.01], [price[0] * 2, 3.0]),
                maxfev=5000,
            )
            fitted = power_decay(age, *popt)
            params = {"initial_value": popt[0], "exponent": popt[1]}
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # R-squared
        ss_res = np.sum((price - fitted) ** 2)
        ss_tot = np.sum((price - np.mean(price)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return {
            "status": "success",
            "model_type": model_type,
            "params": params,
            "r_squared": round(r_squared, 4),
            "n_points": len(age),
            "predicted_values": fitted.tolist(),
        }
    except Exception as e:
        logger.warning(f"Curve fitting failed: {e}")
        return {"status": "fitting_failed", "error": str(e)}


def compute_all_depreciation_curves(
    df: pd.DataFrame,
    segments: list[str] | None = None,
    segment_col: str = "brand",
    min_samples: int = 50,
) -> dict[str, pd.DataFrame]:
    """Compute depreciation curves for all major segments.

    Args:
        df: Full listings DataFrame with 'age' and 'price'
        segments: Specific segments to compute (None = auto-select top by volume)
        segment_col: Column to segment by
        min_samples: Minimum listings required for a segment

    Returns:
        Dictionary mapping segment name to curve DataFrame
    """
    if segments is None:
        # Auto-select top segments by volume
        segment_counts = df[segment_col].value_counts()
        segments = segment_counts[segment_counts >= min_samples].index.tolist()[:15]

    curves = {}
    for segment in segments:
        curve = compute_retention_curve(df, segment_col, segment)
        if not curve.empty and len(curve) >= 3:
            curves[segment] = curve

    logger.info(f"Computed depreciation curves for {len(curves)} segments")
    return curves


def compare_segments(
    curves: dict[str, pd.DataFrame],
    at_ages: list[int] | None = None,
) -> pd.DataFrame:
    """Create comparison table of retention rates across segments.

    This is the visual centrepiece of the Depreciation Explorer page.
    """
    comparison_rows = []
    at_ages = at_ages or [1, 3, 5, 7, 10]

    for segment, curve in curves.items():
        row: dict[str, str | float | None] = {"segment": segment}
        for age in at_ages:
            age_data = curve[curve["age"] == age]
            if not age_data.empty:
                row[f"retention_{age}yr"] = age_data["retention_pct"].iloc[0]
            else:
                row[f"retention_{age}yr"] = None
        comparison_rows.append(row)

    comparison_df = pd.DataFrame(comparison_rows)
    comparison_df = comparison_df.sort_values("retention_3yr", ascending=False, na_position="last")

    return comparison_df
