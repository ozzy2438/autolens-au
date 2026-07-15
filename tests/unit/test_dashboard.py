"""Streamlit smoke tests: every product page must render without placeholders crashing."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.api.schemas import MAX_MANUFACTURE_YEAR
from src.dashboard.formatting import format_optional_currency, format_optional_percentage

DASHBOARD_FILES = [
    Path("src/dashboard/app.py"),
    *sorted(Path("src/dashboard/pages").glob("[1-4]_*.py")),
]


@pytest.mark.parametrize("dashboard_file", DASHBOARD_FILES, ids=lambda path: path.stem)
def test_dashboard_page_renders(dashboard_file: Path) -> None:
    app = AppTest.from_file(str(dashboard_file), default_timeout=15).run()
    assert not app.exception


def test_valuation_year_slider_matches_api_limit() -> None:
    app = AppTest.from_file("src/dashboard/pages/1_instant_valuation.py", default_timeout=15).run()

    assert app.slider[0].max <= MAX_MANUFACTURE_YEAR


def test_optional_metric_formatting_preserves_zero_and_missing() -> None:
    assert format_optional_currency(None) == "Unknown"
    assert format_optional_currency(0) == "$0"
    assert format_optional_percentage(None) == "Unknown"
    assert format_optional_percentage(0.0, ratio=True) == "0.0%"
