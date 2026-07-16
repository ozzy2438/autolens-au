"""Tests for measured monthly-refresh evidence generation."""

import pytest

from scripts.write_refresh_status import append_changelog, build_refresh_status


def _pipeline(status: str = "success") -> dict:
    return {
        "status": status,
        "sources": {
            "kaggle": {"status": "success", "loaded_rows": 120},
            "qld": {"status": "success", "rows": 45},
        },
    }


def _dbt(status: str = "pass") -> dict:
    return {
        "results": [
            {"unique_id": "model.autolens.stg_listings", "status": "success"},
            {"unique_id": "test.autolens.not_null", "status": status},
        ]
    }


def test_refresh_status_contains_measured_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    status = build_refresh_status(
        _pipeline(),
        _dbt(),
        {
            "model_version": "1.0.0",
            "validation_strategy": "random_holdout_single_snapshot",
            "lgbm_metrics": {"overall": {"mae": 2500, "mdape": 8.1}},
        },
    )

    assert status["status"] == "success"
    assert status["dbt"]["tests_passed"] == 1
    assert status["model"]["mae"] == 2500


def test_failed_pipeline_or_dbt_cannot_be_recorded_as_success() -> None:
    with pytest.raises(ValueError, match="non-passing pipeline"):
        build_refresh_status(_pipeline("failed"), _dbt())
    with pytest.raises(ValueError, match="failed nodes"):
        build_refresh_status(_pipeline(), _dbt("fail"))


def test_empty_dbt_evidence_cannot_be_recorded_as_success() -> None:
    with pytest.raises(ValueError, match="at least one model and one test"):
        build_refresh_status(_pipeline(), {"results": []})


def test_changelog_is_idempotent_and_uses_real_counts(tmp_path) -> None:
    path = tmp_path / "CHANGELOG.md"
    status = build_refresh_status(_pipeline(), _dbt())
    status["github_run_id"] = "456"

    append_changelog(path, status)
    append_changelog(path, status)
    content = path.read_text(encoding="utf-8")

    assert content.count("refresh:456") == 1
    assert "rows=120" in content
    assert "tests passed=1" in content
