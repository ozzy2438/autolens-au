"""Run point-in-time health probes without claiming historical uptime."""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


def _probe(
    client: httpx.Client,
    *,
    name: str,
    url: str,
    require_healthy_model: bool,
    attempts: int,
    retry_delay: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    last_error = "probe did not run"
    for attempt in range(1, attempts + 1):
        try:
            response = client.get(url)
            response.raise_for_status()
            if require_healthy_model:
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("API health response is not a JSON object")
                if payload.get("status") != "healthy" or payload.get("model_loaded") is not True:
                    raise ValueError("API is reachable but no calibrated model is loaded")
            elif not response.content:
                raise ValueError("dashboard returned an empty response")
            return {
                "name": name,
                "url": url,
                "status": "healthy",
                "status_code": response.status_code,
                "attempts": attempt,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            }
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as error:
            last_error = str(error)
            if attempt < attempts and retry_delay:
                time.sleep(retry_delay)
    return {
        "name": name,
        "url": url,
        "status": "unhealthy",
        "attempts": attempts,
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        "error": last_error,
    }


def check_deployment_health(
    *,
    api_url: str | None,
    dashboard_url: str | None,
    client: httpx.Client | None = None,
    attempts: int = 3,
    retry_delay: float = 1,
) -> dict[str, Any]:
    """Probe configured endpoints and return one machine-readable observation."""
    configured = {"api": api_url, "dashboard": dashboard_url}
    missing = [name for name, url in configured.items() if not url]
    checked_at = datetime.now(UTC).isoformat()
    if len(missing) == len(configured):
        return {
            "status": "not_configured",
            "checked_at": checked_at,
            "message": "No public deployment URLs are configured; no uptime is claimed.",
            "endpoints": [],
        }
    if missing:
        return {
            "status": "configuration_error",
            "checked_at": checked_at,
            "message": f"Missing deployment URLs: {', '.join(missing)}",
            "endpoints": [],
        }

    owns_client = client is None
    http_client = client or httpx.Client(follow_redirects=True, timeout=15)
    try:
        endpoints = [
            _probe(
                http_client,
                name="api",
                url=str(api_url),
                require_healthy_model=True,
                attempts=attempts,
                retry_delay=retry_delay,
            ),
            _probe(
                http_client,
                name="dashboard",
                url=str(dashboard_url),
                require_healthy_model=False,
                attempts=attempts,
                retry_delay=retry_delay,
            ),
        ]
    finally:
        if owns_client:
            http_client.close()
    return {
        "status": (
            "healthy"
            if all(endpoint["status"] == "healthy" for endpoint in endpoints)
            else "unhealthy"
        ),
        "checked_at": checked_at,
        "message": "Point-in-time probes only; this is not an uptime percentage.",
        "endpoints": endpoints,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check deployed AutoLens endpoints")
    parser.add_argument("--api-url")
    parser.add_argument("--dashboard-url")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = check_deployment_health(
        api_url=args.api_url or None,
        dashboard_url=args.dashboard_url or None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if report["status"] in {"unhealthy", "configuration_error"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
