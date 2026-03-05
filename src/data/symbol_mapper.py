# SOURCE_OF_TRUTH: SECTION_2.1, SECTION_5 -- IMMUTABLE
"""Resolve weekly and monthly option symbols for CE and PE. Fail-closed with assertions."""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# NSE symbol roots
SYMBOL_ROOTS = {
    "BANKNIFTY": "BANKNIFTY",
    "FINNIFTY": "FINNIFTY",
    "MIDCPNIFTY": "MIDCPNIFTY",
    "NIFTY": "NIFTY",
}


def _find_nearest_expiry(expiries: list[str], target_date: datetime, weekly: bool) -> str | None:
    """Find nearest weekly or monthly expiry from a sorted list of expiry date strings."""
    parsed = []
    for exp_str in expiries:
        try:
            exp_dt = datetime.strptime(exp_str, "%d-%b-%Y")
            parsed.append((exp_dt, exp_str))
        except ValueError:
            continue

    parsed.sort(key=lambda x: x[0])

    for exp_dt, exp_str in parsed:
        if exp_dt < target_date:
            continue
        days_away = (exp_dt - target_date).days
        if weekly and days_away <= 7:
            return exp_str
        if not weekly and days_away > 7:
            return exp_str

    return None


def resolve_symbols(index: str, spot: float, chain: dict, side: str, now: datetime | None = None) -> dict | None:
    """
    Resolve ATM weekly and monthly symbols for a given side (CE or PE).

    Returns dict with keys: weekly_symbol, monthly_symbol, strike, weekly_expiry, monthly_expiry
    or None on failure (fail-closed).
    """
    now = now or datetime.now()

    assert index in SYMBOL_ROOTS, f"Unknown index: {index}"
    assert side in ("CE", "PE"), f"Invalid side: {side}"
    assert spot > 0, f"Invalid spot price: {spot}"
    assert chain and "records" in chain, "Invalid or empty chain"

    root = SYMBOL_ROOTS[index]

    # Determine ATM strike (nearest to spot from available strikes)
    try:
        all_data = chain["records"]["data"]
        strikes = sorted(set(row["strikePrice"] for row in all_data))
    except (KeyError, TypeError) as e:
        logger.error("Cannot extract strikes from chain for %s: %s", index, e)
        return None

    assert len(strikes) > 0, f"No strikes found for {index}"

    atm_strike = min(strikes, key=lambda s: abs(s - spot))

    # Get available expiries
    try:
        expiries = sorted(set(chain["records"]["expiryDates"]))
    except (KeyError, TypeError):
        logger.error("Cannot extract expiries from chain for %s", index)
        return None

    assert len(expiries) >= 2, f"Need at least 2 expiries for calendar, got {len(expiries)} for {index}"

    weekly_expiry = _find_nearest_expiry(expiries, now, weekly=True)
    monthly_expiry = _find_nearest_expiry(expiries, now, weekly=False)

    if not weekly_expiry or not monthly_expiry:
        logger.error("Could not resolve expiries for %s: weekly=%s monthly=%s", index, weekly_expiry, monthly_expiry)
        return None

    assert weekly_expiry != monthly_expiry, (
        f"Weekly and monthly expiry must differ for {index}: both={weekly_expiry}"
    )

    strike_int = int(atm_strike)
    weekly_symbol = f"{root}{weekly_expiry.replace('-', '').upper()}{strike_int}{side}"
    monthly_symbol = f"{root}{monthly_expiry.replace('-', '').upper()}{strike_int}{side}"

    result = {
        "weekly_symbol": weekly_symbol,
        "monthly_symbol": monthly_symbol,
        "strike": atm_strike,
        "weekly_expiry": weekly_expiry,
        "monthly_expiry": monthly_expiry,
        "side": side,
        "index": index,
    }

    logger.info("Resolved %s %s: %s / %s @ strike=%s", index, side,
                weekly_symbol, monthly_symbol, atm_strike)
    return result
