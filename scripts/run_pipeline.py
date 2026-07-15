"""Data pipeline orchestration script.

Runs the full ingestion pipeline:
1. Load Kaggle datasets (if available locally or download)
2. Fetch NSW fuel prices (live API)
3. Load QLD registration data
4. Load economic context data (CPI)

Usage:
    python scripts/run_pipeline.py                 # Full pipeline
    python scripts/run_pipeline.py --monthly-refresh  # Monthly refresh mode
    python scripts/run_pipeline.py --source fuel   # Single source only
"""

import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import test_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_full_pipeline(download: bool = False) -> dict:
    """Execute the complete data pipeline."""
    results = {
        "started_at": datetime.now().isoformat(),
        "sources": {},
    }
    
    # 1. Kaggle listings
    logger.info("=" * 60)
    logger.info("Step 1/4: Kaggle vehicle listings")
    logger.info("=" * 60)
    try:
        from src.ingestion.kaggle_loader import run_ingestion
        results["sources"]["kaggle"] = run_ingestion(download=download)
    except Exception as e:
        logger.error(f"Kaggle ingestion failed: {e}")
        results["sources"]["kaggle"] = {"status": "error", "error": str(e)}
    
    # 2. NSW Fuel prices
    logger.info("=" * 60)
    logger.info("Step 2/4: NSW Fuel prices (live API)")
    logger.info("=" * 60)
    try:
        from src.ingestion.nsw_fuelcheck import run_fuel_ingestion
        results["sources"]["nsw_fuel"] = run_fuel_ingestion()
    except Exception as e:
        logger.error(f"NSW Fuel ingestion failed: {e}")
        results["sources"]["nsw_fuel"] = {"status": "error", "error": str(e)}
    
    # 3. QLD Registrations
    logger.info("=" * 60)
    logger.info("Step 3/4: QLD vehicle registrations")
    logger.info("=" * 60)
    try:
        from src.ingestion.qld_registrations import run_qld_ingestion
        results["sources"]["qld_rego"] = run_qld_ingestion(download=download)
    except Exception as e:
        logger.error(f"QLD registration ingestion failed: {e}")
        results["sources"]["qld_rego"] = {"status": "error", "error": str(e)}
    
    # 4. Economic data (CPI)
    logger.info("=" * 60)
    logger.info("Step 4/4: ABS economic data (CPI)")
    logger.info("=" * 60)
    try:
        from src.ingestion.abs_economic import load_economic_data_to_db
        results["sources"]["abs_cpi"] = load_economic_data_to_db()
    except Exception as e:
        logger.error(f"Economic data ingestion failed: {e}")
        results["sources"]["abs_cpi"] = {"status": "error", "error": str(e)}
    
    results["completed_at"] = datetime.now().isoformat()
    
    # Summary
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"Results: {results}")
    logger.info("=" * 60)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="AutoLens AU Data Pipeline")
    parser.add_argument(
        "--monthly-refresh", action="store_true",
        help="Run in monthly refresh mode (skip re-download of static sources)"
    )
    parser.add_argument(
        "--download", action="store_true",
        help="Download fresh data from external sources"
    )
    parser.add_argument(
        "--source", type=str, choices=["kaggle", "fuel", "qld", "cpi"],
        help="Run only a specific source"
    )
    
    args = parser.parse_args()
    
    # Test database connection first
    logger.info("Testing database connection...")
    if not test_connection():
        logger.error("Database connection failed. Check configuration.")
        sys.exit(1)
    logger.info("Database connection OK.")
    
    if args.source:
        logger.info(f"Running single source: {args.source}")
        # Run individual source (implementation would go here)
    else:
        download = args.download and not args.monthly_refresh
        run_full_pipeline(download=download)


if __name__ == "__main__":
    main()
