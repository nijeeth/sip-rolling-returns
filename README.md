# SIP Rolling Returns - Modular Version

A Streamlit application for analyzing rolling SIP and lump-sum returns in Indian mutual funds. NAV data comes from [mfapi.in](https://www.mfapi.in/).

Choose a fund in one box. Type at least 4 characters of the name (spaces count) and pick a match from the list on that box. Press Enter to search. The search matches any part of the name and shows up to 30 funds. × clears the choice so you can switch funds.

## Why returns are slightly different from popular sites

Checked on 28 September 2026 against Advisorkhoj and PrimeInvestor. The funds were Aditya Birla SL Large & Mid Cap Regular Growth (scheme 100033), Parag Parikh Flexi Cap Direct (scheme 122639), and HDFC Flexi Cap Regular (scheme 101762). The check used 1-year and 3-year lump sums, with a new start on every trading day.

Averages, medians (the middle value), and the share of periods that lost money match Advisorkhoj within about 0.1 percentage points. Aditya Birla SL Large & Mid Cap Regular Growth, 1-year rolling, start dates from 3 April 2006 to today, averages 14.63% in this app and 14.63% on Advisorkhoj. They match PrimeInvestor within about 0.1 to 0.45 points. Parag Parikh Flexi Cap Direct Growth, 3-year rolling, sale dates from 24 September 2021 to 24 September 2026, averages 22.85% in this app and 23.26% on PrimeInvestor (about 0.4 points apart). The single best period and the single worst period can differ by more.

The main reason is the sale date. When the anniversary falls on a weekend or a market holiday, this app sells on the next trading day. The money is held for at least the full number of years. Advisorkhoj and PrimeInvestor sell on the last trading day on or before the anniversary.

On a jumpy day, that choice can change one period a lot. Example: a buy in the Aditya Birla fund on 19 January 2007. This app sells on Monday 21 January 2008, for a return of +23.87%. Advisorkhoj sells on Friday 18 January 2008, for a return of +40.66%. These gaps mostly cancel out in the average. They can still move the best and worst numbers.

A smaller difference is how a year is counted. This app divides the real number of days held by 365.25. The websites treat the holding as exactly 1 year, or exactly 3 years, and so on. Their 1-year figure is simply the gain over that span. The effect is very small.

The dates do not mean the same thing on every site. In this app, From is the first buy date. To is the last date a sale is allowed. On Advisorkhoj, the start date is also a buy date, and the check runs to the latest price. On PrimeInvestor, the start date and the end date are sale dates. To match PrimeInvestor, set From to its start date minus the number of years, and set To to its end date. To match Advisorkhoj, set From to its start date and set To to today.

This app can show one fewer period at the very end. That happens when the last anniversary has no price after it yet. For example, the anniversary falls on a weekend just before today.

Prices come from mfapi.in, which passes on AMFI data. On every shared date that was checked, those prices matched Advisorkhoj. mfapi has no prices before about April 2006, so a longer history on another site cannot be matched here. Other sites may use a different data source, or skip a day now and then. That explains the small gaps that are left.

The same sale rule applies to a SIP. If a payment day is closed, the app buys on the next trading day. The sale is the anniversary of the start date: that date plus the number of years. A SIP that starts on 1 January 2024 is sold on 1 January 2025. Every other start date uses its own anniversary. If that day is a weekend or a market holiday, or it has no NAV, the app sells on the next day that has a NAV. It does not sell on the day after the last monthly payment, and it does not treat 31 December of the same year as one full year. The SIP percentage uses those real dates. It is not a simple gain from the first price to the last price.

##### The documentation, UI, code are generated using AI tools ####



## 📁 Project Structure

```
sip_app/
├── app.py              # Main Streamlit UI (run this file)
├── app_config.py       # All configuration constants
├── fund_picker.py      # Fund search box helpers
├── calculations.py     # XIRR, lump-sum CAGR, rolling windows
├── data_api.py         # API calls to mfapi.in
├── utils.py            # Formatting, validation, chart, Excel
├── logic_notes.docx    # How the returns are calculated
├── CHANGELOG.md        # Version history
├── WHATS_NEW.md        # Plain-language notes for each version
├── LICENSE             # MIT License
└── README.md           # This file
```


## 📦 Module Descriptions

### **app.py** - Main UI
- Streamlit interface
- User input handling
- Results display
- **NO calculation logic** - purely UI

### **app_config.py** - Configuration
- All constants in one place
- Easy to modify settings
- No logic, just values

### **calculations.py** - Core Calculations
- XIRR via a bracketed search (handles deep losses)
- Lump-sum CAGR from the two NAV dates
- Rolling SIP and lump-sum windows
- The rupee result is the actual redemption value
- **No UI code** in the pure functions

### **data_api.py** - API Interactions
- Fetch NAV data from mfapi.in
- Search mutual funds
- File-based caching
- Retry logic for API failures

### **utils.py** - Helper Functions
- Input validation
- Currency formatting (₹ Lakh/Crore)
- Date formatting
- Chart generation
- Excel export



## 🎨 File Dependencies

```
app.py
  ├── imports: app_config, data_api, calculations, utils
  └── calls: fetch_nav(), search_funds(), rolling SIP and lump-sum calculations

calculations.py
  ├── imports: app_config
  └── uses: constants from app_config

data_api.py
  ├── imports: app_config
  └── uses: API settings, cache settings

utils.py
  ├── imports: app_config
  └── uses: formatting constants
```


## 📞 Support

**Created by:** Nijeeth Muniyandi  
**Email:** nijeethfish@gmail.com  
**Data Source:** [mfapi.in](https://www.mfapi.in/)

## ⚠️ Disclaimer

This tool is for educational purposes only. Not financial advice. Mutual fund investments are subject to market risks. Past performance does not guarantee future returns. Consult a qualified financial advisor before investing.

---

## 🎓 Learn More

### Understanding the Code Flow

1. **User enters inputs** → `app.py` (UI)
2. **Validate inputs** → `utils.validate_inputs()` 
3. **Fetch NAV data** → `data_api.fetch_nav()`
4. **Calculate returns** → `calculations.calculate_rolling_sip()` or `calculate_rolling_lumpsum()`
5. **Display results** → `app.py` (UI)
6. **Generate Excel** → `utils.build_excel()`

### Constants Used Throughout

All defined in `app_config.py`:
- `XIRR_TOLERANCE = 1e-12` → Used by `calculations.py`
- `CACHE_EXPIRY_DAYS = 1` → Used by `data_api.py`
- `LAKH_THRESHOLD = 100000` → Used by `utils.py`
- `DEFAULT_SIP_AMOUNT = 10000` → Used by `app.py` (monthly SIP)
- `DEFAULT_LUMPSUM_AMOUNT = 100000` → Used by `app.py` (one-time lump sum)
- `ROLLING_PERIOD_OPTIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` → Used by `app.py`

This modular design makes it easy to understand, modify, and extend!

## License

This project is under the [MIT License](LICENSE).

##### The documentation, UI, code are generated using AI tools ####


