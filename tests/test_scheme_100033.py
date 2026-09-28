"""Rolling SIP on a real scheme that used to drop the deep-loss periods."""

from datetime import date

import pandas as pd

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
    # Old Newton solver: 788 periods, minimum about -42.40%.
    # Bracketed solver on this same window: 923 periods, minimum -74.74%.
    assert len(result) == 923
    assert float(result["XIRR %"].min()) == -74.74
    assert round(float(result["XIRR %"].mean()), 2) == 23.41
    assert (pd.to_datetime(result["Redemption Date"]) <= pd.Timestamp("2010-12-31")).all()
    assert (pd.to_datetime(result["End Date"]) <= pd.Timestamp("2010-12-31")).all()
    assert (result["Final Value"] > 0).all()


def test_axis_elss_zero_nav_on_7_apr_2013_is_removed():
    nav = load_nav("120503")
    assert (nav["nav"] > 0).all()
    assert not nav["date"].duplicated().any()
    assert pd.Timestamp("2013-04-07") not in set(pd.to_datetime(nav["date"]))
