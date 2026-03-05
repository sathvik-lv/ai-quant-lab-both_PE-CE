# SOURCE_OF_TRUTH: SECTION_2.1 -- IMMUTABLE
"""
Side selector: independently determines whether CE, PE, or both sides qualify.
Section 2.1: For every qualifying opportunity, CE and PE are evaluated independently.
No directional bias (Section 2: DIRECTIONAL_BIAS: NONE).
"""

import logging

logger = logging.getLogger(__name__)


def select_sides(chain: dict, spot: float, index: str) -> list[str]:
    """
    Determine which sides (CE, PE) qualify for the current bar.

    Both CE and PE are always evaluated independently.
    Returns list of qualifying sides: ["CE"], ["PE"], ["CE", "PE"], or [].
    """
    qualifying = []

    for side in ("CE", "PE"):
        if _side_qualifies(chain, spot, index, side):
            qualifying.append(side)

    if qualifying:
        logger.info("SIDE_SELECTOR %s: qualifying sides = %s", index, qualifying)
    else:
        logger.debug("SIDE_SELECTOR %s: no sides qualify", index)

    return qualifying


def _side_qualifies(chain: dict, spot: float, index: str, side: str) -> bool:
    """Check if a specific side qualifies based on chain data availability."""
    try:
        records = chain.get("records", {})
        data = records.get("data", [])

        # Verify ATM data exists for this side
        strikes = sorted(set(row["strikePrice"] for row in data))
        if not strikes:
            return False

        atm_strike = min(strikes, key=lambda s: abs(s - spot))

        # Check that both weekly and monthly data exist for this side at ATM
        expiries = sorted(set(records.get("expiryDates", [])))
        if len(expiries) < 2:
            return False

        side_key = side
        atm_rows = [row for row in data if row["strikePrice"] == atm_strike]

        has_data = False
        for row in atm_rows:
            if side_key in row and row[side_key].get("openInterest", 0) > 0:
                has_data = True
                break

        if not has_data:
            logger.debug("SIDE_SELECTOR %s %s: no OI data at ATM strike %s", index, side, atm_strike)
            return False

        return True

    except Exception as e:
        logger.error("SIDE_SELECTOR %s %s error: %s", index, side, e)
        return False
