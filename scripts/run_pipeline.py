"""Command-line orchestration for AutoLens AU data ingestion."""

import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import test_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SOURCE_NAMES = ("kaggle", "fuel", "qld", "cpi", "bitre")


def run_source(
    source: str,
    *,
    download: bool = False,
    snapshot_date: date | None = None,
    since: date | None = None,
) -> dict[str, int | str]:
    """Dispatch exactly one named source to its ingestion function."""
    if source == "kaggle":
        from src.ingestion.kaggle_loader import run_ingestion

        return run_ingestion(download=download, snapshot_date=snapshot_date)
    if source == "fuel":
        from src.ingestion.nsw_fuelcheck import run_fuel_ingestion

        return run_fuel_ingestion()
    if source == "qld":
        from src.ingestion.qld_registrations import run_qld_ingestion

        return run_qld_ingestion(since=since)
    if source == "cpi":
        from src.ingestion.abs_economic import load_economic_data_to_db

        return load_economic_data_to_db()
    if source == "bitre":
        from src.ingestion.bitre_vehicles import run_bitre_ingestion

        return run_bitre_ingestion()
    raise ValueError(f"Unknown source: {source}")


def run_full_pipeline(
    *,
    sources: Sequence[str] = SOURCE_NAMES,
    download: bool = False,
    snapshot_date: date | None = None,
    since: date | None = None,
) -> dict[str, Any]:
    """Run requested sources and return a machine-readable success/failure summary."""
    results: dict[str, Any] = {
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "sources": {},
    }
    failed_sources: list[str] = []

    for source in sources:
        logger.info("Running source: %s", source)
        try:
            source_result = run_source(
                source,
                download=download,
                snapshot_date=snapshot_date,
                since=since,
            )
        except Exception as error:
            logger.exception("%s ingestion failed", source)
            source_result = {"status": "error", "error": str(error)}

        results["sources"][source] = source_result
        if source_result.get("status") == "error":
            failed_sources.append(source)

    results["completed_at"] = datetime.now(UTC).isoformat()
    results["failed_sources"] = failed_sources
    results["status"] = "failed" if failed_sources else "success"
    return results


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from error


def main() -> int:
    parser = argparse.ArgumentParser(description="AutoLens AU data ingestion")
    parser.add_argument(
        "--monthly-refresh",
        action="store_true",
        help="Download and snapshot every configured source",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download Kaggle files instead of using the local cache",
    )
    parser.add_argument("--source", choices=SOURCE_NAMES, help="Run exactly one source")
    parser.add_argument(
        "--snapshot-date",
        type=_parse_date,
        help="Listing snapshot date (YYYY-MM-DD; defaults to current UTC date)",
    )
    parser.add_argument(
        "--since",
        type=_parse_date,
        help="Earliest QLD activity date (YYYY-MM-DD; defaults to two years)",
    )
    args = parser.parse_args()

    logger.info("Testing database connection")
    if not test_connection():
        logger.error("Database connection failed; check DATABASE_URL or DB_* settings")
        return 1

    sources = (args.source,) if args.source else SOURCE_NAMES
    result = run_full_pipeline(
        sources=sources,
        download=args.download or args.monthly_refresh,
        snapshot_date=args.snapshot_date,
        since=args.since,
    )
    logger.info("Pipeline result: %s", result)
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
