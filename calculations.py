"""
Core calculation functions for SIP and lump-sum rolling returns.
"""

import math
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

from config import (
    DAYS_PER_YEAR,
    MAX_XIRR_ITERATIONS,
    PROGRESS_UPDATE_INTERVAL,
    XIRR_RATE_HIGH,
    XIRR_RATE_LOW,
    XIRR_TOLERANCE,
)
from data_api import clean_nav_dataframe


def xirr(cashflows: Sequence[float], dates: Sequence) -> float:
    """
    Annual internal rate of return for uneven cash flows.

    Uses a bracketed root search (bisection) on [-99.99%, 10,000%].
    A Newton start at 8% overshoots below -100% on deep losses and then
    either crashes or returns no result, which used to drop those periods.

    Returns the rate as a decimal (0.12 means 12%), or NaN when the cash
    flows have no sign change and no rate exists.
    """
    if len(cashflows) < 2 or len(cashflows) != len(dates):
        return np.nan

    has_pos = any(cf > 0 for cf in cashflows)
    has_neg = any(cf < 0 for cf in cashflows)
    if not (has_pos and has_neg):
        return np.nan

    t0 = pd.Timestamp(dates[0]).normalize()
    times = [(pd.Timestamp(d).normalize() - t0).days / DAYS_PER_YEAR for d in dates]

    def npv(rate: float) -> float:
        if rate <= -1.0:
            return math.nan
        base = 1.0 + rate
        total = 0.0
        for cf, t in zip(cashflows, times):
            try:
                total += cf / base ** t
            except OverflowError:
                return math.copysign(math.inf, cf)
        return total

    low = XIRR_RATE_LOW
    f_low = npv(low)
    # Pull the lower end up if the power overflows so the bracket stays finite.
    for _ in range(30):
        if math.isfinite(f_low):
            break
        low = (low + 0.0) / 2.0
        if low <= -1.0:
            low = -0.9999
        f_low = npv(low)
    if not math.isfinite(f_low):
        return np.nan

    high = XIRR_RATE_HIGH
    f_high = npv(high)
    if not math.isfinite(f_high):
        return np.nan

    if f_low == 0.0:
        return low
    if abs(npv(0.0)) <= XIRR_TOLERANCE:
        return 0.0
    if f_low * f_high > 0.0:
        return np.nan

    root = _bisect_root(npv, low, high, f_low, f_high, XIRR_TOLERANCE, MAX_XIRR_ITERATIONS)
    if root is None or not math.isfinite(root) or root <= -1.0:
        return np.nan
    return root


def _bisect_root(
    func: Callable[[float], float],
    low: float,
    high: float,
    f_low: float,
    f_high: float,
    xtol: float,
    maxiter: int,
) -> Optional[float]:
    """Root of a continuous function on a bracket that changes sign."""
    for _ in range(maxiter):
        if abs(high - low) <= xtol:
            return (low + high) / 2.0
        mid = (low + high) / 2.0
        if mid == low or mid == high:
            return mid
        f_mid = func(mid)
        if not math.isfinite(f_mid):
            return None
        if f_mid == 0.0:
            return mid
        # Keep the half where the sign changes.
        if f_low * f_mid < 0.0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2.0


def lump_sum_cagr(start_nav: float, end_nav: float, start_date, end_date) -> float:
    """
    CAGR between two NAV dates.

    years_exact is the actual number of days between the NAV dates divided by
    365.25, the same year length used for XIRR.
    """
    if start_nav <= 0 or end_nav <= 0:
        return np.nan
    days = (pd.Timestamp(end_date).normalize() - pd.Timestamp(start_date).normalize()).days
    if days <= 0:
        return np.nan
    years_exact = days / DAYS_PER_YEAR
    return (end_nav / start_nav) ** (1.0 / years_exact) - 1.0


