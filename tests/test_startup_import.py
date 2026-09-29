"""The app must import the fund picker helpers when Streamlit starts."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

import fund_picker
import utils

APP_PATH = str(Path(__file__).resolve().parents[1] / "app.py")


def test_fund_option_label_imports_from_both_modules():
    assert callable(fund_picker.fund_option_label)
    assert utils.fund_option_label is fund_picker.fund_option_label
    assert fund_picker.fund_option_label("1", "Growth", [("1", "Growth")]) == "Growth"
    assert (
        fund_picker.fund_option_label("1", "Growth", [("1", "Growth"), ("2", "Growth")])
        == "Growth · 1"
    )


def test_app_starts_without_import_error():
    app = AppTest.from_file(APP_PATH, default_timeout=30)
    app.run(timeout=30)
    assert not app.exception
