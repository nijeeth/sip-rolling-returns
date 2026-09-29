"""Fund combobox helpers. No Streamlit, pandas, or matplotlib imports.

app.py imports these names from this module so startup does not depend on
utils.py having finished loading them.
"""

from typing import List, Optional

from app_config import MAX_SEARCH_RESULTS, MIN_SEARCH_QUERY_LENGTH


def fund_search_text(text: Optional[str], minimum: int = MIN_SEARCH_QUERY_LENGTH) -> Optional[str]:
    """Text to send to fund search, or None when the typed value is too short.

    The length check uses the raw text, so spaces count toward ``minimum``.
    Leading and trailing spaces are removed only after that check. A value
    that is long enough but empty once those spaces are removed is not searched.
    """
    raw = "" if text is None else str(text)
    if len(raw) < minimum:
        return None
    query = raw.strip()
    return query or None


def unique_fund_matches(matches, limit: int = MAX_SEARCH_RESULTS):
    """Unique (scheme code, scheme name) pairs, capped at ``limit``.

    Returns ``(rows, truncated)``. ``truncated`` is true when another unique
    fund was left off the list.
    """
    rows = []
    seen = set()
    truncated = False
    for fund in matches or []:
        if not isinstance(fund, dict):
            continue
        code = str(fund.get("schemeCode", "")).strip()
        name = str(fund.get("schemeName", "")).strip()
        if not code or not name or code in seen:
            continue
        if len(rows) >= limit:
            truncated = True
            break
        seen.add(code)
        rows.append((code, name))
    return rows, truncated


def fund_option_label(code: str, name: str, rows: List[tuple]) -> str:
    """Menu label. The scheme code is added only when two names match."""
    if sum(1 for _code, other in rows if other == name) > 1:
        return f"{name} · {code}"
    return name


def sync_fund_picker_state(
    raw_query: Optional[str],
    previous_query: Optional[str],
    selected_code: Optional[str],
    selected_name: Optional[str],
    menu_open: bool,
) -> dict:
    """Update selection and the match list after the box text changes.

    Choosing a fund writes that fund's name into the box and closes the list.
    This keeps the list closed when the box still shows the chosen name, so a
    later pass does not immediately open it again. Clearing the box drops the
    scheme code and the name. A different query opens the list once it is long
    enough to search, including spaces.
    """
    raw_query = "" if raw_query is None else str(raw_query)
    selected_code = selected_code or None
    selected_name = selected_name or None

    if selected_name and raw_query != selected_name:
        selected_code = None
        selected_name = None

    if previous_query is not None and raw_query != previous_query:
        still_selected = bool(selected_name) and raw_query == selected_name
        if raw_query == "":
            menu_open = False
            selected_code = None
            selected_name = None
        elif still_selected:
            pass
        elif fund_search_text(raw_query):
            menu_open = True
        else:
            menu_open = False

    return {
        "selected_code": selected_code,
        "selected_name": selected_name,
        "menu_open": menu_open,
        "previous_query": raw_query,
    }
