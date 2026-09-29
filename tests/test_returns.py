"""Tests for XIRR, redemption value, NAV cleaning, the To Date, and lump-sum CAGR."""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
import requests
from dateutil.relativedelta import relativedelta

from calculations import (
    calculate_rolling_lumpsum,
    calculate_rolling_sip,
    lump_sum_cagr,
    scale_final_values,
    xirr,
)
from app_config import DAYS_PER_YEAR, MIN_VALID_PERIODS
from data_api import MfapiError, clean_nav_dataframe, fetch_nav, load_nav, load_search_results
from utils import round_to_step, validate_inputs


def _npv(rate, cashflows, dates):
    t0 = dates[0]
    total = 0.0
    for cf, d in zip(cashflows, dates):
        total += cf / (1.0 + rate) ** ((d - t0).days / DAYS_PER_YEAR)
    return total


def _scipy_xirr(cashflows, dates):
    brentq = pytest.importorskip("scipy.optimize").brentq
    return brentq(lambda rate: _npv(rate, cashflows, dates), -0.9999, 100.0)


def test_xirr_normal_case_matches_brentq():
    dates = [datetime(2016, 1, 15) + relativedelta(months=i) for i in range(12)]
    cashflows = [-1000.0] * 12
    dates.append(dates[-1] + timedelta(days=3))
    cashflows.append(14500.0)

    got = xirr(cashflows, dates)
    expected = _scipy_xirr(cashflows, dates)
    assert abs(got - expected) < 5e-11
    assert 0.05 < got < 0.5


def test_xirr_big_loss_matches_brentq_and_stays_above_minus_100():
    """About -74% a year. Newton-Raphson from 8% steps to roughly -768% here."""
    dates = [datetime(2008, 1, 2) + relativedelta(months=i) for i in range(12)]
    cashflows = [-1000.0] * 12
    dates.append(dates[-1] + timedelta(days=1))
    cashflows.append(6938.75)  # ₹12,000 in, about ₹6,939 back

    got = xirr(cashflows, dates)
    expected = _scipy_xirr(cashflows, dates)
    assert np.isfinite(got)
    assert -0.80 < got < -0.70
    assert abs(got - expected) < 5e-11


def test_xirr_does_not_raise_on_near_total_loss():
    dates = [datetime(2008, 5, 1) + relativedelta(months=i) for i in range(12)]
    cashflows = [-1000.0] * 12
    dates.append(dates[-1] + timedelta(days=1))
    cashflows.append(80.0)
    got = xirr(cashflows, dates)
    # Worse than -99.99% a year has no root inside the bracket. That must
    # come back as "no result", not an exception that stops the whole run.
    assert not np.isfinite(got)


def _monthly_nav(start, months, navs, extra_days=5):
    dates = [pd.Timestamp(start) + relativedelta(months=i) for i in range(months)]
    last = dates[-1]
    for extra in range(1, extra_days + 1):
        dates.append(last + pd.Timedelta(days=extra))
        navs = list(navs) + [navs[-1]]
    return pd.DataFrame({"date": dates[: months + extra_days], "nav": navs[: months + extra_days]})


def test_final_value_is_units_times_redemption_nav():
    start = pd.Timestamp("2014-01-01")
    navs = [10, 12, 15, 14, 16, 18, 20, 19, 17, 21, 22, 25]
    frame = _monthly_nav(start, 12, navs, extra_days=3)
    redeem_nav = 25.0
    out = calculate_rolling_sip(frame, 1, start, start + relativedelta(months=13))
    assert len(out) >= 1
    first = out.iloc[0]
    units = sum(1.0 / nav for nav in navs)
    assert first["Final Value"] == pytest.approx(units * redeem_nav)
    assert first["Final Value"] != pytest.approx(12.0)  # not simply instalments × ₹1


def test_scaling_amount_does_not_change_xirr():
    start = pd.Timestamp("2014-01-01")
    navs = [10 + i for i in range(12)]
    frame = _monthly_nav(start, 12, navs)
    per_rupee = calculate_rolling_sip(frame, 1, "2014-01-01", "2015-06-01")
    small = scale_final_values(per_rupee, 1000)
    large = scale_final_values(per_rupee, 5000)
    assert list(small["XIRR %"]) == list(large["XIRR %"])
    assert list(large["Final Value"]) == pytest.approx(list(small["Final Value"] * 5))


