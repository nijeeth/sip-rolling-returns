# What's new

A short log of what changed for people using the calculator.

## Version 1.2.2 — 29 September 2026

- **Returns follow the real buy and sale.** If a date is closed, the app uses the next trading day. Large losses stay in the results. The rupee amount is the sale value (units times the sale price). Averages stay close to other sites. One very good or very bad period can differ, because those sites often sell on the previous trading day. The How it works tab has a short example.

- **Lump sum or SIP.** Leave Lump sum off for a monthly SIP, which starts at ₹1,000. Turn it on for a one-time investment. The first time you turn it on, the amount starts at ₹10,000.

- **One box to choose a fund.** Type a name and pick the fund in that same box. × clears the choice so you can switch. Search starts after 4 characters, and spaces count. A match can be anywhere in the name. The list shows up to 30 funds. Press Enter to search.

## Version 1.2.0 — 29 September 2026

**The support email is nijeethfish@gmail.com.**

**The two tabs are wide enough to click easily.** Home takes about three quarters of the bar and How It Works the rest. Home is teal and How It Works is a related blue, so they do not look like the purple title. The tab you are on is filled in; the other is a pale tint. The icons are unchanged.

**There is one search box for the fund.** Type a few letters, or a scheme code. Matching funds appear as rows you can click. The row you click stays highlighted. There is no second dropdown.

**The form sits in the centre of the page.**

**"What's new" is on a pale yellow background.**

**The Lump sum switch explains itself.** Turn it on to find rolling returns of a one-time lump-sum investment. Turn it off to find rolling returns of a regular monthly SIP. The first time you turn it on, the amount starts at ₹10,000. A monthly SIP still starts at ₹1,000.

**The lump-sum results heading now says "LUMP SUM Rolling Return".** A SIP still says "SIP Rolling Return".

## Version 1.1.0 — 28 September 2026

**You can now check lump-sum returns as well as SIPs.** Turn on "Lump sum" and the amount box changes to "Lump sum amount". The results then show CAGR instead of XIRR, and the heading says "Rolling Return" without the word SIP. The Excel download stays at the bottom. Its name ends with `_LumpSum` or `_SIP`, so the two files are easy to tell apart.

**Bad periods are no longer missing.** Some 2008-style losses were so deep that the old calculator skipped them or could stop with an error. Those periods are included now. On Aditya Birla SL Large & Mid Cap Regular Growth, 1 year, from 1 May 2006 to 31 December 2010, you should see 923 periods and a worst return of about -74.7%.

**The rupee amount is what you would actually have got on sale.** It used to be estimated from the return percentage, and that estimate was too high. The amount table and the Excel file now use units × the NAV on the sale date.

**Finding a fund is faster.** Type a few letters of the name, or the scheme code. You no longer wait for every scheme in India to load. The code is shown next to the name, so two funds with the same name are not mixed up.

**The To Date is respected.** If the last investment or the sale would fall after the date you chose, that start date is left out.

**Dividend (IDCW) plans show a warning.** Those payouts are not added back, so the return looks lower than the Growth option of the same fund.

**A few quieter corrections.** A NAV of zero is ignored. If you type ₹1,250 it rounds to ₹1,500. A date range that is too short for a reliable result says so straight away. The back-to-top button is visible again. Yesterday's results disappear if the new calculation is rejected.

**Why returns are slightly different from popular sites.** Averages stay very close. One best or worst period can look quite different, because this app sells on the next trading day when an anniversary is a holiday, and some popular sites sell on the previous trading day. The How it works tab has a short example.
