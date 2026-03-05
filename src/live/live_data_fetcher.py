# SOURCE_OF_TRUTH: LIVE_DATA -- IMMUTABLE
"""Live data fetcher wrapper with strict freshness gate (<60s for live)."""

import time
import logging

from src.data.fetcher import fetch_option_chain, fetch_spot_price
from src.data.symbol_mapper import resolve_symbols
from src.data import cache

logger = logging.getLogger(__name__)

LIVE_FRESHNESS_LIMIT = 60  # seconds


def fetch_live_chain(index: str) -> dict:
    """Fetch option chain with live freshness validation (<60s)."""
    chain = fetch_option_chain(index)
    if not chain:
        logger.error("LIVE_DATA: No chain data for %s", index)
        return {}

    cache.put(index, chain)

    age = time.time() - chain.get("_fetch_ts", 0)
    if age > LIVE_FRESHNESS_LIMIT:
        logger.error("LIVE_DATA: Chain for %s is %.1fs old (limit=%ds) — STALE",
                      index, age, LIVE_FRESHNESS_LIMIT)
        return {}

    logger.info("LIVE_DATA: Chain for %s fresh (%.1fs old)", index, age)
    return chain


def fetch_live_spot(index: str) -> float | None:
    """Fetch spot price for live trading."""
    spot = fetch_spot_price(index)
    if spot is None:
        logger.error("LIVE_DATA: No spot price for %s", index)
    return spot


def resolve_live_symbols(index: str, spot: float, chain: dict, side: str) -> dict | None:
    """Resolve symbols with live data validation."""
    from datetime import datetime
    symbols = resolve_symbols(index, spot, chain, side, datetime.now())
    if symbols:
        logger.info("LIVE_DATA: Resolved %s %s: %s / %s",
                     index, side, symbols["weekly_symbol"], symbols["monthly_symbol"])
    return symbols
