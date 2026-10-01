"""
Settings for the SIP Rolling Returns application.
All constants and configuration parameters are defined here.

This module is named app_config, not config. Streamlit ships its own
config module (streamlit.config). A local config.py can be imported in
its place on Streamlit Cloud and then crash startup with ImportError.
"""

import tempfile

# ══════════════════════════════════════════════════════════════════════════════
# XIRR CALCULATION CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
MAX_XIRR_ITERATIONS = 200       # Maximum bisection steps for the XIRR root
XIRR_TOLERANCE = 1e-12          # Stop when the rate bracket is narrower than this
XIRR_RATE_LOW = -0.9999         # Lowest annual rate searched (-99.99%)
XIRR_RATE_HIGH = 100.0          # Highest annual rate searched (10,000%)

# ══════════════════════════════════════════════════════════════════════════════
# CACHE SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
CACHE_EXPIRY_DAYS = 1           # NAV file-cache validity in days (refresh daily)
CACHE_DIR = tempfile.gettempdir()  # Directory for cache files
NAV_CACHE_TTL_SECONDS = 86400   # Recheck the NAV file cache at least daily
SEARCH_CACHE_TTL_SECONDS = 3600 # Short memory cache for fund-name searches
FUND_LIST_CACHE_TTL_SECONDS = 86400  # Full list, if a caller still requests it

# ══════════════════════════════════════════════════════════════════════════════
# API SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
NAV_API_TIMEOUT = 10            # Timeout for NAV API calls in seconds
SEARCH_API_TIMEOUT = 6          # Timeout for search API calls in seconds
MAX_API_RETRIES = 3             # Maximum retry attempts for failed API calls
RETRY_DELAY_SECONDS = 1.5       # Delay between retry attempts
API_BASE_URL = "https://api.mfapi.in/mf"  # Base URL for mfapi.in

# ══════════════════════════════════════════════════════════════════════════════
# DATA VALIDATION
# ══════════════════════════════════════════════════════════════════════════════
MIN_VALID_PERIODS = 50          # Minimum rolling periods required for statistical validity
DAYS_PER_YEAR = 365.25          # Average days per year (accounting for leap years)

# ══════════════════════════════════════════════════════════════════════════════
# UI SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
PROGRESS_UPDATE_INTERVAL = 50   # Update progress bar every N iterations
MIN_SEARCH_QUERY_LENGTH = 4     # Characters before fund search runs; spaces count
MAX_SEARCH_RESULTS = 30         # Maximum search results to display
AMOUNT_STEP = 500               # SIP and lump-sum amounts round to this step

# SIP Amount Limits
MIN_SIP_AMOUNT = 500            # Minimum SIP amount in rupees
MAX_SIP_AMOUNT = 100_000        # Maximum SIP amount in rupees
DEFAULT_SIP_AMOUNT = 10_000     # Default SIP amount in rupees
DEFAULT_LUMPSUM_AMOUNT = 100_000  # Default one-time amount when Lump sum is first turned on

# ══════════════════════════════════════════════════════════════════════════════
# CURRENCY FORMATTING
# ══════════════════════════════════════════════════════════════════════════════
CRORE_THRESHOLD = 10_000_000    # Format as crores above this value (1 Cr)
LAKH_THRESHOLD = 100_000        # Format as lakhs above this value (1 L)

# ══════════════════════════════════════════════════════════════════════════════
# ROLLING PERIOD OPTIONS
# ══════════════════════════════════════════════════════════════════════════════
ROLLING_PERIOD_OPTIONS = list(range(1, 11))  # Every year from 1 through 10

# ══════════════════════════════════════════════════════════════════════════════
# RETURN DISTRIBUTION BINS
# ══════════════════════════════════════════════════════════════════════════════
RETURN_BINS = [
    (float('-inf'), 0, '< 0%'),
    (0, 5, '0–5%'),
    (5, 10, '5–10%'),
    (10, 15, '10–15%'),
    (15, 20, '15–20%'),
    (20, float('inf'), '> 20%'),
]

# ══════════════════════════════════════════════════════════════════════════════
# APP METADATA
# ══════════════════════════════════════════════════════════════════════════════
APP_TITLE = "SIP Rolling Returns"
APP_ICON = "📈"
CREATOR_NAME = "Nijeeth Muniyandi"
CREATOR_EMAIL = "nijeethfish@gmail.com"
DATA_SOURCE_NAME = "mfapi.in"
DATA_SOURCE_URL = "https://www.mfapi.in/"
