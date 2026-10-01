"""
Utility functions for SIP Rolling Returns application.
Includes formatting, validation, charting, and Excel export functions.
"""

from typing import List, Optional

# Bind picker helpers before pandas or matplotlib import. A circular import
# during those libraries must not hide fund_option_label.
from fund_picker import (
    fund_option_label,
    fund_search_text,
    sync_fund_picker_state,
    unique_fund_matches,
)

import math
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from io import BytesIO

from app_config import (
    AMOUNT_STEP,
    CRORE_THRESHOLD,
    DEFAULT_LUMPSUM_AMOUNT,
    DEFAULT_SIP_AMOUNT,
    LAKH_THRESHOLD,
    MAX_SIP_AMOUNT,
    MIN_SIP_AMOUNT,
    MIN_VALID_PERIODS,
    CREATOR_NAME,
    CREATOR_EMAIL,
    DATA_SOURCE_URL
)


def round_to_step(value: float, step: int = AMOUNT_STEP) -> int:
    """Round half up to the nearest multiple of ``step`` (1250 → 1500 when step is 500)."""
    if step <= 0:
        raise ValueError("step must be positive")
    return int(math.floor(float(value) / step + 0.5)) * step


def format_indian_int(value: int) -> str:
    """Group an integer with Indian commas and no decimals (10000000 → ``1,00,00,000``)."""
    number = int(value)
    sign = "-" if number < 0 else ""
    digits = str(abs(number))
    if len(digits) <= 3:
        return sign + digits
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while head:
        groups.append(head[-2:])
        head = head[:-2]
    groups.reverse()
    return sign + ",".join(groups) + "," + tail


def parse_indian_amount(text: Optional[str]) -> Optional[int]:
    """Read a whole-rupee amount. Commas may be Indian or Western. Decimals are rejected."""
    if text is None:
        return None
    raw = str(text).strip().replace("₹", "").replace(" ", "")
    if "." in raw:
        raw = raw.split(".", 1)[0]
    if raw == "":
        return None
    raw = raw.replace(",", "")
    if not raw.isdigit():
        return None
    return int(raw)


def clamp_amount(value) -> int:
    """Round half up to the ₹ step, then keep the amount inside the allowed range."""
    rounded = round_to_step(value, AMOUNT_STEP)
    return max(MIN_SIP_AMOUNT, min(MAX_SIP_AMOUNT, rounded))


def resolve_amount_state(
    lump_sum_on: bool,
    *,
    amount_mode: Optional[str],
    saved_sip_amount: Optional[int],
    saved_lump_amount: Optional[int],
    sip_amount: Optional[int],
    sip_amount_text: Optional[str],
) -> dict:
    """Choose the SIP or lump-sum figure and the text shown in the amount box.

    A fresh SIP starts at DEFAULT_SIP_AMOUNT. The first time Lump sum is turned
    on, the box starts at DEFAULT_LUMPSUM_AMOUNT. Later switches restore the
    amount last used for that mode. Typed text is parsed, rounded to the step,
    and shown again with Indian grouping and no decimals.
    """
    mode = amount_mode if amount_mode in ("sip", "lumpsum") else "sip"
    saved_sip = DEFAULT_SIP_AMOUNT if saved_sip_amount is None else int(saved_sip_amount)
    saved_lump = None if saved_lump_amount is None else int(saved_lump_amount)
    current = DEFAULT_SIP_AMOUNT if sip_amount is None else int(sip_amount)

    if sip_amount_text is not None:
        parsed = parse_indian_amount(sip_amount_text)
        if parsed is not None:
            current = parsed

    new_mode = "lumpsum" if lump_sum_on else "sip"
    if new_mode != mode:
        if mode == "sip":
            saved_sip = clamp_amount(current)
            current = DEFAULT_LUMPSUM_AMOUNT if saved_lump is None else saved_lump
        else:
            saved_lump = clamp_amount(current)
            current = saved_sip
        mode = new_mode

    current = clamp_amount(current)
    if mode == "lumpsum":
        saved_lump = current
    else:
        saved_sip = current

    return {
        "amount_mode": mode,
        "saved_sip_amount": saved_sip,
        "saved_lump_amount": saved_lump,
        "sip_amount": current,
        "sip_amount_text": format_indian_int(current),
    }


def is_idcw_plan(fund_name: Optional[str]) -> bool:
    """True for dividend / IDCW plans, whose NAV drop is not offset by reinvestment here."""
    if not fund_name:
        return False
    upper = fund_name.upper()
    return "IDCW" in upper or "DIVIDEND" in upper


def format_date(dt: Optional[datetime]) -> str:
    """
    Format a date for display.
    
    Args:
        dt: datetime or pd.Timestamp object, or None
    
    Returns:
        Formatted date string in DD/MM/YYYY format, or "—" if None
    """
    if dt is None:
        return "—"
    if isinstance(dt, pd.Timestamp):
        dt = dt.date()
    return dt.strftime("%d/%m/%Y")


