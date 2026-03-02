"""
SIP Rolling Returns - Streamlit Application
Main UI file for the SIP Rolling Returns analysis tool.
"""

from datetime import date
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time

from config import (
    APP_TITLE,
    APP_ICON,
    MIN_SEARCH_QUERY_LENGTH,
    MAX_SEARCH_RESULTS,
    ROLLING_PERIOD_OPTIONS,
    MIN_SIP_AMOUNT,
    MAX_SIP_AMOUNT,
    DEFAULT_SIP_AMOUNT,
    MIN_VALID_PERIODS,
    CREATOR_NAME,
    CREATOR_EMAIL,
    DATA_SOURCE_NAME,
    DATA_SOURCE_URL
)
from data_api import fetch_nav, search_funds, fetch_all_funds
from calculations import calculate_all_possible_rolling_sip
from utils import validate_inputs, plot_rolling_xirr, build_excel, fmt_inr

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



    /* ── Streamlit native tab overrides: clear nav-button style ── */
    .stTabs [data-baseweb="tab-list"] {
        background: #1a1f36 !important;
        border: none !important;
        border-bottom: 3px solid #667eea !important;
        gap: 0 !important;
        justify-content: center !important;
        padding: 0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        color: #a5b4fc !important;
        font-size: 2.0em !important;
        font-weight: 700 !important;
        padding: 36px 200px !important;
        letter-spacing: 0.04em !important;
        transition: background 0.2s, color 0.2s !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(102,126,234,0.15) !important;
        color: #ffffff !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(102,126,234,0.2) !important;
        color: #ffffff !important;
        border-bottom: 3px solid #a78bfa !important;
    }
    /* Hide the tab highlight/border bars Streamlit adds */
    .stTabs [data-baseweb="tab-highlight"] { display: none !important; }
    .stTabs [data-baseweb="tab-border"]    { display: none !important; }

    /* ── Green Download button ── */
    div[data-testid="stDownloadButton"] > button {
        background: linear-gradient(135deg, #16a34a 0%, #15803d 100%) !important;
        border-color: #15803d !important; color: white !important;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background: linear-gradient(135deg, #15803d 0%, #166534 100%) !important;
    }
    /* ── Green Calculate button ── */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #16a34a 0%, #15803d 100%) !important;
        border-color: #15803d !important;
        color: white !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #15803d 0%, #166534 100%) !important;
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
    /* SIP amount box — wide enough for 8 digits */
    div[data-testid="stNumberInput"] input {
        max-width: 140px;
    }
    /* go-to-top button styles injected via components.html */
</style>
""", unsafe_allow_html=True)

# Floating go-to-top button using JS (anchor href="#" doesn't work in Streamlit iframe)
import streamlit.components.v1 as _components
_components.html("""
<style>
  #topbtn {
    position: fixed; bottom: 32px; right: 32px; z-index: 9999;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; border: none; border-radius: 50%;
    width: 52px; height: 52px; font-size: 1.5em;
    cursor: pointer; box-shadow: 0 4px 16px rgba(102,126,234,0.5);
    display: flex; align-items: center; justify-content: center;
    transition: transform 0.2s, box-shadow 0.2s;
  }
  #topbtn:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(102,126,234,0.7); }
</style>
<button id="topbtn" title="Back to top" onclick="
  var el = window.parent.document.querySelector('section.main') ||
            window.parent.document.querySelector('.block-container') ||
            window.parent.document.querySelector('[data-testid=stAppViewContainer]') ||
            window.parent.document.documentElement;
  el.scrollTo ? el.scrollTo({top:0,behavior:'smooth'}) : el.scrollTop=0;
">↑</button>
""", height=0)

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
        Analyze historical rolling returns for systematic investment plans
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
    import streamlit.components.v1 as _c

    # TOC — uses zero-height iframes to inject anchor divs into the parent page,
    # then scrolls to them. The content itself is plain st.markdown (no box/iframe).
    _c.html("""
