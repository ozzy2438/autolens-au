"""Create dashboard/changelog evidence from completed pipeline and dbt artifacts."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def build_refresh_status(
    pipeline: dict[str, Any],
    dbt_results: dict[str, Any],
    model_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate upstream evidence and produce the single operational status object."""
    if pipeline.get("status") != "success":
        raise ValueError("Cannot record a successful refresh from a failed pipeline result")

    results = dbt_results.get("results", [])
    failed = [result for result in results if result.get("status") in {"error", "fail"}]
    if failed:
        raise ValueError("Cannot record a successful refresh when dbt has failed nodes")
    tests = [result for result in results if str(result.get("unique_id", "")).startswith("test.")]
    models = [result for result in results if str(result.get("unique_id", "")).startswith("model.")]
    if not tests or not models:
        raise ValueError("dbt evidence must contain at least one model and one test result")

    return {
        "status": "success",
        "completed_at": datetime.now(UTC).isoformat(),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "commit_sha": os.getenv("GITHUB_SHA"),
        "sources": pipeline.get("sources", {}),
        "dbt": {
            "status": "success",
            "tests_passed": sum(result.get("status") == "pass" for result in tests),
            "tests_failed": 0,
            "models_built": sum(result.get("status") == "success" for result in models),
        },
        "model": (
            {
                "status": "available",
                "version": model_metrics.get("model_version"),
                "trained_at": model_metrics.get("trained_at"),
                "validation_strategy": model_metrics.get("validation_strategy"),
                "mae": model_metrics.get("lgbm_metrics", {}).get("overall", {}).get("mae"),
                "mdape": model_metrics.get("lgbm_metrics", {}).get("overall", {}).get("mdape"),
            }
            if model_metrics
            else {"status": "not_available"}
        ),
    }


def append_changelog(path: Path, status: dict[str, Any]) -> None:
    """Append one idempotent, measured monthly-refresh entry."""
    run_id = status.get("github_run_id") or status["completed_at"]
    marker = f"<!-- refresh:{run_id} -->"
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Changelog\n"
    if marker in existing:
        return

    source_lines = []
    for source, result in status["sources"].items():
        measured = result.get("loaded_rows", result.get("rows"))
        detail = f", rows={measured}" if measured is not None else ""
        source_lines.append(f"- `{source}`: {result.get('status', 'unknown')}{detail}")
    dbt = status["dbt"]
    model = status["model"]
    lines = [
        "",
        marker,
        f"## {status['completed_at'][:10]} Monthly Refresh (run {run_id})",
        "",
        *source_lines,
        (
            f"- `dbt build`: {dbt['status']}; models={dbt['models_built']}, "
            f"tests passed={dbt['tests_passed']}, tests failed={dbt['tests_failed']}"
        ),
        (
            f"- model: {model['status']}; validation={model.get('validation_strategy')}, "
            f"MAE={model.get('mae')}, MdAPE={model.get('mdape')}"
        ),
        "",
    ]
    path.write_text(existing.rstrip() + "\n" + "\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write measured refresh evidence")
    parser.add_argument("--pipeline", type=Path, required=True)
    parser.add_argument("--dbt-results", type=Path, required=True)
    parser.add_argument("--model-metrics", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--changelog", type=Path, required=True)
    args = parser.parse_args()

    pipeline = _read_object(args.pipeline)
    dbt_results = _read_object(args.dbt_results)
    model_metrics = (
        _read_object(args.model_metrics)
        if args.model_metrics and args.model_metrics.exists()
        else None
    )
    status = build_refresh_status(pipeline, dbt_results, model_metrics)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    append_changelog(args.changelog, status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
