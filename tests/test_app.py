from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app.py"


def test_app_loads_without_exception():
    at = AppTest.from_file(str(APP)).run()
    assert not at.exception
    assert len(at.tabs) == 5
