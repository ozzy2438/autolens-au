"""Tests for truthful point-in-time deployment health evidence."""

import httpx

from scripts.check_deployment_health import check_deployment_health


def test_unconfigured_health_check_does_not_claim_uptime() -> None:
    report = check_deployment_health(api_url=None, dashboard_url=None)

    assert report["status"] == "not_configured"
    assert "no uptime is claimed" in report["message"]
    assert report["endpoints"] == []


def test_both_endpoints_must_be_configured() -> None:
    report = check_deployment_health(
        api_url="https://api.example/health",
        dashboard_url=None,
    )

    assert report["status"] == "configuration_error"
    assert "dashboard" in report["message"]


def test_healthy_api_model_and_dashboard_are_recorded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.example":
            return httpx.Response(200, json={"status": "healthy", "model_loaded": True})
        return httpx.Response(200, content=b"streamlit")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = check_deployment_health(
            api_url="https://api.example/health",
            dashboard_url="https://dashboard.example",
            client=client,
            retry_delay=0,
        )

    assert report["status"] == "healthy"
    assert [endpoint["status"] for endpoint in report["endpoints"]] == ["healthy", "healthy"]


def test_degraded_api_fails_even_when_http_status_is_200() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.example":
            return httpx.Response(200, json={"status": "degraded", "model_loaded": False})
        return httpx.Response(200, content=b"streamlit")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = check_deployment_health(
            api_url="https://api.example/health",
            dashboard_url="https://dashboard.example",
            client=client,
            attempts=1,
            retry_delay=0,
        )

    assert report["status"] == "unhealthy"
    assert report["endpoints"][0]["status"] == "unhealthy"
