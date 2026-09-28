# What's new

A short log of what changed for people using the calculator.

## Version 1.1.0 — 28 September 2026

**You can now check lump-sum returns as well as SIPs.** Turn on "Lump sum" and the amount box changes to "Lump sum amount". The results then show CAGR instead of XIRR, and the heading says "Rolling Return" without the word SIP. The Excel download stays at the bottom. Its name ends with `_LumpSum` or `_SIP`, so the two files are easy to tell apart.

**Bad periods are no longer missing.** Some 2008-style losses were so deep that the old calculator skipped them or could stop with an error. Those periods are included now. On Aditya Birla SL Large & Mid Cap Regular Growth, 1 year, from 1 May 2006 to 31 December 2010, you should see 923 periods and a worst return of about -74.7%.

**The rupee amount is what you would actually have got on sale.** It used to be estimated from the return percentage, and that estimate was too high. The amount table and the Excel file now use units × the NAV on the sale date.

**Finding a fund is faster.** Type a few letters of the name, or the scheme code. You no longer wait for every scheme in India to load. The code is shown next to the name, so two funds with the same name are not mixed up.

**The To Date is respected.** If the last investment or the sale would fall after the date you chose, that start date is left out.

**Dividend (IDCW) plans show a warning.** Those payouts are not added back, so the return looks lower than the Growth option of the same fund.

**A few quieter corrections.** A NAV of zero is ignored. If you type ₹1,250 it rounds to ₹1,500. A date range that is too short for a reliable result says so straight away. The back-to-top button is visible again. Yesterday's results disappear if the new calculation is rejected.
