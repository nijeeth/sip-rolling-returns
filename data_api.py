"""
API interaction module for fetching mutual fund data.
Handles API calls to mfapi.in for NAV data and fund search.
"""

import json
import os
import time
from typing import List, Optional
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st
from datetime import datetime

from config import (
    API_BASE_URL,
    CACHE_DIR,
    CACHE_EXPIRY_DAYS,
    FUND_LIST_CACHE_TTL_SECONDS,
    MAX_API_RETRIES,
    NAV_API_TIMEOUT,
    NAV_CACHE_TTL_SECONDS,
    RETRY_DELAY_SECONDS,
    SEARCH_API_TIMEOUT,
    SEARCH_CACHE_TTL_SECONDS,
)


class MfapiError(RuntimeError):
    """Raised when mfapi data cannot be loaded. Streamlit does not cache this."""


def clean_nav_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop blank rows, zero or negative NAVs, and duplicate dates.

    A zero NAV (seen on some schemes) would blow up units = amount / NAV.
    If the same date appears twice, the later row is kept.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "nav"])

    cleaned = df.copy()
    if "date" not in cleaned.columns or "nav" not in cleaned.columns:
        return pd.DataFrame(columns=["date", "nav"])

    cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    cleaned["nav"] = pd.to_numeric(cleaned["nav"], errors="coerce")
    cleaned = cleaned.dropna(subset=["date", "nav"])
    cleaned = cleaned[cleaned["nav"] > 0]
    cleaned = cleaned.sort_values("date")
    cleaned = cleaned.drop_duplicates(subset=["date"], keep="last")
    cleaned = cleaned[["date", "nav"]].reset_index(drop=True)
    return cleaned


def _cache_path(scheme_code: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"nav_{scheme_code}.csv")


def _read_fresh_cache(cache: str) -> Optional[pd.DataFrame]:
    if not os.path.exists(cache):
        return None
    age_days = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache))).days
    if age_days >= CACHE_EXPIRY_DAYS:
        return None
    try:
        return clean_nav_dataframe(pd.read_csv(cache, parse_dates=["date"]))
    except Exception:
        return None


def _read_any_cache(cache: str) -> Optional[pd.DataFrame]:
    if not os.path.exists(cache):
        return None
    try:
        frame = clean_nav_dataframe(pd.read_csv(cache, parse_dates=["date"]))
    except Exception:
        return None
    if frame.empty:
        return None
    return frame


def load_nav(scheme_code: str) -> pd.DataFrame:
    """
    Fetch NAV history for one scheme.

    Uses a daily file cache. Network and empty-data failures raise MfapiError
    instead of returning an empty frame, so Streamlit does not remember the failure.
    A stale file is used only when the network itself fails.
    """
    scheme_code = str(scheme_code).strip()
    if not scheme_code:
        raise MfapiError("Scheme code is missing.")

    cache = _cache_path(scheme_code)
    cached = _read_fresh_cache(cache)
    if cached is not None and not cached.empty:
        return cached

    last_error: Optional[Exception] = None
    payload = None
    for attempt in range(MAX_API_RETRIES):
        try:
            response = requests.get(
                f"{API_BASE_URL}/{quote(scheme_code)}",
                timeout=NAV_API_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
            break
        except Exception as exc:
            last_error = exc
            if attempt < MAX_API_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)

    if payload is None:
        stale = _read_any_cache(cache)
        if stale is not None:
            return stale
        raise MfapiError(f"Could not fetch NAV for scheme {scheme_code}.") from last_error

    data = payload.get("data") if isinstance(payload, dict) else None
    if not data:
        stale = _read_any_cache(cache)
        if stale is not None:
            return stale
        raise MfapiError(f"No NAV history returned for scheme {scheme_code}.")

    frame = pd.DataFrame(data)
    if "date" not in frame.columns or "nav" not in frame.columns:
        raise MfapiError(f"NAV history for scheme {scheme_code} was not in the expected format.")

    frame["date"] = pd.to_datetime(frame["date"], format="%d-%m-%Y", errors="coerce")
    frame["nav"] = pd.to_numeric(frame["nav"], errors="coerce")
    frame = clean_nav_dataframe(frame)
    if frame.empty:
        raise MfapiError(f"No usable NAV rows for scheme {scheme_code}.")

    try:
        frame.to_csv(cache, index=False)
    except Exception:
        pass
    return frame