<style>
  .toc-box { background:#f0f4ff; border-radius:8px; padding:16px 22px;
             border:1px solid #c7d2fe; font-family:Arial,sans-serif; }
  .toc-box h4 { color:#4338ca; margin:0 0 10px 0; font-size:0.85em;
                text-transform:uppercase; letter-spacing:0.07em; }
  .toc-box a { color:#4f46e5; text-decoration:none; font-size:0.95em;
               display:block; padding:5px 0; cursor:pointer; }
  .toc-box a:hover { color:#7c3aed; text-decoration:underline; }
</style>
<div class="toc-box">
  <h4>📋 Table of Contents</h4>
  <a onclick="scrollToHeading('How to Use This Calculator')">➊ &nbsp;How to Use This Calculator</a>
  <a onclick="scrollToHeading('Understanding the Results')">➋ &nbsp;Understanding the Results</a>
  <a onclick="scrollToHeading('Example Interpretation')">➌ &nbsp;Example Interpretation</a>
  <a onclick="scrollToHeading('Calculation Logic')">➍ &nbsp;Calculation Logic</a>
</div>
<script>
function scrollToHeading(text) {
  var doc = window.parent.document;
  var headings = doc.querySelectorAll('h1, h2, h3, h4');
  for (var i = 0; i < headings.length; i++) {
    if (headings[i].textContent.indexOf(text) !== -1) {
      headings[i].scrollIntoView({behavior: 'smooth', block: 'start'});
      return;
    }
  }
}
</script>
""", height=185)

    st.markdown("""
## 🧭 How to Use This Calculator

**Step 1 — Search for a Fund**
Type at least 4 characters of the fund name or scheme code and select from the dropdown.

**Step 2 — Select Rolling Period**
Choose 1, 2, 3, 5, 7, or 10 years. This is the SIP investment duration for each rolling window.

**Step 3 — Choose Date Range**
Set the From and To dates for your analysis window.
- **From Date** must be on or after the fund's inception date.
- **To Date** must be on or before the last available NAV date for the fund.

**Step 4 — Enter SIP Amount**
Must be a multiple of ₹500. Minimum: ₹500 | Maximum: ₹1,00,000. The app will auto-round if you type a non-multiple.

**Step 5 — Click Calculate**
The app computes rolling returns for every possible SIP start date in your selected range.

---
    """, unsafe_allow_html=True)

    st.markdown("""
## 📊 Understanding the Results

### Statistics Table
- **Min / Max** — Worst and best XIRR achieved across all rolling periods
- **Mean** — Average return across all periods
- **Median** — Middle value (50th percentile)
- **25th / 75th %ile** — Lower and upper quartiles
- **Std Dev** — Volatility of returns

### Distribution Table
Shows what % of rolling periods fell into each return range (e.g. 0–5%, 5–10%, etc.). Helps you understand the probability of different outcomes.

### SIP Amount Analysis
- **Invested** — Total amount put in (SIP amount × number of months)
- **Worst / Best** — Minimum and maximum final corpus across all rolling periods
- **Percentiles** — Distribution of what the final corpus could have been

### Rolling XIRR Chart
- **X-axis** — SIP start date
- **Y-axis** — XIRR percentage
- **Orange line** — Mean return across all periods

Helps visualise how returns varied depending on when you started your SIP.

---
    """, unsafe_allow_html=True)

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

    st.markdown("""
## 🔢 Calculation Logic

This tool uses XIRR (Extended Internal Rate of Return) to calculate rolling SIP returns. The methodology covers how NAV dates are selected, how missing NAV dates are handled, how redemption dates are determined, and when a rolling period is accepted or rejected.

For a full explanation of the calculation steps, assumptions, and edge cases — download the document below.
    """, unsafe_allow_html=True)

    # Download button for calculation logic document
    import os as _os
    _doc_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "logic_notes.docx")
    if _os.path.exists(_doc_path):
        with open(_doc_path, "rb") as _f:
            _doc_bytes = _f.read()
        st.download_button(
            label="📄  Download Calculation Logic & Assumptions (Word Document)",
            data=_doc_bytes,
            file_name="SIP_Rolling_Returns_Calculation_Logic.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=False,
        )
    else:
        st.caption(f"_File not found at: {_doc_path}_")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: HOME - MAIN DASHBOARD (NO SIDEBAR)
# ══════════════════════════════════════════════════════════════════════════════

with tab1:

    # ── Session state defaults (persists across reruns) ──────────────────────
    if 'results' not in st.session_state:
        st.session_state.results = None


    # ══════════════════════════════════════════════════════════════════════════
    # INPUT SECTION - IN MAIN AREA (NO SIDEBAR)
    # ══════════════════════════════════════════════════════════════════════════


    
    # ── Fund Search: combobox via st.selectbox ───────────────────────────────
    # Full fund list is fetched once at startup and cached for the session.
    # st.selectbox has a built-in type-to-filter search field — the user
    # types inside the dropdown and it filters live, exactly like a combobox.
    st.markdown("#### Select Mutual Fund")

    all_funds = fetch_all_funds()

    col_fund, _ = st.columns([3.8, 3])
    with col_fund:
        if not all_funds:
            st.error("Could not load fund list. Check your connection and refresh.")
            selected_fund_code = None
            selected_fund_name = None
        else:
            # Build label→code mapping; label is what the user sees and searches
            fund_labels = [f["schemeName"] for f in all_funds]
            fund_map    = {f["schemeName"]: str(f["schemeCode"]) for f in all_funds}

            chosen_label = st.selectbox(
                "Select Mutual Fund",
                options=fund_labels,
                index=None,
                placeholder="Type to search fund name or scheme...",
                label_visibility="collapsed",
                key="chosen_fund",
            )

            if chosen_label:
                selected_fund_code = fund_map[chosen_label]
                selected_fund_name = chosen_label
            else:
                selected_fund_code = None
                selected_fund_name = None

    # ── Row: Rolling Period | From Date | To Date — all on one line ──────────
    # Columns sized just enough for their content; spacer fills the rest.
    st.markdown("#### Analysis Period")
    col_yr, col_from, col_to, _ = st.columns([1, 1.4, 1.4, 3])

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

    # ── SIP Amount — mandatory field ─────────────────────────────────────────
    st.markdown("#### Monthly SIP Amount (₹)")
    col_sip, col_sip_sp = st.columns([1, 4])
    with col_sip:
        # Seed session state on first load only — avoids the "default + session state" conflict
        if "sip_amount" not in st.session_state:
            st.session_state["sip_amount"] = DEFAULT_SIP_AMOUNT
        else:
            # Round whatever is in the box to nearest 500
            _raw = st.session_state["sip_amount"]
            _rounded = int(round(_raw / 500) * 500)
            _rounded = max(MIN_SIP_AMOUNT, min(MAX_SIP_AMOUNT, _rounded))
            st.session_state["sip_amount"] = _rounded

        sip_amount = st.number_input(
            "Monthly SIP Amount (₹)",
            min_value=MIN_SIP_AMOUNT,
            max_value=MAX_SIP_AMOUNT,
            step=500,
            label_visibility="collapsed",
            key="sip_amount"
        )
    # sip_enabled always True now — SIP is a required input
    sip_enabled = True

    # Action Buttons
    st.divider()
    col_btn1, _ = st.columns([1, 4])
    with col_btn1:
        calculate_btn = st.button("\u25b6 Calculate Rolling Returns", type="primary", use_container_width=True)

    st.divider()
    
    # ══════════════════════════════════════════════════════════════════════════
    # RESULTS AREA
    # ══════════════════════════════════════════════════════════════════════════
    
    if calculate_btn:

        # Fix #2: Use if/else instead of st.stop() so tab2 stays accessible
        # Fix #11: Run a cheap basic check first (no API call) to catch obvious
        # errors early. After fetching NAV, re-run with nav_df for boundary checks.
        # Both passes go through the same function — no duplicate logic.
        basic_errors = validate_inputs(selected_fund_code, from_date, to_date, years)

        if basic_errors:
            for e in basic_errors:
                st.error(e)

        else:
            # Fetch NAV Data
            with st.spinner("Fetching NAV data..."):
                nav_df = fetch_nav(selected_fund_code)

            if nav_df.empty:
                st.error("Could not fetch NAV data. Check your connection and try again.")

            else:
                # Fix #11: Single combined validation with NAV boundaries
                all_errors = validate_inputs(selected_fund_code, from_date, to_date, years, nav_df)

                if all_errors:
                    for e in all_errors:
                        st.error(e)

                else:
                    # SIP amount is now a required field — always use it directly
                    calculation_sip_amount = sip_amount

                    start_time = time.time()
                    result_df = calculate_all_possible_rolling_sip(
                        nav_df_json=nav_df.to_json(date_format='iso'),
                        years=years,
                        range_start=pd.Timestamp(from_date),
                        range_end=pd.Timestamp(to_date),
                        sip_amount=calculation_sip_amount
                    )
                    elapsed = time.time() - start_time

                    if result_df.empty or len(result_df) < MIN_VALID_PERIODS:
                        st.error("The dataset is too small to generate reliable results. Please extend your date range and try again.")

                    else:
                        # Store everything needed to render results in session_state.
                        # This means a download-button rerun or any other rerun will
                        # re-render the results without re-running the calculation.
                        st.session_state.results = {
                            'result_df':        result_df,
                            'elapsed':          elapsed,
                            'fund_name':        selected_fund_name,
                            'years':            years,
                            'from_date':        from_date,
                            'to_date':          to_date,
                            'sip_amount':       sip_amount,
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
        x = result_df['XIRR %']

        st.markdown(
            f"<div style='margin-bottom:10px;'>"
            f"<span style='color:#22c55e;font-size:0.9em;font-weight:600;'>✓ Done in {elapsed:.1f}s "
            f"— {len(result_df):,} rolling periods calculated&nbsp;&nbsp;"
            f"<span style='color:#ef5350;font-weight:600;'>⚠ Past performance does not "
            f"guarantee future returns.</span></div>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<div style='background:linear-gradient(135deg,#1a237e 0%,#4a148c 100%);"
            f"padding:14px 20px;border-radius:8px;margin:10px 0 16px 0;text-align:center;'>"
            f"<div style='color:#ffffff;font-size:1.05em;font-weight:600;'>📈 Results : "
            f"{years_r}-Year SIP Rolling Return &nbsp;|&nbsp; "
            f"Date Range: {from_date_r.strftime('%d/%m/%Y')} to {to_date_r.strftime('%d/%m/%Y')}</div>"
            f"<div style='color:#ffffff;font-size:1em;font-weight:500;margin-top:5px;'>{fund_name}</div></div>",
            unsafe_allow_html=True
        )

        p25 = round(float(x.quantile(0.25)), 2)
        p75 = round(float(x.quantile(0.75)), 2)
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
                "font-size:0.82em;text-align:right;border-bottom:2px solid #c7d2fe;'>XIRR %</th>"
                f"</tr></thead><tbody>{rows1}</tbody></table></div>",
                unsafe_allow_html=True
            )

        with col2:
            ranges = ['< 0%', '0–5%', '5–10%', '10–15%', '15–20%', '> 20%']
            rows2 = ''.join(
                f"<tr>"
                f"<td style='padding:7px 12px;color:#1e293b;border-right:1px solid #cbd5e1;"
                f"border-bottom:1px solid #e2e8f0;background:{'#f8fafc' if j%2==0 else '#f1f5f9'};'>{r}</td>"
                f"<td style='padding:7px 12px;color:#1e293b;text-align:right;"
                f"border-bottom:1px solid #e2e8f0;background:{'#f8fafc' if j%2==0 else '#f1f5f9'};"
                f"font-weight:600;'>{p:.2f}</td></tr>"
                for j,(r,p) in enumerate(zip(ranges, bins))
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

        # SIP Amount Analysis — clean table, worst=red, best=green
        if sip_amount_r:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 10px; border-radius: 5px; text-align: center;
                        margin-top: 20px; margin-bottom: 0px;'>
                <b style='color: white; font-size: 16px;'>&#x1F4B0; {yr}-Year SIP Amount Analysis &mdash; &#x20B9;{amt:,}/month</b>
            </div>
            """.format(yr=years_r, amt=sip_amount_r), unsafe_allow_html=True)

            months    = years_r * 12
            invested  = sip_amount_r * months
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

        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 10px; border-radius: 5px; text-align: center;
                    margin-top: 20px; margin-bottom: 10px;'>
            <b style='color: white; font-size: 16px;'>📊 Rolling XIRR Chart</b>
        </div>
        """, unsafe_allow_html=True)
        fig = plot_rolling_xirr(result_df, fund_name, years_r)
        st.pyplot(fig)
        plt.close(fig)

        st.markdown("<div style='margin-top: 56px;'></div>", unsafe_allow_html=True)

        # Excel Download
        df_export = result_df.copy()
        df_export['Start Date']      = pd.to_datetime(df_export['Start Date']).dt.strftime('%d/%m/%Y')
        df_export['End Date']        = pd.to_datetime(df_export['End Date']).dt.strftime('%d/%m/%Y')
        df_export['Redemption Date'] = pd.to_datetime(df_export['Redemption Date']).dt.strftime('%d/%m/%Y')

        # Always add invested/total columns — SIP amount is always present
        if sip_amount_r:
            months_xl   = years_r * 12
            invested_xl = sip_amount_r * months_xl
            df_export['Invested Amount (\u20b9)'] = invested_xl
            df_export['Total Amount (\u20b9)']    = result_df['Final Value'].apply(lambda v: round(v, 0))

        excel_buf = build_excel(
            df_export, fund_name, years_r,
            from_date_r, to_date_r, True, sip_amount_r or 0
        )
        safe_name = fund_name.replace(' ', '_').replace('/', '-')[:50]
        st.download_button(
            label="⬇  Download the complete rolling period calculations for every start date as an Excel file",
            data=excel_buf,
            file_name=f"rolling_xirr_{safe_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
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
  <a href="mailto:nijeeth91@gmail.com"
     style="color:#1a56db; text-decoration:none;">nijeeth91@gmail.com</a>
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
""", unsafe_allow_html=True)
