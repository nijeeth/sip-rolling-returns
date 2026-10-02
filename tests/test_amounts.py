"""Amount box: Indian grouping, no decimals, and the SIP / lump-sum defaults."""

from app_utils import format_indian_int, parse_indian_amount, resolve_amount_state


def test_indian_grouping_has_no_decimals():
    assert format_indian_int(500) == "500"
    assert format_indian_int(1000) == "1,000"
    assert format_indian_int(10000) == "10,000"
    assert format_indian_int(100000) == "1,00,000"
    assert format_indian_int(1200000) == "12,00,000"
    assert format_indian_int(10000000) == "1,00,00,000"
    assert "." not in format_indian_int(10000000)


def test_parse_accepts_indian_or_western_commas_and_drops_paise():
    assert parse_indian_amount("10,000") == 10000
    assert parse_indian_amount("1,00,000") == 100000
    assert parse_indian_amount("1,00,00,000") == 10000000
    assert parse_indian_amount("100,000") == 100000
    assert parse_indian_amount("₹ 1,00,000") == 100000
    assert parse_indian_amount("1,00,000.50") == 100000
    assert parse_indian_amount("10.5") == 10
    assert parse_indian_amount("") is None
    assert parse_indian_amount("abc") is None
    assert parse_indian_amount(None) is None


def _fresh(**overrides):
    state = dict(
        amount_mode=None,
        saved_sip_amount=None,
        saved_lump_amount=None,
        sip_amount=None,
        sip_amount_text=None,
    )
    state.update(overrides)
    return state


def _with(state, **overrides):
    merged = dict(state)
    merged.update(overrides)
    return _fresh(**merged)


def test_fresh_sip_defaults_to_10000_not_1000():
    shown = resolve_amount_state(False, **_fresh())
    assert shown["sip_amount"] == 10_000
    assert shown["sip_amount_text"] == "10,000"
    assert shown["amount_mode"] == "sip"


def test_first_lump_sum_defaults_to_100000_not_10000():
    sip = resolve_amount_state(False, **_fresh())
    lump = resolve_amount_state(True, **_fresh(**sip))
    assert lump["sip_amount"] == 100_000
    assert lump["sip_amount_text"] == "1,00,000"
    assert lump["saved_sip_amount"] == 10_000


def test_switching_back_restores_each_mode():
    sip = resolve_amount_state(False, **_fresh())
    edited = resolve_amount_state(False, **_with(sip, sip_amount_text="15,000"))
    assert edited["sip_amount"] == 15_000
    assert edited["sip_amount_text"] == "15,000"
    lump = resolve_amount_state(True, **_fresh(**edited))
    assert lump["sip_amount_text"] == "1,00,000"
    back = resolve_amount_state(False, **_fresh(**lump))
    assert back["sip_amount"] == 15_000
    assert back["sip_amount_text"] == "15,000"
    again = resolve_amount_state(True, **_fresh(**back))
    assert again["sip_amount"] == 100_000


def test_typed_amount_rounds_to_500_and_stays_inside_limits():
    sip = resolve_amount_state(False, **_fresh())
    rounded = resolve_amount_state(False, **_with(sip, sip_amount_text="1,250"))
    assert rounded["sip_amount"] == 1_500
    assert rounded["sip_amount_text"] == "1,500"
    low = resolve_amount_state(False, **_with(sip, sip_amount_text="100"))
    assert low["sip_amount"] == 500
    high = resolve_amount_state(False, **_with(sip, sip_amount_text="1,00,00,000"))
    assert high["sip_amount"] == 100_000
    assert high["sip_amount_text"] == "1,00,000"
    junk = resolve_amount_state(False, **_with(sip, sip_amount_text="nope"))
    assert junk["sip_amount"] == 10_000
    assert junk["sip_amount_text"] == "10,000"
