"""Startup imports must not depend on a module named utils.

Streamlit Cloud redacts the ImportError text. When ``utils`` is some other
module, the traceback is only ``from utils import`` in app.py.
"""

import sys
import types
from pathlib import Path

from streamlit.testing.v1 import AppTest

import fund_picker
from app_utils import (
    build_excel,
    fmt_inr,
    format_indian_int,
    is_idcw_plan,
    plot_rolling_xirr,
    resolve_amount_state,
    validate_inputs,
)

APP_PATH = str(Path(__file__).resolve().parents[1] / "app.py")
STARTUP_NAMES = (
    validate_inputs,
    plot_rolling_xirr,
    build_excel,
    fmt_inr,
    format_indian_int,
    is_idcw_plan,
    resolve_amount_state,
)


def test_fund_picker_helpers_come_from_fund_picker():
    assert callable(fund_picker.fund_option_label)
    assert fund_picker.fund_option_label("1", "Growth", [("1", "Growth")]) == "Growth"
    assert (
        fund_picker.fund_option_label("1", "Growth", [("1", "Growth"), ("2", "Growth")])
        == "Growth · 1"
    )


def test_app_starts_when_another_utils_module_is_loaded():
    """A site-packages module named utils must not take the app's helpers."""
    fake = types.ModuleType("utils")
    fake.__file__ = "/tmp/site-packages/utils/__init__.py"
    previous = sys.modules.get("utils")
    sys.modules["utils"] = fake
    try:
        assert all(callable(fn) for fn in STARTUP_NAMES)
        assert format_indian_int(100000) == "1,00,000"
        assert not hasattr(fake, "validate_inputs")
        app = AppTest.from_file(APP_PATH, default_timeout=30)
        app.run(timeout=30)
        assert not app.exception
    finally:
        if previous is None:
            sys.modules.pop("utils", None)
        else:
            sys.modules["utils"] = previous
