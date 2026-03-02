"""
Configuration file for SIP Rolling Returns application.
All constants and configuration parameters are defined here.
"""

import tempfile

# ══════════════════════════════════════════════════════════════════════════════
# XIRR CALCULATION CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
MAX_XIRR_ITERATIONS = 150       # Maximum Newton-Raphson iterations for XIRR convergence
XIRR_TOLERANCE = 1e-10          # Convergence threshold for XIRR calculation
XIRR_INITIAL_RATE = 0.08        # Starting guess for XIRR (8% annual return)
XIRR_VALIDATION_TOLERANCE = 1e-6  # Final validation threshold relative to redemption value

# ══════════════════════════════════════════════════════════════════════════════
# CACHE SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
CACHE_EXPIRY_DAYS = 1           # NAV cache validity in days (refresh daily)
CACHE_DIR = tempfile.gettempdir()  # Directory for cache files

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
MIN_SEARCH_QUERY_LENGTH = 4     # Minimum characters required for fund search
MAX_SEARCH_RESULTS = 15         # Maximum search results to display

# SIP Amount Limits
MIN_SIP_AMOUNT = 500            # Minimum SIP amount in rupees
MAX_SIP_AMOUNT = 100_000        # Maximum SIP amount in rupees
DEFAULT_SIP_AMOUNT = 1000       # Default SIP amount in rupees

# ══════════════════════════════════════════════════════════════════════════════
# CURRENCY FORMATTING
# ══════════════════════════════════════════════════════════════════════════════
CRORE_THRESHOLD = 10_000_000    # Format as crores above this value (1 Cr)
LAKH_THRESHOLD = 100_000        # Format as lakhs above this value (1 L)

# ══════════════════════════════════════════════════════════════════════════════
# ROLLING PERIOD OPTIONS
# ══════════════════════════════════════════════════════════════════════════════
ROLLING_PERIOD_OPTIONS = [1, 2, 3, 5, 7, 10]  # Available rolling period years

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
CREATOR_EMAIL = "nijeeth91@gmail.com"
DATA_SOURCE_NAME = "mfapi.in"
DATA_SOURCE_URL = "https://www.mfapi.in/"
