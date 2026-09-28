# SIP Rolling Returns - Modular Version

A Streamlit application for analyzing rolling SIP and lump-sum returns in Indian mutual funds. NAV data comes from [mfapi.in](https://www.mfapi.in/).



##### The documentation, UI, code are generated using AI tools ####



## 📁 Project Structure

```
sip_app/
├── app.py              # Main Streamlit UI (run this file)
├── config.py           # All configuration constants
├── calculations.py     # XIRR, lump-sum CAGR, rolling windows
├── data_api.py         # API calls to mfapi.in
├── utils.py            # Formatting, validation, chart, Excel
├── logic_notes.docx    # How the returns are calculated
├── CHANGELOG.md        # Version history
├── WHATS_NEW.md        # Plain-language notes for each version
└── README.md           # This file
```


## 📦 Module Descriptions

### **app.py** - Main UI
- Streamlit interface
- User input handling
- Results display
- **NO calculation logic** - purely UI

### **config.py** - Configuration
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
  ├── imports: config, data_api, calculations, utils
  └── calls: fetch_nav(), search_funds(), rolling SIP and lump-sum calculations

calculations.py
  ├── imports: config
  └── uses: constants from config

data_api.py
  ├── imports: config
  └── uses: API settings, cache settings

utils.py
  ├── imports: config
  └── uses: formatting constants
```


## 📞 Support

**Created by:** Nijeeth Muniyandi  
**Email:** nijeeth91@gmail.com  
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

All defined in `config.py`:
- `XIRR_TOLERANCE = 1e-12` → Used by `calculations.py`
- `CACHE_EXPIRY_DAYS = 1` → Used by `data_api.py`
- `LAKH_THRESHOLD = 100000` → Used by `utils.py`
- `DEFAULT_SIP_AMOUNT = 1000` → Used by `app.py`

This modular design makes it easy to understand, modify, and extend!

##### The documentation, UI, code are generated using AI tools ####


