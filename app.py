"""
SIP Rolling Returns - Streamlit Application
Main UI file for the SIP Rolling Returns analysis tool.
"""

from datetime import date
from html import escape
import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time

from app_config import (
    MIN_SEARCH_QUERY_LENGTH,
    MAX_SEARCH_RESULTS,
    ROLLING_PERIOD_OPTIONS,
    MIN_SIP_AMOUNT,
    MAX_SIP_AMOUNT,
    DEFAULT_SIP_AMOUNT,
    DEFAULT_LUMPSUM_AMOUNT,
    AMOUNT_STEP,
    MIN_VALID_PERIODS,
    CREATOR_EMAIL,
)
from data_api import MfapiError, fetch_nav, search_funds
from calculations import (
    calculate_all_possible_rolling_lumpsum,
    calculate_all_possible_rolling_sip,
    scale_final_values,
)
from fund_picker import (
    fund_option_label,
    fund_search_text,
    sync_fund_picker_state,
    unique_fund_matches,
)
from utils import (
    validate_inputs,
    plot_rolling_xirr,
    build_excel,
    fmt_inr,
    round_to_step,
    is_idcw_plan,
)

IDCW_WARNING = (
    "This is an IDCW (dividend) plan. Payouts are not reinvested in this calculator, "
    "so the return is lower than the Growth option of the same fund."
)

