"""Tests for coherent GitHub Release-backed dashboard artifacts."""

import hashlib
from pathlib import Path

import httpx
import pytest

from src.dashboard.release_artifacts import (
    METRICS_ASSET_NAME,
    MODEL_ASSET_NAME,
    ReleaseArtifactError,
    ensure_model_release_artifacts,
)


def _asset(name: str, content: bytes) -> dict[str, object]:
    return {
        "name": name,
        "state": "uploaded",
        "size": len(content),
        "digest": f"sha256:{hashlib.sha256(content).hexdigest()}",
        "browser_download_url": f"https://downloads.example/{name}",
    }


def _release_transport(model: bytes, metrics: bytes) -> httpx.MockTransport:
    releases = [
        {
            "tag_name": "v1.0.0",
            "draft": False,
            "published_at": "2026-07-15T00:00:00Z",
            "assets": [],
        },
        {
            "tag_name": "model-123-1",
            "draft": False,
            "prerelease": True,
            "published_at": "2026-07-16T00:00:00Z",
            "assets": [_asset(MODEL_ASSET_NAME, model), _asset(METRICS_ASSET_NAME, metrics)],
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.github.com":
            return httpx.Response(200, json=releases)
        if request.url.path.endswith(MODEL_ASSET_NAME):
            return httpx.Response(200, content=model)
        if request.url.path.endswith(METRICS_ASSET_NAME):
            return httpx.Response(200, content=metrics)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_release_artifacts_are_downloaded_and_verified(tmp_path: Path) -> None:
    model = b"calibrated-model"
    metrics = b'{"model_version": "1.0.0"}'
    model_path = tmp_path / MODEL_ASSET_NAME
    metrics_path = tmp_path / METRICS_ASSET_NAME

    with httpx.Client(transport=_release_transport(model, metrics)) as client:
        result = ensure_model_release_artifacts(
            repository="ozzy2438/autolens-au",
            model_path=model_path,
            metrics_path=metrics_path,
            client=client,
        )

    assert result.release_tag == "model-123-1"
    assert result.source == "github:ozzy2438/autolens-au"
    assert model_path.read_bytes() == model
    assert metrics_path.read_bytes() == metrics


def test_complete_local_pair_never_calls_github(tmp_path: Path) -> None:
    model_path = tmp_path / MODEL_ASSET_NAME
    metrics_path = tmp_path / METRICS_ASSET_NAME
    model_path.write_bytes(b"local-model")
    metrics_path.write_text("{}", encoding="utf-8")

    result = ensure_model_release_artifacts(
        model_path=model_path,
        metrics_path=metrics_path,
    )

    assert result.release_tag == "local"
    assert result.source == "local"


def test_invalid_digest_leaves_no_partial_pair(tmp_path: Path) -> None:
    model = b"calibrated-model"
    metrics = b'{"model_version": "1.0.0"}'
    transport = _release_transport(model, metrics)

    def corrupt_metrics(request: httpx.Request) -> httpx.Response:
        response = transport.handle_request(request)
        if request.url.path.endswith(METRICS_ASSET_NAME):
            return httpx.Response(200, content=b"corrupted-but-same-size-xxxxxxxx")
        return response

    model_path = tmp_path / MODEL_ASSET_NAME
    metrics_path = tmp_path / METRICS_ASSET_NAME
    with httpx.Client(transport=httpx.MockTransport(corrupt_metrics)) as client:
        with pytest.raises(ReleaseArtifactError, match=r"verification failed|size mismatch"):
            ensure_model_release_artifacts(
                repository="ozzy2438/autolens-au",
                model_path=model_path,
                metrics_path=metrics_path,
                client=client,
            )

    assert not model_path.exists()
    assert not metrics_path.exists()
