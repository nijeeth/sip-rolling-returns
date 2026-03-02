"""
API interaction module for fetching mutual fund data.
Handles API calls to mfapi.in for NAV data and fund search.
"""

import pandas as pd
import requests
import os
import time
import streamlit as st
from datetime import datetime
from typing import List

from config import (
    CACHE_DIR,
    CACHE_EXPIRY_DAYS,
    NAV_API_TIMEOUT,
    SEARCH_API_TIMEOUT,
    MAX_API_RETRIES,
    RETRY_DELAY_SECONDS,
    API_BASE_URL
)


@st.cache_data(show_spinner=False)
def fetch_nav(scheme_code: str) -> pd.DataFrame:
    """
    Fetch NAV data for a mutual fund scheme with file-based caching.
    
    Args:
        scheme_code: Mutual fund scheme code
    
    Returns:
        DataFrame with columns ['date', 'nav'] sorted by date
        Returns empty DataFrame if fetch fails
    """
    scheme_code = str(scheme_code).strip()
    # Use scheme_code directly as the unique cache key
    cache = os.path.join(CACHE_DIR, f"nav_{scheme_code}.csv")

    # Check if cache exists and is fresh
    if os.path.exists(cache):
        age_days = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache))).days
        if age_days < CACHE_EXPIRY_DAYS:
            return pd.read_csv(cache, parse_dates=['date'])
        os.remove(cache)

    # Fetch from API with retry logic
    for attempt in range(MAX_API_RETRIES):
        try:
            r = requests.get(f"{API_BASE_URL}/{scheme_code}", timeout=NAV_API_TIMEOUT)
            r.raise_for_status()
            data = r.json()['data']
            break
        except Exception:
            if attempt < MAX_API_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                return pd.DataFrame()

    # Process and cache the data
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y', errors='coerce')
    df['nav']  = pd.to_numeric(df['nav'], errors='coerce')
    df = df.dropna().sort_values('date').reset_index(drop=True)
    
    if not df.empty:
        df.to_csv(cache, index=False)
    
    return df


@st.cache_data(show_spinner=False)
def search_funds(query: str) -> List[dict]:
    """
    Search for mutual funds by name or scheme code.
    
    Args:
        query: Search query string
    
    Returns:
        List of dictionaries containing fund details (schemeName, schemeCode)
        Returns empty list if search fails
    """
    try:
        r = requests.get(f"{API_BASE_URL}/search?q={query}", timeout=SEARCH_API_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []

@st.cache_data(show_spinner=False)
def fetch_all_funds() -> List[dict]:
    """
    Fetch the complete list of all mutual funds from mfapi.in.
    Cached for the session — only fetched once per app startup.
    Returns a list of dicts with keys: schemeName, schemeCode.
    Returns empty list if fetch fails.
    """
    try:
        r = requests.get(API_BASE_URL, timeout=NAV_API_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []
