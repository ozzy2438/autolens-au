"""Model training script.

Usage:
    python scripts/train_model.py              # Train new model
    python scripts/train_model.py --check-drift    # Check drift, retrain if needed
    python scripts/train_model.py --force-retrain  # Force retrain regardless
"""

import sys
import argparse
import logging
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import MODEL_DIR, model_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def train_model():
    """Train the hedonic pricing model."""
    from config.database import get_engine
    from src.models.hedonic_model import (
        prepare_training_data,
        train_baseline_model,
        train_lgbm_model,
        save_model,
    )
    from src.models.evaluation import (
        evaluate_model,
        evaluate_by_price_segment,
        out_of_time_split,
    )
    
    import pandas as pd
    import numpy as np
    
    logger.info("Loading training data from database...")
    engine = get_engine()
    
    try:
        df = pd.read_sql("SELECT * FROM raw.raw_listings", engine)
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        logger.info("Attempting to load from CSV fallback...")
        data_path = Path("data/raw/Australian Vehicle Prices.csv")
        if data_path.exists():
            df = pd.read_csv(data_path)
        else:
            logger.error("No data available. Run the pipeline first.")
            sys.exit(1)
    
    logger.info(f"Loaded {len(df)} records")
    
    # Prepare features
    X, y = prepare_training_data(df)
    
    # Out-of-time split
    if "year" in df.columns:
        X_with_year = X.copy()
        X_with_year["year"] = df.loc[X.index, "year"] if "year" in df.columns else 2020
        train_mask = X_with_year["year"] <= 2021
        test_mask = X_with_year["year"] > 2021
        
        X_train, y_train = X[train_mask], y[train_mask]
        X_test, y_test = X[test_mask], y[test_mask]
        
        if len(X_test) < 100:
            # Not enough future data; use random split
            from sklearn.model_selection import train_test_split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            logger.info("Using random split (insufficient future data for OOT)")
        else:
            logger.info(f"Using out-of-time split: train={len(X_train)}, test={len(X_test)}")
    else:
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
    
    # Train baseline
    logger.info("Training baseline model (Ridge)...")
    baseline = train_baseline_model(X_train, y_train)
    baseline_pred = baseline.predict(X_test)
    
    # Train LightGBM
    logger.info("Training LightGBM model...")
    lgbm = train_lgbm_model(X_train, y_train)
    lgbm_pred = lgbm.predict(X_test)
    
    # Convert from log scale for evaluation
    y_test_actual = np.expm1(y_test)
    baseline_actual = np.expm1(baseline_pred)
    lgbm_actual = np.expm1(lgbm_pred)
    
    # Evaluate
    logger.info("\n" + "=" * 60)
    logger.info("MODEL EVALUATION RESULTS")
    logger.info("=" * 60)
    
    baseline_metrics = evaluate_model(y_test_actual, baseline_actual)
    lgbm_metrics = evaluate_model(y_test_actual, lgbm_actual)
    
    logger.info(f"Baseline (Ridge): MAE=${baseline_metrics['overall']['mae']:,.0f}, MdAPE={baseline_metrics['overall']['mdape']:.1f}%")
    logger.info(f"LightGBM: MAE=${lgbm_metrics['overall']['mae']:,.0f}, MdAPE={lgbm_metrics['overall']['mdape']:.1f}%")
    
    # Segment evaluation
    segment_results = evaluate_by_price_segment(y_test_actual, lgbm_actual)
    logger.info(f"\nSegment Performance:\n{segment_results.to_string()}")
    
    # Save the best model (LightGBM)
    model_path = save_model(lgbm)
    
    # Save metrics
    metrics_path = MODEL_DIR / "latest_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump({
            "trained_at": datetime.now().isoformat(),
            "baseline_metrics": baseline_metrics,
            "lgbm_metrics": lgbm_metrics,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
        }, f, indent=2, default=str)
    
    logger.info(f"\nModel saved to: {model_path}")
    logger.info(f"Metrics saved to: {metrics_path}")
    logger.info("Training complete!")


def check_drift():
    """Check if model performance has drifted."""
    metrics_path = MODEL_DIR / "latest_metrics.json"
    if not metrics_path.exists():
        logger.info("No baseline metrics found. Training new model.")
        train_model()
        return
    
    # TODO: Evaluate current model on new data and compare
    logger.info("Drift check: would compare current vs baseline metrics")
    logger.info("No drift detected (placeholder)")


def main():
    parser = argparse.ArgumentParser(description="AutoLens AU Model Training")
    parser.add_argument("--check-drift", action="store_true", help="Check for model drift")
    parser.add_argument("--force-retrain", action="store_true", help="Force model retrain")
    
    args = parser.parse_args()
    
    if args.check_drift and not args.force_retrain:
        check_drift()
    else:
        train_model()


if __name__ == "__main__":
    main()
