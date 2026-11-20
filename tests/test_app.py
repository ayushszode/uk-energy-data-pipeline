"""Smoke test: every dashboard page renders without an exception (needs app_data/)."""
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
DATA = Path(__file__).resolve().parents[1] / "app_data" / "daily.csv.gz"

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
pytestmark = pytest.mark.skipif(not DATA.exists(), reason="run the pipeline first to export app_data/")

PAGES = ["Overview", "Daily patterns", "Carbon & renewables", "Best time to use power",
         "Regions", "Forecast", "Data quality", "About"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = streamlit_testing.AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.sidebar.radio(key="page").set_value(page).run()
    assert not at.exception, f"{page}: {at.exception}"
