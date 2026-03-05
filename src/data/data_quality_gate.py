# SOURCE_OF_TRUTH: SECTION_11 -- IMMUTABLE
"""Data quality gate: reject stale or invalid data. >5 min stale = NO_TRADE."""

import time
import logging

from config.frozen_params import DATA_STALE_SECONDS

logger = logging.getLogger(__name__)


def check_freshness(chain: dict) -> bool:
    """Return True if data is fresh enough to trade. False = NO_TRADE."""
    fetch_ts = chain.get("_fetch_ts")
    if fetch_ts is None:
        logger.warning("DATA_QUALITY: No fetch timestamp in chain — NO_TRADE")
        return False

    age = time.time() - fetch_ts
    if age > DATA_STALE_SECONDS:
        logger.warning("DATA_QUALITY: Data is %.1f seconds old (limit=%d) — NO_TRADE",
                        age, DATA_STALE_SECONDS)
        return False

    return True


def check_chain_integrity(chain: dict, index: str) -> bool:
    """Basic sanity checks on chain data. Returns False = NO_TRADE."""
    if not chain:
        logger.warning("DATA_QUALITY: Empty chain for %s — NO_TRADE", index)
        return False

    records = chain.get("records")
    if not records:
        logger.warning("DATA_QUALITY: No records in chain for %s — NO_TRADE", index)
        return False

    data = records.get("data")
    if not data or len(data) < 5:
        logger.warning("DATA_QUALITY: Insufficient data rows (%s) for %s — NO_TRADE",
                        len(data) if data else 0, index)
        return False

    expiries = records.get("expiryDates")
    if not expiries or len(expiries) < 2:
        logger.warning("DATA_QUALITY: Insufficient expiries for %s — NO_TRADE", index)
        return False

    return True


def gate(chain: dict, index: str) -> bool:
    """Combined quality gate. Returns True only if all checks pass."""
    return check_chain_integrity(chain, index) and check_freshness(chain)
