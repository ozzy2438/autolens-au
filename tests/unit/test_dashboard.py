"""Streamlit smoke tests: every product page must render without placeholders crashing."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

DASHBOARD_FILES = [
    Path("src/dashboard/app.py"),
    *sorted(Path("src/dashboard/pages").glob("[1-4]_*.py")),
]


@pytest.mark.parametrize("dashboard_file", DASHBOARD_FILES, ids=lambda path: path.stem)
def test_dashboard_page_renders(dashboard_file: Path) -> None:
    app = AppTest.from_file(str(dashboard_file), default_timeout=15).run()
    assert not app.exception