def _lookup_scheme_by_code(scheme_code: str) -> Optional[dict]:
    """Direct scheme lookup. The search endpoint does not match scheme codes."""
    response = requests.get(
        f"{API_BASE_URL}/{quote(scheme_code)}",
        timeout=SEARCH_API_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        return None
    meta = payload.get("meta") or {}
    name = str(meta.get("scheme_name") or "").strip()
    code = str(meta.get("scheme_code") or scheme_code).strip()
    if not name or not payload.get("data"):
        return None
    return {"schemeCode": code, "schemeName": name}


def load_search_results(query: str) -> List[dict]:
    """
    Search funds by name, or by exact scheme code when the query is all digits.

    Raises MfapiError on network failure. An empty list means nothing matched.
    """
    query = str(query).strip()
    if not query:
        return []

    if query.isdigit():
        try:
            match = _lookup_scheme_by_code(query)
        except Exception as exc:
            raise MfapiError("Fund search failed.") from exc
        return [match] if match else []

    try:
        response = requests.get(
            f"{API_BASE_URL}/search",
            params={"q": query},
            timeout=SEARCH_API_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise MfapiError("Fund search failed.") from exc

    if not isinstance(payload, list):
        raise MfapiError("Fund search returned an unexpected response.")

    results = []
    seen = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        code = str(item.get("schemeCode") or "").strip()
        name = str(item.get("schemeName") or "").strip()
        if not code or not name or code in seen:
            continue
        seen.add(code)
        results.append({"schemeCode": code, "schemeName": name})
    return results


def load_all_funds() -> List[dict]:
    """
    Full scheme list. Kept for callers that need it; the app searches instead.

    A failed download is not returned as an empty list, so it is not cached.
    """
    fund_list_timeout = 30
    fund_list_retries = 3
    cache_file = os.path.join(CACHE_DIR, "all_funds_cache.json")
    os.makedirs(CACHE_DIR, exist_ok=True)

    last_error: Optional[Exception] = None
    for attempt in range(fund_list_retries):
        try:
            response = requests.get(API_BASE_URL, timeout=fund_list_timeout)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and data:
                try:
                    with open(cache_file, "w", encoding="utf-8") as handle:
                        json.dump(data, handle)
                except Exception:
                    pass
                return data
        except Exception as exc:
            last_error = exc
            if attempt < fund_list_retries - 1:
                time.sleep(2 ** attempt)

    try:
        if os.path.exists(cache_file):
            with open(cache_file, encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, list) and data:
                return data
    except Exception:
        pass

    raise MfapiError("Could not load the mutual fund list.") from last_error


@st.cache_data(show_spinner=False, ttl=NAV_CACHE_TTL_SECONDS)
def fetch_nav(scheme_code: str) -> pd.DataFrame:
    """NAV history. Cached in memory for one day; failures are not cached."""
    return load_nav(scheme_code)


@st.cache_data(show_spinner=False, ttl=SEARCH_CACHE_TTL_SECONDS)
def search_funds(query: str) -> List[dict]:
    """Fund search. Cached for a short time; failures are not cached."""
    return load_search_results(query)


@st.cache_data(show_spinner=False, ttl=FUND_LIST_CACHE_TTL_SECONDS)
def fetch_all_funds() -> List[dict]:
    """Full fund list. Failures raise, so an empty failure is not cached for a day."""
    return load_all_funds()
