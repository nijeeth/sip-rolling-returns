# Changelog

All notable changes to the SIP Rolling Returns Calculator are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-09-28

### Added

- Lump-sum rolling returns. Turn on **Lump sum** to invest once instead of every month. The result is a CAGR, using the actual number of days between the buy NAV and the sell NAV and a 365.25-day year. The Excel file uses lump-sum columns and the file name ends with `_LumpSum`.
- Fund search as you type (name, or a scheme code). The scheme code is shown in the list so funds that share a name can be told apart.
- A warning on IDCW (dividend) plans, because payouts are not added back.
- A collapsed "What's new" note on the home page, plus `WHATS_NEW.md`.
- Tests for deep-loss XIRR, the real redemption value, zero NAVs, the To Date, and lump-sum CAGR.
- A plain-English section, "Why returns are slightly different from popular sites", in the README, the How it works tab, and the calculation notes.
- The project is released under the MIT License. See `LICENSE`.

### Fixed

- Very poor periods are no longer dropped or able to crash the calculation. The annual return is found by searching between -99.99% and 10,000%, instead of stepping from an 8% guess. For Aditya Birla SL Large & Mid Cap Regular Growth (scheme 100033), 1 year, 1 May 2006 to 31 December 2010, the calculator now keeps 923 periods and a worst return of -74.74% (it previously kept 788 periods and stopped around -42%).
- The rupee result is the actual sale value (units × NAV on the sale date). It is no longer rebuilt from the XIRR percentage, which overstated the amount.
- A zero NAV is ignored, and a repeated date is kept once. This removes the 0.00 NAV on Axis ELSS Direct (scheme 120503) for 7 April 2013.
- Choosing a fund no longer depends on the name alone. Two schemes with the same name no longer load whichever one happened to be last in the list.
- NAV data is rechecked at least once a day. A failed download is not remembered as "there is no data", so a later retry can succeed.
- If a new calculation fails its checks, the previous results are cleared instead of staying on screen under the error.
- The sale, and every monthly investment, must fall on or before the To Date. A start date whose sale would land after the To Date is left out.
- Start dates around month-ends are judged from the real investment and sale dates, not from a month subtraction that can clip 31 down to 30.
- A date range that is shorter than the rolling period once the day of the month is counted is rejected up front. A range that is only as long as the rolling period itself now says that at least 50 periods are needed, instead of passing the first check and then saying the dataset is too small.
- An amount halfway between two ₹500 steps rounds half up (₹1,250 becomes ₹1,500).
- Changing the SIP or lump-sum amount no longer recalculates every period. The return does not depend on the amount; only the rupee value is scaled.
- A fund history with no rows no longer causes a crash.
- The back-to-top button is drawn on the page. It used to sit in a zero-height frame, so it never appeared.
- Fund search text is sent as a proper search parameter, including names that contain spaces or `&`.
- Fund names shown in the results header are escaped, so an unusual character in a name cannot change the page layout.
- Package versions are pinned. The Excel file is still written with xlsxwriter. `use_container_width` and `st.components.v1.html` are no longer used.

### Changed

- The home page no longer downloads the full list of schemes on every visit.
- SIP Excel column "Total Amount" is now "Final Value (₹)", and it is the actual redemption value. Lump-sum files use Start Date, End Date, Start NAV, End NAV, CAGR %, Final Value.
- The calculation-logic document and the How it works tab describe the corrected SIP rules and the lump-sum rules.

## [1.0.0] - 2026-03-02

### Added

- First public version of the SIP rolling-returns calculator, with NAV data from mfapi.in, summary tables, a chart, and an Excel download.
