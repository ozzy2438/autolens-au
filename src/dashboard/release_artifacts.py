"""Retrieve a coherent, verified model bundle from GitHub Releases."""

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

from config.settings import MODEL_DIR, model_config

GITHUB_API_URL = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"
MODEL_ASSET_NAME = "hedonic_model_latest.joblib"
METRICS_ASSET_NAME = "latest_metrics.json"


class ReleaseArtifactError(RuntimeError):
    """Raised when a complete, verified model release cannot be prepared."""


@dataclass(frozen=True)
class ReleaseArtifactBundle:
    """Paths and release provenance for one coherent artifact pair."""

    model_path: Path
    metrics_path: Path
    release_tag: str
    source: str


def _headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "autolens-au-dashboard",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _select_model_release(payload: Any, tag_prefix: str) -> dict[str, Any]:
    if not isinstance(payload, list):
        raise ReleaseArtifactError("GitHub release response must be a list")
    candidates = [
        release
        for release in payload
        if isinstance(release, dict)
        and not release.get("draft", False)
        and str(release.get("tag_name", "")).startswith(tag_prefix)
    ]
    if not candidates:
        raise ReleaseArtifactError(f"No published {tag_prefix}* model release exists")
    return max(
        candidates,
        key=lambda release: str(release.get("published_at") or release.get("created_at") or ""),
    )


def _asset_bytes(
    client: httpx.Client,
    asset: dict[str, Any],
    headers: dict[str, str],
) -> bytes:
    name = str(asset.get("name", "unnamed asset"))
    url = asset.get("browser_download_url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ReleaseArtifactError(f"{name} has no valid HTTPS download URL")
    response = client.get(url, headers=headers)
    response.raise_for_status()
    content = response.content
    if not content:
        raise ReleaseArtifactError(f"{name} is empty")

    expected_size = asset.get("size")
    if isinstance(expected_size, int) and len(content) != expected_size:
        raise ReleaseArtifactError(
            f"{name} size mismatch: expected {expected_size}, downloaded {len(content)}"
        )
    digest = asset.get("digest")
    if isinstance(digest, str) and digest.startswith("sha256:"):
        actual = hashlib.sha256(content).hexdigest()
        expected = digest.removeprefix("sha256:")
        if actual != expected:
            raise ReleaseArtifactError(f"{name} SHA-256 verification failed")
    return content


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
            temporary_name = file.name
        Path(temporary_name).replace(path)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def ensure_model_release_artifacts(
    *,
    repository: str | None = None,
    model_path: Path | None = None,
    metrics_path: Path | None = None,
    token: str | None = None,
    tag_prefix: str = "model-",
    client: httpx.Client | None = None,
) -> ReleaseArtifactBundle:
    """Use local artifacts when complete, otherwise fetch the newest verified pair."""
    destination_model = model_path or model_config.model_path
    destination_metrics = metrics_path or MODEL_DIR / METRICS_ASSET_NAME
    if destination_model.exists() and destination_metrics.exists():
        return ReleaseArtifactBundle(
            model_path=destination_model,
            metrics_path=destination_metrics,
            release_tag="local",
            source="local",
        )

    target_repository = repository or os.getenv("MODEL_RELEASE_REPOSITORY", "").strip()
    if not target_repository or target_repository.count("/") != 1:
        raise ReleaseArtifactError(
            "MODEL_RELEASE_REPOSITORY must be configured as owner/repository"
        )
    headers = _headers(token or os.getenv("GITHUB_TOKEN"))
    owns_client = client is None
    http_client = client or httpx.Client(follow_redirects=True, timeout=30)
    try:
        response = http_client.get(
            f"{GITHUB_API_URL}/repos/{target_repository}/releases",
            headers=headers,
            params={"per_page": 50},
        )
        response.raise_for_status()
        release = _select_model_release(response.json(), tag_prefix)
        assets = {
            str(asset.get("name")): asset
            for asset in release.get("assets", [])
            if isinstance(asset, dict) and asset.get("state") == "uploaded"
        }
        missing = [name for name in (MODEL_ASSET_NAME, METRICS_ASSET_NAME) if name not in assets]
        if missing:
            raise ReleaseArtifactError(
                f"Release {release.get('tag_name')} is missing assets: {', '.join(missing)}"
            )

        model_bytes = _asset_bytes(http_client, assets[MODEL_ASSET_NAME], headers)
        metrics_bytes = _asset_bytes(http_client, assets[METRICS_ASSET_NAME], headers)
        metrics_payload = json.loads(metrics_bytes)
        if not isinstance(metrics_payload, dict):
            raise ReleaseArtifactError("latest_metrics.json must contain a JSON object")
        _atomic_write(destination_model, model_bytes)
        _atomic_write(destination_metrics, metrics_bytes)
        return ReleaseArtifactBundle(
            model_path=destination_model,
            metrics_path=destination_metrics,
            release_tag=str(release["tag_name"]),
            source=f"github:{target_repository}",
        )
    except (httpx.HTTPError, ValueError) as error:
        raise ReleaseArtifactError(f"Model release retrieval failed: {error}") from error
    finally:
        if owns_client:
            http_client.close()


@st.cache_resource(ttl=300)
def prepare_dashboard_artifacts() -> ReleaseArtifactBundle:
    """Prepare one thread-safe, process-cached artifact pair for Streamlit pages."""
    return ensure_model_release_artifacts()
