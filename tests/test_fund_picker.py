"""Fund combobox rules: length includes spaces, the list is capped, clear drops the pick."""

from pathlib import Path

from utils import (
    fund_option_label,
    fund_search_text,
    sync_fund_picker_state,
    unique_fund_matches,
)


def test_search_starts_after_four_characters_and_spaces_count():
    assert fund_search_text("abc") is None
    assert fund_search_text("a b") is None
    assert fund_search_text("abcd") == "abcd"
    assert fund_search_text("ab c") == "ab c"
    # Four characters only because of spaces. The API receives the trimmed text.
    assert fund_search_text(" ab ") == "ab"
    assert fund_search_text("    ") is None
    assert fund_search_text(None) is None


def test_match_list_stops_at_thirty_unique_funds():
    matches = [
        {"schemeCode": i, "schemeName": f"Fund {i}"}
        for i in range(1, 41)
    ]
    matches.insert(0, {"schemeCode": 1, "schemeName": "Fund 1"})
    matches.append({"schemeCode": "", "schemeName": "Missing code"})
    matches.append("not a fund")
    rows, truncated = unique_fund_matches(matches, limit=30)
    assert truncated is True
    assert len(rows) == 30
    assert rows[0] == ("1", "Fund 1")
    assert rows[-1] == ("30", "Fund 30")
    assert all(code != "" for code, _name in rows)


def test_exact_cap_is_not_marked_truncated():
    matches = [{"schemeCode": i, "schemeName": f"Fund {i}"} for i in range(1, 31)]
    rows, truncated = unique_fund_matches(matches, limit=30)
    assert truncated is False
    assert len(rows) == 30


def test_duplicate_names_show_the_scheme_code():
    rows = [("1", "Growth"), ("2", "Growth"), ("3", "Balanced")]
    assert fund_option_label("1", "Growth", rows) == "Growth · 1"
    assert fund_option_label("3", "Balanced", rows) == "Balanced"


def test_typing_four_characters_opens_the_list():
    state = sync_fund_picker_state("smal", "sma", None, None, False)
    assert state["menu_open"] is True
    assert state["selected_code"] is None

    short = sync_fund_picker_state("sma", "sm", None, None, False)
    assert short["menu_open"] is False


def test_clearing_the_box_drops_the_selection():
    state = sync_fund_picker_state(
        "",
        "Axis Small Cap Fund Direct Growth",
        "120465",
        "Axis Small Cap Fund Direct Growth",
        False,
    )
    assert state["selected_code"] is None
    assert state["selected_name"] is None
    assert state["menu_open"] is False


def test_choosing_a_fund_keeps_the_list_closed():
    # The pick callback writes the name into the box and closes the list.
    # The next pass must not open the list just because the text changed.
    state = sync_fund_picker_state(
        "Axis Small Cap Fund Direct Growth",
        "smal",
        "120465",
        "Axis Small Cap Fund Direct Growth",
        False,
    )
    assert state["menu_open"] is False
    assert state["selected_code"] == "120465"
    assert state["selected_name"] == "Axis Small Cap Fund Direct Growth"


def test_chevron_can_open_the_list_for_the_selected_fund():
    state = sync_fund_picker_state(
        "Axis Small Cap Fund Direct Growth",
        "Axis Small Cap Fund Direct Growth",
        "120465",
        "Axis Small Cap Fund Direct Growth",
        True,
    )
    assert state["menu_open"] is True
    assert state["selected_code"] == "120465"


def test_editing_the_selected_name_clears_it_and_searches_again():
    state = sync_fund_picker_state(
        "Axis Small",
        "Axis Small Cap Fund Direct Growth",
        "120465",
        "Axis Small Cap Fund Direct Growth",
        False,
    )
    assert state["selected_code"] is None
    assert state["selected_name"] is None
    assert state["menu_open"] is True


def test_in_app_whats_new_is_the_user_facing_summary():
    text = Path("WHATS_NEW.md").read_text(encoding="utf-8")
    first, _rest = text.split("## ", 1)[1].split("\n## ", 1)
    latest = "## " + first
    assert latest.startswith("## Version 1.2.2")
    assert "ImportError" not in latest
    assert "startup error" not in latest.lower()
    assert "config.py" not in latest
    assert "4 characters" in latest
    assert "spaces count" in latest
    assert "Lump sum" in latest
    assert "₹1,000" in latest
    assert "₹10,000" in latest
    assert "30 funds" in latest
    lowered = latest.lower()
    assert "one box" in lowered
    assert "no second dropdown" not in lowered
    assert "click a row" not in lowered


def test_how_it_works_and_readme_describe_the_one_box():
    app = Path("app.py").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "Type at least 3 characters" not in app
    assert "no second dropdown" not in app
    assert "at least 4 characters" in app
    assert "spaces count" in app
    assert "up to 30 funds" in app
    assert "4 characters" in readme
    assert "spaces count" in readme
    assert "no second dropdown" not in readme
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [1.2.2]" in changelog
    assert "ImportError" in changelog