def test_clean_nav_drops_zero_and_duplicate_dates():
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2013-04-07", "2013-04-08", "2013-04-08", "2013-04-09"]),
            "nav": [0.0, 10.0, 12.5, -3.0],
        }
    )
    cleaned = clean_nav_dataframe(frame)
    assert list(cleaned["nav"]) == [12.5]
    assert cleaned.iloc[0]["date"] == pd.Timestamp("2013-04-08")


def test_zero_nav_is_not_used_in_a_sip():
    dates = pd.bdate_range("2015-01-01", "2016-06-01")
    nav = pd.Series(50.0, index=dates)
    nav.loc[pd.Timestamp("2015-04-07")] = 0.0
    frame = pd.DataFrame({"date": nav.index, "nav": nav.values})
    out = calculate_rolling_sip(frame, 1, "2015-01-05", "2016-06-01")
    assert not out.empty
    assert (out["Final Value"] > 0).all()
    assert np.isfinite(out["XIRR %"]).all()


def test_to_date_blocks_instalments_and_redemption_after_the_end():
    frame = pd.DataFrame(
        {
            "date": pd.bdate_range("2018-01-01", "2019-02-15"),
            "nav": 100.0,
        }
    )
    to_date = pd.Timestamp("2018-12-29")
    out = calculate_rolling_sip(frame, 1, "2018-01-02", to_date)
    assert not out.empty
    assert (pd.to_datetime(out["End Date"]) <= to_date).all()
    assert (pd.to_datetime(out["Redemption Date"]) <= to_date).all()
    # 29 Jan 2018 schedules its last instalment on Sat 29 Dec 2018, which snaps
    # into 2019. That period must not be kept.
    assert date(2018, 1, 29) not in set(out["Start Date"])


def test_month_end_start_follows_the_real_sale_date():
    """30 Apr 2019 as the To Date: 29 May 2018 sells on 30 Apr and is kept.
    30 and 31 May 2018 sell on 1 May, which is after the To Date, so they are left out.
    """
    frame = pd.DataFrame({"date": pd.date_range("2018-04-01", "2019-05-05"), "nav": 20.0})
    out = calculate_rolling_sip(frame, 1, "2018-04-01", "2019-04-30")
    starts = set(out["Start Date"])
    assert date(2018, 5, 29) in starts
    assert date(2018, 5, 30) not in starts
    assert date(2018, 5, 31) not in starts
    kept = out[out["Start Date"] == date(2018, 5, 29)].iloc[0]
    assert kept["Redemption Date"] == date(2019, 4, 30)