def build_nav_arrays(nav_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Convert a cleaned NAV frame into sorted numpy arrays."""
    return (
        nav_df["date"].values.astype("datetime64[ns]"),
        nav_df["nav"].values.astype(float),
    )


def get_next_nav_fast(
    nav_dates: np.ndarray, nav_vals: np.ndarray, target
) -> Tuple[Optional[pd.Timestamp], Optional[float]]:
    """
    Next available NAV on or after the target date.

    Returns (None, None) when every NAV is before the target.
    """
    idx = np.searchsorted(nav_dates, np.datetime64(pd.Timestamp(target), "ns"), side="left")
    if idx >= len(nav_dates):
        return None, None
    return pd.Timestamp(nav_dates[idx]), float(nav_vals[idx])


def _prepare_nav(nav_df: pd.DataFrame) -> pd.DataFrame:
    cleaned = clean_nav_dataframe(nav_df)
    if cleaned.empty:
        return cleaned
    return cleaned.sort_values("date").reset_index(drop=True)


def _progress(on_progress, i: int, n: int) -> None:
    if on_progress is None or n <= 0 or i % PROGRESS_UPDATE_INTERVAL != 0:
        return
    on_progress(i / n, f"Calculating... {int(i / n * 100)}%")


def calculate_rolling_sip(
    nav_df: pd.DataFrame,
    years: int,
    range_start,
    range_end,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> pd.DataFrame:
    """
    Rolling SIP results for every valid start date.

    Final Value is the redemption proceeds of a ₹1 monthly SIP (units × redemption NAV).
    Multiply by the rupee SIP amount to get the investor's amount. XIRR does not
    depend on the SIP amount, so the amount is applied after this function.
    """
    nav_df = _prepare_nav(nav_df)
    if nav_df.empty:
        return pd.DataFrame()

    range_start = pd.Timestamp(range_start).normalize()
    range_end = pd.Timestamp(range_end).normalize()
    months_target = years * 12
    nav_dates, nav_vals = build_nav_arrays(nav_df)

    snapped_start, _ = get_next_nav_fast(nav_dates, nav_vals, range_start)
    if snapped_start is None or snapped_start > range_end:
        return pd.DataFrame()

    # Month subtraction clips day-of-month (31 May minus 11 months from 30 April
    # becomes 30 May). Keep a few extra days and accept or reject each start
    # from its real instalment and redemption dates.
    nominal_max = range_end - relativedelta(months=months_target - 1)
    max_start = nominal_max + relativedelta(days=3)

    start_candidates = nav_df[
        (nav_df["date"] >= snapped_start) & (nav_df["date"] <= max_start)
    ]["date"].reset_index(drop=True)

    results = []
    n = len(start_candidates)
    unit_amount = 1.0

    for i, start_date in enumerate(start_candidates, 1):
        start_date = pd.Timestamp(start_date)
        if start_date > range_end:
            _progress(on_progress, i, n)
            continue

        cashflows: List[float] = []
        invest_dates: List[pd.Timestamp] = []
        units = 0.0

        _, first_nav_val = get_next_nav_fast(nav_dates, nav_vals, start_date)
        if first_nav_val is None or first_nav_val <= 0:
            _progress(on_progress, i, n)
            continue
        units += unit_amount / first_nav_val
        cashflows.append(-unit_amount)
        invest_dates.append(start_date)

        complete = True
        for m in range(1, months_target):
            scheduled = start_date + relativedelta(months=m)
            if pd.Timestamp(scheduled) > range_end:
                complete = False
                break
            nav_date, nav_val = get_next_nav_fast(nav_dates, nav_vals, scheduled)
            if nav_date is None or nav_date > range_end or nav_val is None or nav_val <= 0:
                complete = False
                break
            units += unit_amount / nav_val
            cashflows.append(-unit_amount)
            invest_dates.append(nav_date)

        if not complete or len(cashflows) != months_target:
            _progress(on_progress, i, n)
            continue

        last_date = invest_dates[-1]
        redeem_date, redeem_nav = get_next_nav_fast(
            nav_dates, nav_vals, last_date + pd.Timedelta(days=1)
        )
        if (
            redeem_date is None
            or redeem_date > range_end
            or redeem_nav is None
            or redeem_nav <= 0
        ):
            _progress(on_progress, i, n)
            continue

        final_value = units * redeem_nav
        cashflows.append(final_value)
        invest_dates.append(redeem_date)

        try:
            irr_val = xirr(cashflows, invest_dates)
        except (OverflowError, ValueError, ZeroDivisionError, FloatingPointError):
            irr_val = np.nan
        if irr_val is None or not np.isfinite(irr_val):
            _progress(on_progress, i, n)
            continue

        results.append(
            {
                "Start Date": start_date.date(),
                "End Date": last_date.date(),
                "Redemption Date": redeem_date.date(),
                "Instalments": months_target,
                "XIRR %": round(float(irr_val) * 100, 2),
                "Final Value": float(final_value),
            }
        )
        _progress(on_progress, i, n)

    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results).sort_values("Start Date").reset_index(drop=True)


def calculate_rolling_lumpsum(
    nav_df: pd.DataFrame,
    years: int,
    range_start,
    range_end,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> pd.DataFrame:
    """
    Rolling lump-sum results for every valid start date.

    Invest once on the start NAV. Redeem on the first NAV on or after
    start + N calendar years, and only when that date is on or before the
    To Date. Final Value is the redemption proceeds of a ₹1 investment.
    CAGR uses the actual day count between the two NAV dates / 365.25.
    """
    nav_df = _prepare_nav(nav_df)
    if nav_df.empty:
        return pd.DataFrame()

    range_start = pd.Timestamp(range_start).normalize()
    range_end = pd.Timestamp(range_end).normalize()
    nav_dates, nav_vals = build_nav_arrays(nav_df)

    snapped_start, _ = get_next_nav_fast(nav_dates, nav_vals, range_start)
    if snapped_start is None or snapped_start > range_end:
        return pd.DataFrame()

    nominal_max = range_end - relativedelta(years=years)
    max_start = nominal_max + relativedelta(days=3)
    start_candidates = nav_df[
        (nav_df["date"] >= snapped_start) & (nav_df["date"] <= max_start)
    ]["date"].reset_index(drop=True)

    nav_lookup = dict(zip(nav_df["date"], nav_df["nav"].astype(float)))
    results = []
    n = len(start_candidates)

    for i, start_date in enumerate(start_candidates, 1):
        start_date = pd.Timestamp(start_date)
        start_nav = float(nav_lookup.get(start_date, np.nan))
        if not np.isfinite(start_nav) or start_nav <= 0:
            _progress(on_progress, i, n)
            continue

        target = start_date + relativedelta(years=years)
        end_date, end_nav = get_next_nav_fast(nav_dates, nav_vals, target)
        if end_date is None or end_date > range_end or end_nav is None or end_nav <= 0:
            _progress(on_progress, i, n)
            continue

        cagr = lump_sum_cagr(start_nav, end_nav, start_date, end_date)
        if not np.isfinite(cagr):
            _progress(on_progress, i, n)
            continue

        results.append(
            {
                "Start Date": start_date.date(),
                "End Date": end_date.date(),
                "Start NAV": start_nav,
                "End NAV": end_nav,
                "CAGR %": round(float(cagr) * 100, 2),
                "Final Value": float(end_nav / start_nav),
            }
        )
        _progress(on_progress, i, n)

    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results).sort_values("Start Date").reset_index(drop=True)


def scale_final_values(result_df: pd.DataFrame, amount: float) -> pd.DataFrame:
    """Scale per-rupee final values to the investor's SIP or lump-sum amount."""
    if result_df is None or result_df.empty:
        return result_df
    scaled = result_df.copy()
    scaled["Final Value"] = scaled["Final Value"] * float(amount)
    return scaled


def _nav_json_to_df(nav_df_json: str) -> pd.DataFrame:
    from io import StringIO

    nav_df = pd.read_json(StringIO(nav_df_json))
    return clean_nav_dataframe(nav_df)


@st.cache_data(show_spinner=False)
def calculate_all_possible_rolling_sip(
    nav_df_json: str,
    years: int,
    range_start: pd.Timestamp,
    range_end: pd.Timestamp,
) -> pd.DataFrame:
    """
    Cached rolling SIP calculation.

    The SIP amount is not part of the cache key: XIRR does not depend on it.
    Scale ``Final Value`` with ``scale_final_values``.
    """
    nav_df = _nav_json_to_df(nav_df_json)
    progress = st.progress(0, text="Calculating rolling periods...")
    try:
        return calculate_rolling_sip(
            nav_df,
            years,
            range_start,
            range_end,
            on_progress=lambda frac, text: progress.progress(frac, text=text),
        )
    finally:
        progress.empty()


@st.cache_data(show_spinner=False)
def calculate_all_possible_rolling_lumpsum(
    nav_df_json: str,
    years: int,
    range_start: pd.Timestamp,
    range_end: pd.Timestamp,
) -> pd.DataFrame:
    """Cached rolling lump-sum calculation. Final Value is per rupee invested."""
    nav_df = _nav_json_to_df(nav_df_json)
    progress = st.progress(0, text="Calculating rolling periods...")
    try:
        return calculate_rolling_lumpsum(
            nav_df,
            years,
            range_start,
            range_end,
            on_progress=lambda frac, text: progress.progress(frac, text=text),
        )
    finally:
        progress.empty()