def fmt_inr(v: float) -> str:
    """
    Format a number as Indian Rupees with Lakh/Crore notation.
    Handles negative values by formatting the absolute amount with a leading minus sign.
    
    Args:
        v: Value to format
    
    Returns:
        Formatted string (e.g., '₹5.25 L', '₹1.50 Cr', '₹5,000', '-₹3.20 L')
    """
    sign = '-' if v < 0 else ''
    v = int(round(abs(v)))
    if v >= CRORE_THRESHOLD:
        return f'{sign}₹{v/10_000_000:.2f} Cr'
    elif v >= LAKH_THRESHOLD:
        return f'{sign}₹{v/100_000:.2f} L'
    return f'{sign}₹{format_indian_int(v)}'


def validate_inputs(selected_fund_code: Optional[str], from_date: Optional[date], 
                   to_date: Optional[date], years: int, 
                   nav_df: Optional[pd.DataFrame] = None) -> List[str]:
    """
    Consolidated validation function for all user inputs.
    
    Args:
        selected_fund_code: Selected fund's scheme code
        from_date: Start date for analysis
        to_date: End date for analysis
        years: Rolling period in years
        nav_df: NAV dataframe (optional, for date boundary validation)
    
    Returns:
        List of error messages (empty if all validations pass)
    """
    errors = []
    
    # 1. Fund selection validation
    if not selected_fund_code:
        errors.append("Please search and select a fund.")
    
    # 2. Date selection validation
    if from_date is None or to_date is None:
        errors.append("Please select both From and To dates.")
        return errors  # Can't proceed with further date validations
    
    # 3. Date order validation
    if from_date >= to_date:
        errors.append("From date must be before To date.")
    
    # 4. Date range vs rolling period, using the real calendar (not just year and month).
    period_end = from_date + relativedelta(years=years)
    if to_date < period_end:
        errors.append(
            f"Selected date range is less than the selected rolling period "
            f"({years} year{'s' if years > 1 else ''}). "
            f"Please extend the time period."
        )
    else:
        # Start dates can only run from From Date until about To Date minus the
        # rolling period. If even a NAV on every calendar day could not produce
        # enough periods, say so here instead of failing later with a vague message.
        window_days = (to_date - period_end).days
        if window_days + 1 < MIN_VALID_PERIODS:
            errors.append(
                f"This date range is too short to produce at least {MIN_VALID_PERIODS} "
                f"rolling periods. A {years}-year window needs extra room beyond the "
                f"rolling period itself so many start dates can be tested. "
                f"Please extend the date range."
            )
    
    # 5. NAV availability validation (if NAV data provided)
    if nav_df is not None and not nav_df.empty:
        first_nav_date = nav_df['date'].min().date()
        last_nav_date = nav_df['date'].max().date()
        
        if from_date < first_nav_date:
            errors.append(
                f"From date is outside available NAV data. Please select a date on or after {format_date(first_nav_date)}."
            )
        
        if to_date > last_nav_date:
            errors.append(
                f"To date is outside available NAV data. Please select a date on or before {format_date(last_nav_date)}."
            )
    
    return errors


def plot_rolling_xirr(df: pd.DataFrame, scheme_name: str, years: int,
                      mode: str = "sip") -> plt.Figure:
    """
    Create a chart showing rolling XIRR or lump-sum CAGR over time.
    
    Args:
        df: DataFrame with 'Start Date' and 'XIRR %' or 'CAGR %'
        scheme_name: Name of the mutual fund scheme
        years: Rolling period in years
        mode: "sip" or "lumpsum"
    
    Returns:
        Matplotlib Figure object
    """
    is_lump = mode == "lumpsum"
    y_col = "CAGR %" if is_lump else "XIRR %"
    series_label = "CAGR %" if is_lump else "XIRR %"
    title = (f'{scheme_name}  |  {years}-Year Rolling CAGR'
             if is_lump else f'{scheme_name}  |  {years}-Year Rolling SIP XIRR')
    xlabel = "Start Date" if is_lump else "SIP Start Date"
    ylabel = "CAGR (%)" if is_lump else "XIRR (%)"

    fig, ax = plt.subplots(figsize=(8, 2.5))
    x = pd.to_datetime(df['Start Date'])
    y = df[y_col]

    ax.fill_between(x, y, alpha=0.15, color='steelblue')
    ax.plot(x, y, color='steelblue', linewidth=1.2, label=series_label)

    mean_val = y.mean()
    ax.axhline(mean_val, color='darkorange', linewidth=1.4,
               linestyle='--', label=f'Mean: {mean_val:.2f}%')
    ax.axhline(0, color='red', linewidth=0.8, linestyle=':')

    # Reduced font sizes to match body text
    ax.set_title(title, fontsize=11, fontweight='normal', pad=10)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.tick_params(axis='both', which='major', labelsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=30, ha='right')
    ax.legend(fontsize=9)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    return fig


