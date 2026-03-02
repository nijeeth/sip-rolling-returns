"""
Core calculation functions for SIP Rolling Returns analysis.
This module contains all calculation logic including XIRR, NAV processing, and rolling SIP calculations.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Tuple, Optional

from config import (
    MAX_XIRR_ITERATIONS,
    XIRR_TOLERANCE,
    XIRR_INITIAL_RATE,
    XIRR_VALIDATION_TOLERANCE,
    DAYS_PER_YEAR,
    PROGRESS_UPDATE_INTERVAL,
    DEFAULT_SIP_AMOUNT
)


def xirr(cashflows: List[float], dates: List[datetime]) -> float:
    """
    Calculate Internal Rate of Return using Newton-Raphson method.
    
    Args:
        cashflows: List of cash flow amounts (negative for investments, positive for returns)
        dates: List of datetime objects corresponding to each cash flow
    
    Returns:
        Annual IRR as a decimal (e.g., 0.12 for 12% return)
        Returns np.nan if calculation fails to converge
    """
    if len(cashflows) < 2:
        return np.nan

    def npv(rate: float) -> float:
        """Calculate Net Present Value at given rate."""
        t0 = dates[0]
        return sum(cf / (1 + rate) ** ((d - t0).days / DAYS_PER_YEAR)
                   for cf, d in zip(cashflows, dates))

    def derivative(rate: float) -> float:
        """Calculate derivative of NPV with respect to rate."""
        t0 = dates[0]
        total = 0.0
        for cf, d in zip(cashflows, dates):
            t = (d - t0).days / DAYS_PER_YEAR
            total -= t * cf / (1 + rate) ** (t + 1)
        return total

    rate = XIRR_INITIAL_RATE
    for _ in range(MAX_XIRR_ITERATIONS):
        drv = derivative(rate)
        if drv == 0:
            break
        adj = npv(rate) / drv
        rate -= adj
        # Guard: if Newton-Raphson overshoots to rate <= -1, (1 + rate)
        # hits zero or goes negative, causing ZeroDivisionError or complex
        # numbers in the next iteration. Clamp back to a safe floor.
        if rate <= -1.0:
            rate = -0.9999
        if abs(adj) < XIRR_TOLERANCE:
            break

    redemption = abs(cashflows[-1])
    return rate if abs(npv(rate)) < redemption * XIRR_VALIDATION_TOLERANCE else np.nan


def build_nav_arrays(nav_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert NAV DataFrame to numpy arrays for fast lookups.
    
    Args:
        nav_df: DataFrame with 'date' and 'nav' columns
    
    Returns:
        Tuple of (date_array, nav_array) as numpy arrays
    """
    return (nav_df['date'].values.astype('datetime64[ns]'),
            nav_df['nav'].values)


def get_next_nav_fast(nav_dates: np.ndarray, nav_vals: np.ndarray, 
                      target: datetime) -> Tuple[Optional[pd.Timestamp], Optional[float]]:
    """
    Find the next available NAV on or after the target date using binary search.
    
    Args:
        nav_dates: Sorted numpy array of dates
        nav_vals: Numpy array of NAV values corresponding to nav_dates
        target: Target date to search from
    
    Returns:
        Tuple of (nav_date, nav_value) or (None, None) if not found
    """
    idx = np.searchsorted(nav_dates, np.datetime64(target, 'ns'), side='left')
    if idx >= len(nav_dates):
        return None, None
    return pd.Timestamp(nav_dates[idx]), nav_vals[idx]


def calculate_all_possible_rolling_sip(nav_df_json: str, years: int, range_start: pd.Timestamp, 
                                      range_end: pd.Timestamp, sip_amount: int = DEFAULT_SIP_AMOUNT,
                                      on_progress=None) -> pd.DataFrame:
    """
    Calculate rolling SIP returns for all possible start dates in the given range.
    
    Args:
        nav_df_json: NAV DataFrame serialized as JSON
        years: Rolling period in years
        range_start: Earliest possible SIP start date
        range_end: Latest possible SIP start date
        sip_amount: Monthly SIP investment amount in rupees
    
    Returns:
        DataFrame with columns: Start Date, End Date, Redemption Date, Instalments, XIRR %
        Returns empty DataFrame if insufficient data
    """
    nav_df = pd.read_json(nav_df_json)
    nav_df['date'] = pd.to_datetime(nav_df['date'])

    if nav_df.empty:
        return pd.DataFrame()

    nav_df = nav_df.sort_values('date').reset_index(drop=True)
    months_target = years * 12
    nav_dates, nav_vals = build_nav_arrays(nav_df)

    snapped_start, _ = get_next_nav_fast(nav_dates, nav_vals, range_start)
    if snapped_start is None:
        return pd.DataFrame()

    max_start = range_end - relativedelta(months=months_target - 1)

    start_candidates = nav_df[
        (nav_df['date'] >= snapped_start) &
        (nav_df['date'] <= max_start)
    ]['date'].reset_index(drop=True)

    results = []
    n = len(start_candidates)

    for i, start_date in enumerate(start_candidates, 1):
        cashflows    = []
        invest_dates = []
        units        = 0.0

        first_nav_date, first_nav_val = get_next_nav_fast(nav_dates, nav_vals, start_date)
        units += sip_amount / first_nav_val
        cashflows.append(-sip_amount)
        invest_dates.append(first_nav_date)

        for m in range(1, months_target):
            scheduled = start_date + relativedelta(months=m)
            nav_date, nav_val = get_next_nav_fast(nav_dates, nav_vals, scheduled)
            if nav_date is None:
                break
            units += sip_amount / nav_val
            cashflows.append(-sip_amount)
            invest_dates.append(nav_date)

        if len(cashflows) != months_target:
            continue

        last_date = invest_dates[-1]

        redeem_date, redeem_nav = get_next_nav_fast(
            nav_dates, nav_vals, last_date + relativedelta(days=1)
        )
        if redeem_date is None:
            continue

        final_value = units * redeem_nav
        cashflows.append(final_value)
        invest_dates.append(redeem_date)

        irr_val = xirr(cashflows, invest_dates)
        if np.isnan(irr_val):
            continue

        results.append({
            'Start Date':      start_date.date(),
            'End Date':        last_date.date(),
            'Redemption Date': redeem_date.date(),
            'Instalments':     months_target,
            'XIRR %':          round(irr_val * 100, 2),
            'Final Value':     round(final_value, 2)
        })

        if on_progress and i % PROGRESS_UPDATE_INTERVAL == 0:
            on_progress(i / n)

    if on_progress:
        on_progress(1.0)

    if not results:
        return pd.DataFrame()

    return pd.DataFrame(results).sort_values('Start Date').reset_index(drop=True)
