"""Tests for the required/best-effort pipeline orchestration policy."""

from scripts import run_pipeline


def test_optional_source_failure_degrades_but_does_not_fail(monkeypatch) -> None:
    def fake_source(source: str, **_kwargs) -> dict[str, int | str]:
        if source == "qld":
            return {"status": "no_data", "rows": 0}
        return {"status": "success", "rows": 10}

    monkeypatch.setattr(run_pipeline, "run_source", fake_source)

    result = run_pipeline.run_full_pipeline(sources=("kaggle", "qld"))

    assert result["status"] == "degraded"
    assert result["failed_sources"] == ["qld"]
    assert result["failed_required_sources"] == []


def test_required_source_failure_fails_the_pipeline(monkeypatch) -> None:
    def fake_source(source: str, **_kwargs) -> dict[str, int | str]:
        if source == "kaggle":
            return {"status": "error", "error": "boom"}
        return {"status": "success", "rows": 10}

    monkeypatch.setattr(run_pipeline, "run_source", fake_source)

    result = run_pipeline.run_full_pipeline(sources=("kaggle", "qld"))

    assert result["status"] == "failed"
    assert result["failed_required_sources"] == ["kaggle"]


def test_pipeline_succeeds_only_when_every_source_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(
        run_pipeline,
        "run_source",
        lambda _source, **_kwargs: {"status": "success", "rows": 10},
    )

    result = run_pipeline.run_full_pipeline(sources=("kaggle", "qld"))

    assert result["status"] == "success"
    assert result["failed_sources"] == []