def build_excel(df_export: pd.DataFrame, scheme_name: str, years: int, 
                from_date: date, to_date: date, sip_enabled: bool, 
                sip_amount: int, mode: str = "sip") -> BytesIO:
    """
    Build an Excel file with formatted rolling returns data.
    
    Args:
        df_export: DataFrame with rolling returns data
        scheme_name: Name of the mutual fund scheme
        years: Rolling period in years
        from_date: Start date of analysis range
        to_date: End date of analysis range
        sip_enabled: Whether an invested amount is included (SIP export)
        sip_amount: Monthly SIP amount, or the lump-sum amount
        mode: "sip" or "lumpsum"
    
    Returns:
        BytesIO buffer containing the Excel file
    """
    buf = BytesIO()
    is_lump = mode == "lumpsum"
    sheet_name = "Rolling CAGR" if is_lump else "Rolling XIRR"
    title = (f"{years}-Year Rolling Return" if is_lump
             else f"{years}-Year SIP Rolling Return")
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        gen_date = datetime.now().strftime('%d/%m/%Y %H:%M')
        from_str = from_date.strftime('%d/%m/%Y')
        to_str   = to_date.strftime('%d/%m/%Y')

        df_export.to_excel(writer, index=False,
                           sheet_name=sheet_name, startrow=18)
        wb = writer.book
        ws = writer.sheets[sheet_name]

        def mf(opts): return wb.add_format(opts)

        HDR_COLS = max(len(df_export.columns), 8)
        NC = HDR_COLS - 1

        ws.set_column(0, 0, 20)
        ws.set_column(1, 1, 20)
        ws.set_column(2, 2, 20)
        ws.set_column(3, 3, 14)
        ws.set_column(4, 4, 12)
        if is_lump:
            ws.set_column(5, 5, 18)
        elif sip_enabled:
            ws.set_column(5, 5, 22)
            ws.set_column(6, 6, 22)
        else:
            ws.set_column(5, 8, 14)

        fmt_h1      = mf({'bold':True,'font_size':14,'font_color':'#FFFFFF','bg_color':'#0D47A1','valign':'vcenter','text_wrap':True,'border':0})
        fmt_lbl     = mf({'bold':True,'font_size':10,'font_color':'#0D47A1','bg_color':'#E3F2FD','valign':'vcenter','border':0})
        fmt_meta    = mf({'bold':True,'font_size':10,'font_color':'#1B5E20','bg_color':'#E8F5E9','valign':'vcenter','text_wrap':True,'border':0})
        fmt_creator = mf({'bold':True,'font_size':10,'font_color':'#1B5E20','bg_color':'#E8F5E9','valign':'vcenter','border':0})
        fmt_thanks  = mf({'font_size':10,'font_color':'#880E4F','bg_color':'#FCE4EC','valign':'vcenter','text_wrap':True,'border':0})
        fmt_url     = mf({'bold':True,'font_size':10,'font_color':'#880E4F','underline':1,'bg_color':'#FCE4EC','valign':'vcenter','border':0})
        fmt_disc1   = mf({'font_size':10,'font_color':'#333333','bg_color':'#FFF8E1','valign':'vcenter','text_wrap':True,'border':0})
        fmt_disc2   = mf({'bold':True,'font_size':10,'font_color':'#B71C1C','bg_color':'#FFCDD2','valign':'vcenter','text_wrap':True,'border':0})
        fmt_disc3   = mf({'font_size':10,'font_color':'#880E4F','bg_color':'#FCE4EC','valign':'vcenter','text_wrap':True,'border':0})
        fmt_perf    = mf({'italic':True,'font_size':9,'font_color':'#6A0DAD','bg_color':'#F3E5F5','valign':'vcenter','border':0})
        fmt_sep     = mf({'bg_color':'#90A4AE','border':0})
        fmt_blank   = mf({'bg_color':'#E3F2FD','border':0})

        ws.merge_range(0, 0, 0, NC, title, fmt_h1)
        ws.set_row(0, 26)
        ws.write(1, 0, 'Fund Name:', fmt_lbl)
        ws.merge_range(1, 1, 1, NC, scheme_name, fmt_meta)
        ws.set_row(1, 20)
        ws.write(2, 0, 'Rolling Years:', fmt_lbl)
        ws.write(2, 1, f'{years} Year(s)', fmt_meta)
        ws.write(2, 2, 'From Date:', fmt_lbl)
        ws.write(2, 3, from_str, fmt_meta)
        ws.write(2, 4, 'To Date:', fmt_lbl)
        ws.write(2, 5, to_str, fmt_meta)
        for c in range(6, NC+1): ws.write(2, c, '', fmt_blank)
        ws.set_row(2, 20)
        if is_lump:
            ws.write(3, 0, 'Lump Sum Amount:', fmt_lbl)
            ws.write(3, 1, f'₹{format_indian_int(sip_amount)}', fmt_meta)
            ws.write(3, 2, 'Invested:', fmt_lbl)
            ws.write(3, 3, f'₹{format_indian_int(sip_amount)}', fmt_meta)
            for c in range(4, NC+1): ws.write(3, c, '', fmt_blank)
        elif sip_enabled:
            ws.write(3, 0, 'SIP Amount:', fmt_lbl)
            ws.write(3, 1, f'₹{format_indian_int(sip_amount)}/month', fmt_meta)
            ws.write(3, 2, 'Total Invested:', fmt_lbl)
            ws.write(3, 3, f'₹{format_indian_int(sip_amount * years * 12)}', fmt_meta)
            for c in range(4, NC+1): ws.write(3, c, '', fmt_blank)
        else:
            for c in range(0, NC+1): ws.write(3, c, '', fmt_blank)
        ws.set_row(3, 20)
        ws.write(4, 0, 'File Generated:', fmt_lbl)
        ws.write(4, 1, gen_date, fmt_meta)
        for c in range(2, NC+1): ws.write(4, c, '', fmt_blank)
        ws.set_row(4, 20)
        ws.write(5, 0, 'Created by:', fmt_lbl)
        ws.write(5, 1, CREATOR_NAME, fmt_creator)
        ws.write(5, 2, '', fmt_blank)
        ws.write(5, 3, 'Contact / Feedback:', fmt_lbl)
        ws.write(5, 4, CREATOR_EMAIL, fmt_meta)
        for c in range(5, NC+1): ws.write(5, c, '', fmt_meta)
        ws.set_row(5, 22)
        ws.set_column(1, 1, 24)
        ws.set_column(3, 3, 22)
        ws.set_column(4, 4, 28)
        ws.merge_range(6, 0, 6, NC, '', fmt_sep)
        ws.set_row(6, 4)
        ws.write_url(7, 0, DATA_SOURCE_URL, fmt_url, 'Special Thanks: mfapi.in')
        ws.merge_range(7, 1, 7, NC,
            'for providing real time mutual fund names and NAV data through their freely '
            'accessible API. Their support enables reliable and up-to-date information for this project.',
            fmt_thanks)
        ws.set_row(7, 55)
        ws.merge_range(8, 0, 8, NC, '', fmt_sep)
        ws.set_row(8, 4)
        ws.merge_range(9, 0, 9, NC,
            'Disclaimer: This dashboard is a personal project created with AI '
            '(Claude, Grok, and ChatGPT). The creator is not a software developer/tech person. '
            'This tool may contain inaccuracies, incomplete logic, or unintended errors. '
            'All outputs should be interpreted with caution and are not guaranteed to be '
            'accurate, complete, or suitable for investment decision-making. '
            f'For suggestions/feedback: {CREATOR_EMAIL}', fmt_disc1)
        ws.set_row(9, 70)
        ws.merge_range(10, 0, 10, NC,
            '⚠ Disclaimer: This tool is built solely for educational/exploratory purposes. '
            'Results may contain unintended errors. This is NOT financial advice. '
            'Mutual fund investments are subject to market risks, and past performance '
            'does not guarantee future returns. '
            'The creator is NOT a SEBI-registered investment advisor. '
            'Please consult a qualified financial advisor before investing.', fmt_disc2)
        ws.set_row(10, 65)
        ws.merge_range(11, 0, 11, NC,
            '⚠ Disclaimer: This tool relies on third-party data sources, which may be '
            'delayed, inaccurate, or incomplete. The creator is NOT responsible for any '
            'financial losses, decisions, or outcomes resulting from the use of this dashboard. '
            'This project is not affiliated with, endorsed by, or connected to any '
            'Asset Management Company (AMC), regulator, or official financial authority.', fmt_disc3)
        ws.set_row(11, 60)
        ws.merge_range(12, 0, 12, NC, '', fmt_sep)
        ws.set_row(12, 4)
        ws.merge_range(13, 0, 13, NC,
            '⚠ Past performance does not guarantee future returns.', fmt_perf)
        ws.set_row(13, 18)
        ws.merge_range(14, 0, 14, NC, '', fmt_sep)
        ws.set_row(14, 4)
        ws.merge_range(15, 0, 15, NC, '', fmt_blank)
        ws.set_row(15, 6)
        ws.set_row(16, 16)

    buf.seek(0)
    return buf