def test_lump_sum_cagr_known_example():
    # 1 Jan 2020 → 1 Jan 2021 is 366 days. 100 grows to 121.
    # CAGR = 1.21 ** (365.25 / 366) - 1 = 20.9527...% → 20.95% when shown.
    start = datetime(2020, 1, 1)
    end = datetime(2021, 1, 1)
    rate = lump_sum_cagr(100.0, 121.0, start, end)
    assert rate == pytest.approx(1.21 ** (365.25 / 366) - 1)
    assert round(rate * 100, 2) == 20.95

    frame = pd.DataFrame(
        {
            "date": [pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01")],
            "nav": [100.0, 121.0],
        }
    )
    out = calculate_rolling_lumpsum(frame, 1, "2020-01-01", "2021-01-01")
    assert len(out) == 1
    row = out.iloc[0]
    assert row["Start NAV"] == 100.0
    assert row["End NAV"] == 121.0
    assert row["CAGR %"] == 20.95
    assert row["Final Value"] == pytest.approx(1.21)
    scaled = scale_final_values(out, 10000)
    assert scaled.iloc[0]["Final Value"] == pytest.approx(12100.0)

    blocked = calculate_rolling_lumpsum(frame, 1, "2020-01-01", "2020-12-31")
    assert blocked.empty


def test_idcw_plans_are_recognised():
    from utils import is_idcw_plan

    assert is_idcw_plan("HDFC Large & Mid Cap Fund - Direct Plan - IDCW Option")
    assert is_idcw_plan("Old Plan - Dividend Payout")
    assert not is_idcw_plan("Aditya Birla Sun Life Large & Mid Cap Fund - Regular Plan - GROWTH")


def test_round_half_up_not_bankers():
    assert round_to_step(1250) == 1500
    assert round_to_step(1750) == 2000
    assert round_to_step(1000) == 1000
    assert round_to_step(1249) == 1000


def test_validation_counts_the_day_and_the_minimum_period_count():
    too_short = validate_inputs("100033", date(2019, 6, 15), date(2020, 6, 1), 1)
    assert any("less than the selected rolling period" in msg for msg in too_short)

    exact = validate_inputs("100033", date(2018, 1, 1), date(2019, 1, 1), 1)
    assert any(str(MIN_VALID_PERIODS) in msg for msg in exact)
    assert not any("less than the selected rolling period" in msg for msg in exact)

    long_enough = validate_inputs("100033", date(2015, 1, 1), date(2018, 1, 1), 1)
    assert long_enough == []


def _json_response(payload, status_ok=True):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    if not status_ok:
        response.raise_for_status.side_effect = requests.HTTPError("bad")
    return response


def test_load_nav_empty_data_raises(monkeypatch, tmp_path, monkeypatch_cache):
    monkeypatch.setattr(
        "data_api.requests.get",
        lambda *args, **kwargs: _json_response({"meta": {}, "data": []}),
    )
    with pytest.raises(MfapiError):
        load_nav("empty-data-scheme")


def test_fetch_failure_is_not_cached(monkeypatch):
    calls = {"n": 0}

    def boom(*args, **kwargs):
        calls["n"] += 1
        raise requests.ConnectionError("offline")

    monkeypatch.setattr("data_api.requests.get", boom)
    monkeypatch.setattr("data_api.time.sleep", lambda *_: None)
    fetch_nav.clear()
    with pytest.raises(MfapiError):
        fetch_nav("uncached-failure-scheme")
    with pytest.raises(MfapiError):
        fetch_nav("uncached-failure-scheme")
    assert calls["n"] == 6  # 3 retries, twice; the failure was not remembered


def test_excel_exports_actual_final_value_and_lump_sum_columns():
    from utils import build_excel

    sip = pd.DataFrame(
        {
            "Start Date": ["01/01/2015"],
            "End Date": ["01/12/2015"],
            "Redemption Date": ["02/12/2015"],
            "Instalments": [12],
            "XIRR %": [12.5],
            "Invested Amount (₹)": [12000],
            "Final Value (₹)": [13200],
        }
    )
    sip_buf = build_excel(sip, "Example Fund", 1, date(2015, 1, 1), date(2016, 6, 1), True, 1000, mode="sip")
    lump = pd.DataFrame(
        {
            "Start Date": ["01/01/2020"],
            "End Date": ["01/01/2021"],
            "Start NAV": [100.0],
            "End NAV": [121.0],
            "CAGR %": [20.95],
            "Final Value": [12100.0],
        }
    )
    lump_buf = build_excel(
        lump, "Example Fund", 1, date(2020, 1, 1), date(2021, 6, 1), False, 10000, mode="lumpsum"
    )

    def text_of(buf):
        import zipfile
        with zipfile.ZipFile(buf) as book:
            shared = book.read("xl/sharedStrings.xml").decode()
        return shared

    sip_text = text_of(sip_buf)
    lump_text = text_of(lump_buf)
    assert "Final Value (₹)" in sip_text
    assert "1-Year SIP Rolling Return" in sip_text
    assert "CAGR %" in lump_text
    assert "1-Year Rolling Return" in lump_text
    assert "Lump Sum Amount" in lump_text


def test_search_sends_the_query_as_a_parameter(monkeypatch):
    seen = {}

    def fake_get(url, params=None, timeout=None):
        seen["url"] = url
        seen["params"] = params
        return _json_response([{"schemeCode": 5, "schemeName": "A & B Fund"}])

    monkeypatch.setattr("data_api.requests.get", fake_get)
    results = load_search_results("hdfc & mid")
    assert results == [{"schemeCode": "5", "schemeName": "A & B Fund"}]
    assert seen["params"]["q"] == "hdfc & mid"
    assert "hdfc & mid" not in seen["url"]


@pytest.fixture
def monkeypatch_cache(monkeypatch, tmp_path):
    monkeypatch.setattr("data_api.CACHE_DIR", str(tmp_path))
    return tmp_path
