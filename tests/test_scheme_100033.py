"""Rolling SIP on a real scheme that used to drop the deep-loss periods."""

from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta

from calculations import calculate_rolling_sip
from data_api import load_nav


def test_aditya_birla_large_midcap_includes_the_2008_losses():
    nav = load_nav("100033")
    result = calculate_rolling_sip(
        nav,
        years=1,
        range_start=pd.Timestamp(date(2006, 5, 1)),
        range_end=pd.Timestamp(date(2010, 12, 31)),
    )
    # Day-after-last-instalment sale: 923 periods, minimum -74.74%, mean 23.41%.
    # Anniversary sale on this same window: 904 periods. The deep 2008 loss
    # stays in the results. Every redemption is the start date plus one year,
    # or the next NAV when that anniversary has no price.
    assert len(result) == 904
    assert float(result["XIRR %"].min()) == -73.75
    assert round(float(result["XIRR %"].mean()), 2) == 22.24
    assert (pd.to_datetime(result["Redemption Date"]) <= pd.Timestamp("2010-12-31")).all()
    assert (pd.to_datetime(result["End Date"]) <= pd.Timestamp("2010-12-31")).all()
    assert (result["Final Value"] > 0).all()
    nav_dates = pd.to_datetime(nav["date"]).sort_values().reset_index(drop=True)
    for _, row in result.iterrows():
        anniversary = pd.Timestamp(row["Start Date"]) + relativedelta(years=1)
        assert pd.Timestamp(row["End Date"]) == anniversary
        expected = nav_dates[nav_dates >= anniversary].iloc[0]
        assert pd.Timestamp(row["Redemption Date"]) == expected
        assert expected >= anniversary


def test_axis_elss_zero_nav_on_7_apr_2013_is_removed():
    nav = load_nav("120503")
    assert (nav["nav"] > 0).all()
    assert not nav["date"].duplicated().any()
    assert pd.Timestamp("2013-04-07") not in set(pd.to_datetime(nav["date"]))