# Two short lines. Streamlit renders toggle help as Markdown inside the tooltip.
LUMP_SUM_HELP = (
    "To find Rolling Returns of a One Time Lumpsum Investment, turn it ON.\n\n"
    "To find Rolling Returns of a Regular Monthly SIP, turn it OFF."
)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="SIP Rolling Returns Calculator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"  # Hide sidebar
)

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM CSS - DARK THEME WITH PURPLE/BLUE GRADIENT
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* ── Hide sidebar ── */
    [data-testid="stSidebar"] { display: none; }



    /* ── Tabs: full content width, Home ~75% / How It Works ~25% ──
       Streamlit 1.64 uses React Aria tabs (data-testid="stTab"), not Base Web.
       The tab element itself stretches, so the whole area is the click target. */
    [data-testid="stTabs"] {
        width: 100% !important;
    }
    [data-testid="stTabs"] [role="tablist"] {
        display: flex !important;
        width: 100% !important;
        gap: 0 !important;
        background: #eceff3 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    [data-testid="stTabs"] [role="tablist"]::after {
        display: none !important;
    }
    [data-testid="stTabs"] [data-testid="stTab"] {
        flex: 1 1 0% !important;
        min-width: 0 !important;
        height: auto !important;
        min-height: 52px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 14px 10px !important;
        margin: 0 !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        line-height: 1.25 !important;
        text-align: center !important;
        white-space: normal !important;
        border-radius: 0 !important;
        border: none !important;
        cursor: pointer !important;
    }
    [data-testid="stTabs"] [data-testid="stTab"] * {
        white-space: normal !important;
        text-align: center !important;
    }
    /* Teal for Home, a related blue for How It Works.
       Neither repeats the purple title banner. The open tab is filled;
       the other keeps a pale tint of its own color. */
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(1) {
        flex: 3 1 0% !important;
        width: 75% !important;
        max-width: 75% !important;
        background: #ccfbf1 !important;
        color: #115e59 !important;
    }
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(1),
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(1) * {
        color: #115e59 !important;
    }
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(1):hover,
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(1)[data-hovered] {
        background: #99f6e4 !important;
    }
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(1)[data-selected],
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(1)[aria-selected="true"] {
        background: #0f766e !important;
        color: #ffffff !important;
    }
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(1)[data-selected] *,
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(1)[aria-selected="true"] * {
        color: #ffffff !important;
    }
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(1)[data-selected]:hover,
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(1)[aria-selected="true"]:hover {
        background: #0d9488 !important;
    }
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(2) {
        flex: 1 1 0% !important;
        width: 25% !important;
        max-width: 25% !important;
        background: #e0f2fe !important;
        color: #0c4a6e !important;
    }
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(2),
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(2) * {
        color: #0c4a6e !important;
    }
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(2):hover,
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(2)[data-hovered] {
        background: #bae6fd !important;
    }
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(2)[data-selected],
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(2)[aria-selected="true"] {
        background: #0369a1 !important;
        color: #ffffff !important;
    }
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(2)[data-selected] *,
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(2)[aria-selected="true"] * {
        color: #ffffff !important;
    }
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(2)[data-selected]:hover,
    [data-testid="stTabs"] [role="tablist"] > [data-testid="stTab"]:nth-child(2)[aria-selected="true"]:hover {
        background: #0284c7 !important;
    }
    [data-testid="stTabs"] [data-testid="stTab"] .react-aria-SelectionIndicator {
        display: none !important;
    }

    /* ── Center the home input block on wide screens ── */
    .st-key-home_form {
        width: 100% !important;
        max-width: 760px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    /* ── What's new: pale yellow so the note stands out ── */
    .st-key-whats_new_box [data-testid="stExpander"] details {
        background: #fff6d4 !important;
        border: 1px solid #ead98a !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    .st-key-whats_new_box [data-testid="stExpander"] summary {
        background: #fff3c4 !important;
        color: #1f2937 !important;
    }
    .st-key-whats_new_box [data-testid="stExpander"] summary:hover,
    .st-key-whats_new_box [data-testid="stExpander"] summary:focus-visible {
        background: #ffeeb0 !important;
    }
    .st-key-whats_new_box [data-testid="stExpanderDetails"] {
        background: #fff8dc !important;
        border-top-color: #ead98a !important;
    }

    /* ── Lump-sum help tooltip.
       Streamlit 1.64 draws the popover as [data-testid="stTooltipContent"]
       (class stTooltipContent). The "?" is [data-testid="stTooltipIcon"] and
       is left alone so it still opens the tooltip and does not get its own click handler.
       Also tried, and kept as fallbacks: div[data-baseweb="tooltip"],
       [role="tooltip"]. */
    [data-testid="stTooltipContent"],
    .stTooltipContent,
    div[data-baseweb="tooltip"],
    [role="tooltip"] {
        background: #fff6d4 !important;
        background-color: #fff6d4 !important;
        color: #1f2937 !important;
        white-space: pre-line !important;
    }
    [data-testid="stTooltipContent"] p,
    .stTooltipContent p,
    [role="tooltip"] p {
        color: #1f2937 !important;
        margin: 0 0 0.55em 0 !important;
    }
    [data-testid="stTooltipContent"] p:last-child,
    .stTooltipContent p:last-child,
    [role="tooltip"] p:last-child {
        margin-bottom: 0 !important;
    }

    /* ── What's new version line: smaller than a normal page heading ── */
    .st-key-whats_new_box h2 {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        line-height: 1.35 !important;
        letter-spacing: 0 !important;
        margin-top: 0.1rem !important;
        margin-bottom: 0.45rem !important;
    }

    /* ── One fund box: type, clear, and the list chevron share one border ── */
    .st-key-fund_combo {
        border: 1.5px solid #0f766e !important;
        border-radius: 10px !important;
        background: #ffffff !important;
        padding: 0 2px 0 2px !important;
        align-items: stretch !important;
        overflow: hidden !important;
    }
    .st-key-fund_combo:focus-within {
        box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.16) !important;
    }
    .st-key-fund_combo [data-testid="stTextInput"] {
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }
    .st-key-fund_combo [data-testid="stTextInput"] [data-baseweb="input"],
    .st-key-fund_combo [data-testid="stTextInput"] [data-baseweb="base-input"],
    .st-key-fund_combo [data-testid="stTextInputRootElement"] {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
    }
    .st-key-fund_combo [data-testid="stTextInput"] input {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    .st-key-fund_combo [data-testid="stTextInputClearButton"] {
        width: 22px !important;
        height: 22px !important;
        min-height: 22px !important;
        margin-right: 2px !important;
    }
    .st-key-fund_chevron {
        flex: 0 0 42px !important;
        width: 42px !important;
        min-width: 42px !important;
        max-width: 42px !important;
        display: flex !important;
        align-items: center !important;
    }
    .st-key-fund_chevron button {
        background: transparent !important;
        border: none !important;
        border-left: 1px solid #cbd5e1 !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        color: transparent !important;
        min-width: 42px !important;
        width: 42px !important;
        min-height: 42px !important;
        height: 100% !important;
        padding: 0 !important;
        position: relative !important;
    }
    /* Drawn chevron. The button text stays available to screen readers. */
    .st-key-fund_chevron button p {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        padding: 0 !important;
        margin: -1px !important;
        overflow: hidden !important;
        clip: rect(0, 0, 0, 0) !important;
        white-space: nowrap !important;
        border: 0 !important;
    }
    .st-key-fund_chevron button::after {
        content: "" !important;
        display: block !important;
        width: 8px !important;
        height: 8px !important;
        border-right: 2px solid #475569 !important;
        border-bottom: 2px solid #475569 !important;
        transform: rotate(45deg) !important;
        margin: -4px auto 0 auto !important;
    }
    .st-key-fund_chevron button:hover,
    .st-key-fund_chevron button:focus {
        background: #f0fdfa !important;
        border-left: 1px solid #cbd5e1 !important;
    }
    .st-key-fund_chevron button:hover::after,
    .st-key-fund_chevron button:focus::after {
        border-right-color: #115e59 !important;
        border-bottom-color: #115e59 !important;
    }
    .st-key-fund_menu {
        margin-top: 6px !important;
        border: 1px solid #d5dbe8 !important;
        border-radius: 10px !important;
        background: #ffffff !important;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08) !important;
        max-height: 280px !important;
        overflow-y: auto !important;
        padding: 4px !important;
    }
    .st-key-fund_menu [data-testid="stButton"] {
        margin: 0 !important;
    }
    .st-key-fund_menu button {
        width: 100% !important;
        display: flex !important;
        justify-content: flex-end !important;
        text-align: right !important;
        background: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        color: #1e293b !important;
        font-weight: 500 !important;
        padding: 8px 10px !important;
        min-height: 0 !important;
    }
    .st-key-fund_menu button > div,
    .st-key-fund_menu button span[data-has-shortcut="false"] {
        width: 100% !important;
        flex: 1 1 auto !important;
        display: flex !important;
        justify-content: flex-end !important;
        align-items: flex-start !important;
        min-width: 0 !important;
    }
    .st-key-fund_menu button [data-testid="stMarkdownContainer"] {
        flex: 1 1 auto !important;
        width: auto !important;
        min-width: 0 !important;
        text-align: right !important;
        color: #1e293b !important;
    }
    .st-key-fund_menu button [data-testid="stMarkdownContainer"] p {
        width: auto !important;
        text-align: right !important;
        white-space: normal !important;
        color: #1e293b !important;
    }
    .st-key-fund_menu button [data-testid="stIconMaterial"] {
        width: auto !important;
        flex: 0 0 auto !important;
    }
    .st-key-fund_menu button:hover {
        background: #f0fdfa !important;
        color: #1e293b !important;
    }
    .fund-combo-hint {
        color: #64748b;
        font-size: 0.82rem;
        line-height: 1.45;
        margin: 8px 2px 0 2px;
    }

    /* ── Green Download button ── */
    div[data-testid="stDownloadButton"] > button {
        background: linear-gradient(135deg, #16a34a 0%, #15803d 100%) !important;
        border-color: #15803d !important; color: white !important;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background: linear-gradient(135deg, #15803d 0%, #166534 100%) !important;
    }
    /* ── Green Calculate button ── */
    div[data-testid="stButton"] button[kind="primary"],
    div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #16a34a 0%, #15803d 100%) !important;
        border-color: #15803d !important;
        color: white !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover,
    div[data-testid="stButton"] button[data-testid="stBaseButton-primary"]:hover {
        background: linear-gradient(135deg, #15803d 0%, #166534 100%) !important;
        color: white !important;
    }

    /* ── Remove anchor link icon from markdown headings ── */
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a,
    .css-10trblm a, [data-testid="stMarkdownContainer"] h1 a,
    [data-testid="stMarkdownContainer"] h2 a,
    [data-testid="stMarkdownContainer"] h3 a,
    [data-testid="stMarkdownContainer"] h4 a {
        display: none !important;
    }
    .css-10trblm:hover a, h1:hover a, h2:hover a, h3:hover a, h4:hover a {
        display: none !important;
    }

    /* ── Reduce default Streamlit top padding ── */
    .main .block-container {
        padding-top: 2rem !important;
    }

    /* ── Compact inline row widgets ── */
    div[data-testid="column"] > div[data-testid="stSelectbox"],
    div[data-testid="column"] > div[data-testid="stDateInput"],
    div[data-testid="column"] > div[data-testid="stNumberInput"] {
        min-width: 0;
    }
    /* Rolling-period select (React Aria combobox): value and options sit on the right. */
    div[data-testid="stSelectbox"] input[role="combobox"] {
        text-align: right !important;
    }
    [data-testid="stSelectboxVirtualDropdown"] [role="option"] {
        text-align: right !important;
        justify-content: flex-end !important;
    }
    [data-testid="stSelectboxVirtualDropdown"] [role="option"] > div {
        margin-left: auto !important;
        width: auto !important;
        flex: 0 0 auto !important;
        justify-content: flex-end !important;
        text-align: right !important;
    }
    /* SIP amount box — wide enough for 8 digits */
    div[data-testid="stNumberInput"] input {
        max-width: 140px;
    }
    /* go-to-top button styles injected via components.html */
</style>
""", unsafe_allow_html=True)

# Back to top. Drawn on the page itself (not inside a zero-height frame, which hid the button).
st.html(
    """
<style>
  #sip-topbtn {
    position: fixed; bottom: 32px; right: 32px; z-index: 9999;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; border: none; border-radius: 50%;
    width: 52px; height: 52px; font-size: 1.5em;
    cursor: pointer; box-shadow: 0 4px 16px rgba(102,126,234,0.5);
    display: flex; align-items: center; justify-content: center;
    transition: transform 0.2s, box-shadow 0.2s;
  }
  #sip-topbtn:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(102,126,234,0.7); }
</style>
<button id="sip-topbtn" title="Back to top" type="button">↑</button>
<script>
  (function () {
    var btn = document.getElementById('sip-topbtn');
    if (!btn) return;
    if (btn.parentElement !== document.body) document.body.appendChild(btn);
    if (btn.dataset.bound) return;
    btn.dataset.bound = '1';
    btn.addEventListener('click', function () {
      var el = document.querySelector('section.main') ||
               document.querySelector('[data-testid="stAppViewContainer"]') ||
               document.documentElement;
      if (el.scrollTo) el.scrollTo({top: 0, behavior: 'smooth'});
      else el.scrollTop = 0;
    });
  })();
</script>
""",
    unsafe_allow_javascript=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# HERO BANNER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 2rem 36px 2rem; text-align: center; margin-bottom: 0;'>
    <a href='/' target='_self' style='text-decoration: none;'>
        <h1 style='color: #ffffff; font-size: 2.2em; font-weight: 800;
                   text-transform: uppercase; letter-spacing: 0.06em;
                   margin: 0 0 10px 0; line-height: 1.2; cursor: pointer;'>
            SIP Rolling Returns Calculator
        </h1>
    </a>
    <p style='color: rgba(255,255,255,0.82); font-size: 1.05em;
              font-weight: 400; margin: 0;'>
        Analyze historical rolling returns for SIP and lump-sum investments
    </p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# NAVIGATION TABS
# ══════════════════════════════════════════════════════════════════════════════

tab1, tab2 = st.tabs(["🏠 Home", "ℹ️ How It Works"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: HOW IT WORKS
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown(
        """
<div class="toc-box">
  <h4>📋 Table of Contents</h4>
  <a href="#how-to-use">➊ &nbsp;How to Use This Calculator</a>
  <a href="#understanding-results">➋ &nbsp;Understanding the Results</a>
  <a href="#example-interpretation">➌ &nbsp;Example Interpretation</a>
  <a href="#why-returns-differ">➍ &nbsp;Why returns are slightly different from popular sites</a>
  <a href="#calculation-logic">➎ &nbsp;Calculation Logic</a>
</div>
<style>
  .toc-box { background:#f0f4ff; border-radius:8px; padding:16px 22px;
             border:1px solid #c7d2fe; font-family:Arial,sans-serif; }
  .toc-box h4 { color:#4338ca; margin:0 0 10px 0; font-size:0.85em;
                text-transform:uppercase; letter-spacing:0.07em; }
  .toc-box a { color:#4f46e5; text-decoration:none; font-size:0.95em;
               display:block; padding:5px 0; }
  .toc-box a:hover { color:#7c3aed; text-decoration:underline; }
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<a id="how-to-use"></a>', unsafe_allow_html=True)
    st.markdown("""
## 🧭 How to Use This Calculator

**Step 1 — Select a fund**
Use the one box under Select Mutual Fund. Type at least 4 characters of the fund name — spaces count — and pick a fund from the list on that same box. Press Enter to search. The search matches any part of the name and shows up to 30 funds. The × on the right of the box clears the choice so you can switch funds. A scheme code works the same way once it is at least 4 characters. If two funds in the list have the same name, the scheme code is shown beside that name.

**Step 2 — Select Rolling Period**
Choose 1, 2, 3, 5, 7, or 10 years. This is how long each investment is held.

**Step 3 — Choose Date Range**
Set the From and To dates for your analysis window.
- **From Date** must be on or after the fund's inception date.
- **To Date** must be on or before the last available NAV date for the fund.
- Every investment date and the sale date must fall on or before the To Date. If they do not, that start date is left out.

**Step 4 — SIP or Lump sum**
Leave **Lump sum** off for a regular monthly SIP. Turn it on for a one-time lump-sum investment. The amount box label changes to match. A SIP starts at ₹10,000. A lump sum starts at ₹1,00,000 the first time you turn the switch on. The amount must be a multiple of ₹500 (minimum ₹500, maximum ₹1,00,000). A number that falls halfway between two steps is rounded up (₹1,250 becomes ₹1,500).

**Step 5 — Click Calculate**
The app repeats the investment for every valid start date in your selected range.

IDCW (dividend) plans are flagged. Their payouts are not added back, so the return is lower than the Growth option of the same fund.

---
    """, unsafe_allow_html=True)

    st.markdown('<a id="understanding-results"></a>', unsafe_allow_html=True)
    st.markdown("""
## 📊 Understanding the Results

### Statistics Table
- **Min / Max** — Worst and best return across all rolling periods
- **Mean** — Average return across all periods
- **Median** — Middle value (50th percentile)
- **25th / 75th %ile** — Lower and upper quartiles
- **Std Dev** — Volatility of returns

SIP results are labelled **XIRR**. Lump-sum results are labelled **CAGR**. Both are annual percentages.

### Distribution Table
Shows what % of rolling periods fell into each return range (e.g. 0–5%, 5–10%, etc.). Helps you understand the probability of different outcomes.

### Amount Analysis
- **Invested** — For a SIP, the monthly amount × number of months. For a lump sum, the single amount you invested.
- **Worst / Best** — Smallest and largest redemption value across all rolling periods. This is the real sale value (units × NAV), not a figure rebuilt from the return percentage.
- **Percentiles** — Distribution of what that redemption value could have been

### Rolling Return Chart
- **X-axis** — Investment start date
- **Y-axis** — XIRR (SIP) or CAGR (lump sum)
- **Orange line** — Mean return across all periods

Helps visualise how returns varied depending on when you started.

---
    """, unsafe_allow_html=True)

    st.markdown('<a id="example-interpretation"></a>', unsafe_allow_html=True)
    st.markdown("""
## 💡 Example Interpretation

**Scenario:** You ran a 5-year rolling SIP analysis from 2015–2024.

**Results:**
- Mean XIRR: **12.5%**
- Min: **6.2%**
- Max: **18.7%**
- Distribution: **75% of periods returned between 10–15%**

**What this means:**
- On average, investors who started a SIP in this window got **12.5%** annual returns.
- In the worst 5-year period, they got **6.2%**.
- In the best period, they got **18.7%**.
- 3 out of 4 times, returns fell between **10–15%**.

This gives you a realistic expectation of what might happen in future!

⚠️ PAST PERFORMANCE DOES NOT GUARANTEE FUTURE RETURNS.

---
    """, unsafe_allow_html=True)

    st.markdown('<a id="why-returns-differ"></a>', unsafe_allow_html=True)
    st.markdown("""
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

---
    """, unsafe_allow_html=True)

    st.markdown('<a id="calculation-logic"></a>', unsafe_allow_html=True)
    st.markdown("""
## 🔢 Calculation Logic

**SIP.** Each month the tool buys units at the next available NAV. A 1-year SIP is 12 monthly buys. A 2-year SIP is 24, and so on. The sale is on the anniversary: the start date plus the number of years. If that exact day has a NAV, that price is used. If it is a weekend, a market holiday, or any day with no NAV, the sale is the next day that has a NAV. The sale is not the day after the last instalment, and 31 December of the starting year is not used as the one-year date. In the Excel file, **End Date** is that anniversary and **Redemption Date** is the day the units are actually sold. When the anniversary has a NAV, those two dates match. The rupee result is that sale value. XIRR is the annual rate that makes those cash flows balance, using the actual number of days and a 365.25-day year. The rate is found by a bracketed search that still works when the loss is very large.

**Lump sum.** The tool buys once, at the next NAV on or after the start date, and sells at the first NAV on or after the same date N years later. CAGR is (end NAV / start NAV) raised to 1 / years, where years is the actual number of days between those two NAV dates divided by 365.25. The rupee result is amount × end NAV / start NAV.

A period is kept only when every buy and the sale fall on or before the To Date. Zero NAVs are ignored.

For the full steps, assumptions, and edge cases — download the document below.
    """, unsafe_allow_html=True)

    # Download button for calculation logic document
    _doc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logic_notes.docx")
    if os.path.exists(_doc_path):
        with open(_doc_path, "rb") as _f:
            _doc_bytes = _f.read()
        st.download_button(
            label="📄  Download Calculation Logic & Assumptions (Word Document)",
            data=_doc_bytes,
            file_name="SIP_Rolling_Returns_Calculation_Logic.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="content",
        )
    else:
        st.caption(f"_File not found at: {_doc_path}_")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: HOME - MAIN DASHBOARD (NO SIDEBAR)
# ══════════════════════════════════════════════════════════════════════════════

def _latest_whats_new() -> str:
    """Two newest version sections of WHATS_NEW.md, for the home-tab note.

    The collapsed note keeps the previous summary and adds the latest dated
    item above it. Older sections stay in the file and are not repeated here.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "WHATS_NEW.md")
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return ""
    headings = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if not headings:
        return ""
    start = headings[0]
    end = headings[2] if len(headings) > 2 else len(lines)
    return "\n".join(lines[start:end]).strip()


def _clamp_amount(value) -> int:
    """Round half up to the ₹ step, then keep the amount inside the allowed range."""
    rounded = round_to_step(value, AMOUNT_STEP)
    return max(MIN_SIP_AMOUNT, min(MAX_SIP_AMOUNT, rounded))


def _sync_amount_for_mode(lump_sum_on: bool) -> None:
    """Point the shared amount box at the SIP or lump-sum figure.

    The number input is created later with key ``sip_amount``. Session state for
    that key is written here, before the widget exists. The first time Lump sum
    is turned on, the box starts at DEFAULT_LUMPSUM_AMOUNT. After the user has
    a lump-sum amount, switching away and back restores it. SIP does the same
    with DEFAULT_SIP_AMOUNT.
    """
    if "amount_mode" not in st.session_state:
        st.session_state.amount_mode = "sip"
    if "saved_sip_amount" not in st.session_state:
        st.session_state.saved_sip_amount = DEFAULT_SIP_AMOUNT
    if "saved_lump_amount" not in st.session_state:
        st.session_state.saved_lump_amount = None
    if "sip_amount" not in st.session_state:
        st.session_state.sip_amount = DEFAULT_SIP_AMOUNT

    new_mode = "lumpsum" if lump_sum_on else "sip"
    if new_mode != st.session_state.amount_mode:
        if st.session_state.amount_mode == "sip":
            st.session_state.saved_sip_amount = _clamp_amount(st.session_state.sip_amount)
            remembered = st.session_state.saved_lump_amount
            st.session_state.sip_amount = (
                DEFAULT_LUMPSUM_AMOUNT if remembered is None else remembered
            )
        else:
            st.session_state.saved_lump_amount = _clamp_amount(st.session_state.sip_amount)
            st.session_state.sip_amount = st.session_state.saved_sip_amount
        st.session_state.amount_mode = new_mode

    st.session_state.sip_amount = _clamp_amount(st.session_state.sip_amount)
    if new_mode == "lumpsum":
        st.session_state.saved_lump_amount = st.session_state.sip_amount
    else:
        st.session_state.saved_sip_amount = st.session_state.sip_amount


def _toggle_fund_menu() -> None:
    st.session_state.fund_menu_open = not bool(st.session_state.get("fund_menu_open"))


def _choose_fund(code: str, name: str) -> None:
    """Store the scheme for Calculate and show its name in the same box."""
    st.session_state.selected_fund_code = code
    st.session_state.selected_fund_name = name
    st.session_state.fund_query = name
    st.session_state.fund_menu_open = False


@st.fragment
def _render_fund_picker():
    """One combobox. Type and pick in the same box; × clears the selection.

    The scheme code and name are kept in session state. Calculate reads them
    on the next full run. Typing stays inside this fragment so the results
    below are not redrawn on each search.

    The text box commits when the user pauses, and also when they press Enter.
    Search runs only after MIN_SEARCH_QUERY_LENGTH characters. Spaces count.
    """
    st.markdown("#### Select Mutual Fund")
    synced = sync_fund_picker_state(
        st.session_state.get("fund_query", "") or "",
        st.session_state.get("fund_query_seen"),
        st.session_state.get("selected_fund_code"),
        st.session_state.get("selected_fund_name"),
        bool(st.session_state.get("fund_menu_open", False)),
    )
    st.session_state.selected_fund_code = synced["selected_code"]
    st.session_state.selected_fund_name = synced["selected_name"]
    st.session_state.fund_menu_open = synced["menu_open"]
    st.session_state.fund_query_seen = synced["previous_query"]

    with st.container(
        key="fund_combo",
        horizontal=True,
        vertical_alignment="center",
        gap=None,
        wrap=False,
    ):
        st.text_input(
            "Search mutual fund",
            placeholder="Type a fund name",
            label_visibility="collapsed",
            key="fund_query",
            type="search",
            icon="",
            live="300ms",
        )
        st.button(
            "Show or hide matching funds",
            key="fund_chevron",
            type="tertiary",
            on_click=_toggle_fund_menu,
        )

    raw_query = st.session_state.get("fund_query", "") or ""
    query = fund_search_text(raw_query)
    menu_open = bool(st.session_state.get("fund_menu_open"))
    rows = []
    notice = None
    if menu_open and query:
        try:
            matches = search_funds(query)
        except MfapiError:
            st.error("Could not search funds. Check your connection and try again.")
            matches = None
        if matches is not None:
            rows, truncated = unique_fund_matches(matches, MAX_SEARCH_RESULTS)
            if not rows:
                notice = "No matching funds. Try a different name or scheme code."
            elif truncated:
                notice = (
                    f"Showing the first {MAX_SEARCH_RESULTS} matches. "
                    "Type more of the name to narrow the list."
                )
    elif menu_open and raw_query and query is None:
        notice = (
            f"Type at least {MIN_SEARCH_QUERY_LENGTH} characters to search. "
            "Spaces count."
        )

    selected_code = st.session_state.get("selected_fund_code")
    if selected_code and str(selected_code).isalnum() and any(code == selected_code for code, _name in rows):
        st.markdown(
            f"""
<style>
.st-key-fund_menu .st-key-fund_opt_{selected_code} button,
.st-key-fund_menu .st-key-fund_opt_{selected_code} button:hover {{
    background: #e7f6f3 !important;
    font-weight: 600 !important;
}}
</style>
""",
            unsafe_allow_html=True,
        )

    if rows:
        with st.container(key="fund_menu"):
            for code, name in rows:
                st.button(
                    fund_option_label(code, name, rows),
                    key=f"fund_opt_{code}",
                    icon=":material/search:",
                    type="tertiary",
                    width="stretch",
                    on_click=_choose_fund,
                    args=(code, name),
                )
    if notice:
        st.caption(notice)

    st.markdown(
        (
            f'<p class="fund-combo-hint">ⓘ Matches any part of the name · '
            f"up to {MAX_SEARCH_RESULTS} results · search after "
            f"{MIN_SEARCH_QUERY_LENGTH} characters (spaces count). "
            f"Enter also searches.</p>"
        ),
        unsafe_allow_html=True,
    )

    selected_name = st.session_state.get("selected_fund_name")
    shown_results_name = (st.session_state.get("results") or {}).get("fund_name")
    if (
        selected_name
        and is_idcw_plan(selected_name)
        and selected_name != shown_results_name
    ):
        st.warning(IDCW_WARNING)

    return (
        st.session_state.get("selected_fund_code"),
        st.session_state.get("selected_fund_name"),
    )


with tab1:

    # ── Session state defaults (persists across reruns) ──────────────────────
    if 'results' not in st.session_state:
        st.session_state.results = None

    # Centered input block. Results stay full width below this container.
    with st.container(key="home_form"):
        _whats_new = _latest_whats_new()
        if _whats_new:
            with st.container(key="whats_new_box"):
                with st.expander("What's new", expanded=False):
                    st.markdown(_whats_new)

        # One combobox against mfapi. The full scheme list is tens of
        # thousands of rows and made the page slow, so it is not loaded here.
        # Scheme code and name stay in session state for Calculate.
        selected_fund_code, selected_fund_name = _render_fund_picker()

        st.markdown("#### Analysis Period")
        col_yr, col_from, col_to = st.columns([1, 1.35, 1.35])

        with col_yr:
            st.markdown("**Rolling Period**")
            years = st.selectbox(
                "Rolling Years", ROLLING_PERIOD_OPTIONS,
                index=0, label_visibility="collapsed", key="years"
            )

        with col_from:
            st.markdown("**From Date**")
            from_date = st.date_input(
                "From Date", value=None, format="DD/MM/YYYY",
                min_value=date(1990, 1, 1), max_value=date(2100, 12, 31),
                label_visibility="collapsed", key="from_date"
            )

        with col_to:
            st.markdown("**To Date**")
            to_date = st.date_input(
                "To Date", value=None, format="DD/MM/YYYY",
                min_value=date(1990, 1, 1), max_value=date(2100, 12, 31),
                label_visibility="collapsed", key="to_date"
            )

        lump_sum_on = st.toggle(
            "Lump sum",
            value=False,
            key="lump_sum_mode",
            help=LUMP_SUM_HELP,
        )
        # Seed the amount before the number input is created.
        _sync_amount_for_mode(lump_sum_on)
        amount_heading = "Lump sum amount (₹)" if lump_sum_on else "Monthly SIP Amount (₹)"
        st.markdown(f"#### {amount_heading}")
        sip_amount = st.number_input(
            amount_heading,
            min_value=MIN_SIP_AMOUNT,
            max_value=MAX_SIP_AMOUNT,
            step=AMOUNT_STEP,
            label_visibility="collapsed",
            key="sip_amount",
        )

        st.divider()
        calculate_btn = st.button(
            "\u25b6 Calculate Rolling Returns",
            type="primary",
            width="content",
        )
    
    # ══════════════════════════════════════════════════════════════════════════
    # RESULTS AREA
    # ══════════════════════════════════════════════════════════════════════════
    
    if calculate_btn:
        # Drop the previous result immediately so a failed recalculation
        # cannot leave stale numbers on the page.
        st.session_state.results = None
        investment_mode = "lumpsum" if lump_sum_on else "sip"

        # Cheap checks first (no API call). After NAV loads, the same function
        # checks the fund's real first and last NAV dates.
        basic_errors = validate_inputs(selected_fund_code, from_date, to_date, years)

        if basic_errors:
            for e in basic_errors:
                st.error(e)

        else:
            try:
                with st.spinner("Fetching NAV data..."):
                    nav_df = fetch_nav(selected_fund_code)
            except MfapiError:
                nav_df = pd.DataFrame()
                st.error("Could not fetch NAV data. Check your connection and try again.")

            if not nav_df.empty:
                all_errors = validate_inputs(selected_fund_code, from_date, to_date, years, nav_df)

                if all_errors:
                    for e in all_errors:
                        st.error(e)

                else:
                    calculation_amount = sip_amount
                    nav_json = nav_df.to_json(date_format="iso")
                    range_start = pd.Timestamp(from_date)
                    range_end = pd.Timestamp(to_date)

                    start_time = time.time()
                    if investment_mode == "lumpsum":
                        result_df = calculate_all_possible_rolling_lumpsum(
                            nav_df_json=nav_json,
                            years=years,
                            range_start=range_start,
                            range_end=range_end,
                        )
                    else:
                        result_df = calculate_all_possible_rolling_sip(
                            nav_df_json=nav_json,
                            years=years,
                            range_start=range_start,
                            range_end=range_end,
                        )
                    result_df = scale_final_values(result_df, calculation_amount)
                    elapsed = time.time() - start_time

                    n_found = 0 if result_df is None or result_df.empty else len(result_df)
                    if n_found < MIN_VALID_PERIODS:
                        st.error(
                            f"Only {n_found} rolling period(s) fit this date range. "
                            f"At least {MIN_VALID_PERIODS} are needed for a reliable result. "
                            f"Please extend the date range and try again."
                        )

                    else:
                        # Store everything needed to render results in session_state.
                        # A download-button rerun redraws this without calculating again.
                        st.session_state.results = {
                            'result_df':        result_df,
                            'elapsed':          elapsed,
                            'fund_name':        selected_fund_name,
                            'years':            years,
                            'from_date':        from_date,
                            'to_date':          to_date,
                            'sip_amount':       sip_amount,
                            'mode':             investment_mode,
                        }

    # ── Render results from session_state (persists across all reruns) ────────
    # Separating calculation (above) from rendering (here) means that clicking
    # Download Excel — which triggers a rerun — no longer wipes the results.
    if st.session_state.get("results") is not None:
        r           = st.session_state.results
        result_df   = r['result_df']
        elapsed     = r['elapsed']
        fund_name   = r['fund_name']
        years_r     = r['years']
        from_date_r = r['from_date']
        to_date_r   = r['to_date']
        sip_amount_r  = r['sip_amount']
        is_lump = r.get('mode') == 'lumpsum'
        return_col = 'CAGR %' if is_lump else 'XIRR %'
        return_header = 'CAGR %' if is_lump else 'XIRR %'
        result_kind = 'LUMP SUM Rolling Return' if is_lump else 'SIP Rolling Return'
        safe_fund = escape(fund_name or '')
        x = result_df[return_col]

        if lump_sum_on != is_lump:
            st.info("You switched between SIP and Lump sum. Click Calculate to update the results.")

        st.markdown(
            f"<div style='margin-bottom:10px;'>"
            f"<span style='color:#22c55e;font-size:0.9em;font-weight:600;'>✓ Done in {elapsed:.1f}s "
            f"— {len(result_df):,} rolling periods calculated&nbsp;&nbsp;"
            f"<span style='color:#ef5350;font-weight:600;'>⚠ Past performance does not "
            f"guarantee future returns.</span></div>",
            unsafe_allow_html=True
        )

        if is_idcw_plan(fund_name):
            st.warning(IDCW_WARNING)

        st.markdown(
            f"<div style='background:linear-gradient(135deg,#1a237e 0%,#4a148c 100%);"
            f"padding:14px 20px;border-radius:8px;margin:10px 0 16px 0;text-align:center;'>"
            f"<div style='color:#ffffff;font-size:1.05em;font-weight:600;'>📈 Results : "
            f"{years_r}-Year {result_kind} &nbsp;|&nbsp; "
            f"Date Range: {from_date_r.strftime('%d/%m/%Y')} to {to_date_r.strftime('%d/%m/%Y')}</div>"
            f"<div style='color:#ffffff;font-size:1em;font-weight:500;margin-top:5px;'>{safe_fund}</div></div>",
            unsafe_allow_html=True
        )

        bins = [
            round((x < 0).mean()                       * 100, 2),
            round(((x >= 0)  & (x < 5)).mean()         * 100, 2),
            round(((x >= 5)  & (x < 10)).mean()        * 100, 2),
            round(((x >= 10) & (x < 15)).mean()        * 100, 2),
            round(((x >= 15) & (x < 20)).mean()        * 100, 2),
            round((x >= 20).mean()                     * 100, 2),
        ]

        col1, col2 = st.columns(2)

        with col1:
            stats_rows = [
                ('Min',       round(x.min(),    2)),
                ('Max',       round(x.max(),    2)),
                ('Mean',      round(x.mean(),   2)),
                ('Median',    round(x.median(), 2)),
                ('25th %ile', round(float(x.quantile(0.25)), 2)),
                ('75th %ile', round(float(x.quantile(0.75)), 2)),
                ('Std Dev',   round(x.std(),    2)),
            ]
            rows1 = ''.join(
                f"<tr>"
                f"<td style='padding:7px 12px;color:#1e293b;border-right:1px solid #cbd5e1;"
                f"border-bottom:1px solid #e2e8f0;background:{'#f8fafc' if j%2==0 else '#f1f5f9'};'>{m}</td>"
                f"<td style='padding:7px 12px;color:#1e293b;text-align:right;"
                f"border-bottom:1px solid #e2e8f0;background:{'#f8fafc' if j%2==0 else '#f1f5f9'};"
                f"font-weight:600;'>{v:.2f}</td></tr>"
                for j,(m,v) in enumerate(stats_rows)
            )
            st.markdown(
                "<div style='border:1px solid #cbd5e1;border-radius:6px;overflow:hidden;margin-bottom:8px;'>"
                "<div style='background:linear-gradient(135deg,#667eea,#764ba2);padding:8px 12px;"
                "text-align:center;'><b style='color:white;font-size:0.95em;'>Return Statistics (%)</b></div>"
                "<table style='width:100%;border-collapse:collapse;'>"
                "<thead><tr>"
                "<th style='padding:7px 12px;background:#e8eaf6;color:#3730a3;font-weight:700;"
                "font-size:0.82em;text-align:left;border-right:1px solid #c7d2fe;"
                "border-bottom:2px solid #c7d2fe;'>Metric</th>"
                "<th style='padding:7px 12px;background:#e8eaf6;color:#3730a3;font-weight:700;"
                f"font-size:0.82em;text-align:right;border-bottom:2px solid #c7d2fe;'>{return_header}</th>"
                f"</tr></thead><tbody>{rows1}</tbody></table></div>",
                unsafe_allow_html=True
            )

        with col2:
            ranges = ['< 0%', '0–5%', '5–10%', '10–15%', '15–20%', '> 20%']
            rows2 = ''.join(
                f"<tr>"
                f"<td style='padding:7px 12px;color:#1e293b;border-right:1px solid #cbd5e1;"
                f"border-bottom:1px solid #e2e8f0;background:{'#f8fafc' if j%2==0 else '#f1f5f9'};'>{band}</td>"
                f"<td style='padding:7px 12px;color:#1e293b;text-align:right;"
                f"border-bottom:1px solid #e2e8f0;background:{'#f8fafc' if j%2==0 else '#f1f5f9'};"
                f"font-weight:600;'>{p:.2f}</td></tr>"
                for j,(band,p) in enumerate(zip(ranges, bins))
            )
            st.markdown(
                "<div style='border:1px solid #cbd5e1;border-radius:6px;overflow:hidden;margin-bottom:8px;'>"
                "<div style='background:linear-gradient(135deg,#667eea,#764ba2);padding:8px 12px;"
                "text-align:center;'><b style='color:white;font-size:0.95em;'>Return Distribution — % of Times</b></div>"
                "<table style='width:100%;border-collapse:collapse;'>"
                "<thead><tr>"
                "<th style='padding:7px 12px;background:#e8eaf6;color:#3730a3;font-weight:700;"
                "font-size:0.82em;text-align:left;border-right:1px solid #c7d2fe;"
                "border-bottom:2px solid #c7d2fe;'>Range</th>"
                "<th style='padding:7px 12px;background:#e8eaf6;color:#3730a3;font-weight:700;"
                "font-size:0.82em;text-align:right;border-bottom:2px solid #c7d2fe;'>% of Times</th>"
                f"</tr></thead><tbody>{rows2}</tbody></table></div>",
                unsafe_allow_html=True
            )

        # Amount analysis uses the actual redemption value, worst=red, best=green
        if sip_amount_r:
            if is_lump:
                invested = sip_amount_r
                amount_title = (
                    f"&#x1F4B0; {years_r}-Year Lump Sum Amount Analysis "
                    f"&mdash; &#x20B9;{sip_amount_r:,}"
                )
            else:
                invested = sip_amount_r * years_r * 12
                amount_title = (
                    f"&#x1F4B0; {years_r}-Year SIP Amount Analysis "
                    f"&mdash; &#x20B9;{sip_amount_r:,}/month"
                )
            st.markdown(
                "<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"
                "padding: 10px; border-radius: 5px; text-align: center;"
                "margin-top: 20px; margin-bottom: 0px;'>"
                f"<b style='color: white; font-size: 16px;'>{amount_title}</b>"
                "</div>",
                unsafe_allow_html=True,
            )
            fv_series = result_df['Final Value']
            labels = ['Invested', 'Worst', '10th %ile', '25th %ile',
                      'Mean', 'Median', '75th %ile', '90th %ile', 'Best']
            values = [
                fmt_inr(invested),
                fmt_inr(float(fv_series.min())),
                fmt_inr(float(fv_series.quantile(0.10))),
                fmt_inr(float(fv_series.quantile(0.25))),
                fmt_inr(float(fv_series.mean())),
                fmt_inr(float(fv_series.median())),
                fmt_inr(float(fv_series.quantile(0.75))),
                fmt_inr(float(fv_series.quantile(0.90))),
                fmt_inr(float(fv_series.max())),
            ]
            header_cells = "".join(
                f"<th style='padding:8px 14px;background:#e8eaf6;color:#3730a3;"
                f"font-size:0.82em;font-weight:600;text-align:center;"
                f"border-right:1px solid #c7d2fe;white-space:nowrap;'>{lbl}</th>"
                for lbl in labels
            )
            value_cells = "".join(
                f"<td style='padding:10px 14px;"
                f"color:{'#dc2626' if idx==1 else ('#16a34a' if idx==8 else '#1e293b')};"
                f"font-size:0.9em;font-weight:{'700' if idx in (1,8) else '400'};"
                f"text-align:center;border-right:1px solid #cbd5e1;white-space:nowrap;"
                f"background:{'#fef2f2' if idx==1 else ('#f0fdf4' if idx==8 else ('#f8fafc' if idx%2==0 else '#f1f5f9'))};'>{val}</td>"
                for idx,(lbl,val) in enumerate(zip(labels, values))
            )
            st.markdown(
                f"<div style='overflow-x:auto;margin-bottom:20px;'>"
                f"<table style='width:100%;border-collapse:collapse;"
                f"border:1px solid #cbd5e1;overflow:hidden;'>"
                f"<thead><tr>{header_cells}</tr></thead>"
                f"<tbody><tr>{value_cells}</tr></tbody>"
                f"</table></div>",
                unsafe_allow_html=True
            )

        chart_banner = "📊 Rolling CAGR Chart" if is_lump else "📊 Rolling XIRR Chart"
        st.markdown(
            "<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"
            "padding: 10px; border-radius: 5px; text-align: center;"
            "margin-top: 20px; margin-bottom: 10px;'>"
            f"<b style='color: white; font-size: 16px;'>{chart_banner}</b>"
            "</div>",
            unsafe_allow_html=True,
        )
        fig = plot_rolling_xirr(result_df, fund_name, years_r, mode="lumpsum" if is_lump else "sip")
        st.pyplot(fig)
        plt.close(fig)

        st.markdown("<div style='margin-top: 56px;'></div>", unsafe_allow_html=True)

        # Excel download stays at the bottom.
        df_export = result_df.copy()
        df_export['Start Date'] = pd.to_datetime(df_export['Start Date']).dt.strftime('%d/%m/%Y')
        df_export['End Date'] = pd.to_datetime(df_export['End Date']).dt.strftime('%d/%m/%Y')
        if is_lump:
            df_export['Final Value'] = result_df['Final Value'].round(2)
            df_export = df_export[
                ['Start Date', 'End Date', 'Start NAV', 'End NAV', 'CAGR %', 'Final Value']
            ]
        else:
            df_export['Redemption Date'] = pd.to_datetime(df_export['Redemption Date']).dt.strftime('%d/%m/%Y')
            df_export['Invested Amount (₹)'] = sip_amount_r * years_r * 12
            df_export['Final Value (₹)'] = result_df['Final Value'].round(0)
            df_export = df_export[
                [
                    'Start Date', 'End Date', 'Redemption Date', 'Instalments', 'XIRR %',
                    'Invested Amount (₹)', 'Final Value (₹)',
                ]
            ]

        excel_buf = build_excel(
            df_export, fund_name, years_r,
            from_date_r, to_date_r, not is_lump, sip_amount_r or 0,
            mode="lumpsum" if is_lump else "sip",
        )
        safe_name = (fund_name or "fund").replace(' ', '_').replace('/', '-')[:50]
        mode_tag = "LumpSum" if is_lump else "SIP"
        st.download_button(
            label="⬇  Download the complete rolling period calculations for every start date as an Excel file",
            data=excel_buf,
            file_name=f"rolling_xirr_{safe_name}_{mode_tag}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
            type="primary"
        )


# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# NOTES & DISCLAIMERS
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.markdown("""
<div style='background:#fffdf0; border:1px solid #e8d870; border-radius:8px;
            padding:16px 20px; font-size:0.83em; line-height:1.8; color:#1a1a1a;'>

  <span style='color:#1e40af; font-weight:600;'>&#x1F4A1; Note:</span>
  Switch to the "How It Works" tab above for detailed instructions and examples.
  <br><br>

  <span style='color:#1e40af; font-weight:600;'>Special Thanks:</span>
  <a href="https://www.mfapi.in" target="_blank"
     style="color:#1a56db; text-decoration:none; font-weight:600;">mfapi.in</a>
  for providing real-time mutual fund names and NAV data through their freely
  accessible API. Their support enables reliable and up-to-date information for this project.
  <br><br>

  <span style='color:#b91c1c; font-weight:700;'>&#x26A0; Disclaimer:</span>
  This dashboard is a personal project created with AI (Claude, Grok, and ChatGPT).
  The creator is not a software developer/tech person.
  This tool may contain inaccuracies, incomplete logic, or unintended errors.
  All outputs should be interpreted with caution and are not guaranteed to be accurate,
  complete, or suitable for investment decision-making.
  For suggestions/feedback:
  <a href="mailto:{email}"
     style="color:#1a56db; text-decoration:none;">{email}</a>
  <br><br>

  <span style='color:#b91c1c; font-weight:700;'>&#x26A0; Disclaimer:</span>
  This tool is built solely for educational/exploratory purposes.
  Results may contain unintended errors. This is <b>NOT financial advice.</b>
  Mutual fund investments are subject to market risks, and past performance does
  not guarantee future returns. The creator is <b>NOT a SEBI-registered investment
  advisor.</b> Please consult a qualified financial advisor before investing.
  <br><br>

  <span style='color:#b91c1c; font-weight:700;'>&#x26A0; Disclaimer:</span>
  This tool relies on third-party data sources, which may be delayed, inaccurate,
  or incomplete. The creator is NOT responsible for any financial losses, decisions,
  or outcomes resulting from the use of this dashboard. This project is not affiliated
  with, endorsed by, or connected to any Asset Management Company (AMC), regulator,
  or official financial authority.

</div>
""".format(email=CREATOR_EMAIL), unsafe_allow_html=True)
