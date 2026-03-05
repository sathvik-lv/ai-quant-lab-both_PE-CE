# SOURCE_OF_TRUTH: SECTION_11 -- IMMUTABLE
"""Fetch live option chain data from NSE via nsepython."""

import time
import logging

logger = logging.getLogger(__name__)


def fetch_option_chain(index: str) -> dict:
    """Fetch option chain for an index. Returns raw chain dict or empty on failure."""
    try:
        from nsepython import nse_optionchain_scrapper
        chain = nse_optionchain_scrapper(index)
        if not chain or "records" not in chain:
            logger.error("Empty or malformed chain for %s", index)
            return {}
        chain["_fetch_ts"] = time.time()
        return chain
    except Exception as e:
        logger.error("Failed to fetch chain for %s: %s", index, e)
        return {}


def fetch_spot_price(index: str) -> float | None:
    """Fetch current spot price for an index."""
    try:
        from nsepython import nse_quote_ltp
        symbol_map = {
            "BANKNIFTY": "NIFTY BANK",
            "FINNIFTY": "NIFTY FIN SERVICE",
            "MIDCPNIFTY": "NIFTY MID SELECT",
            "NIFTY": "NIFTY 50",
        }
        ltp = nse_quote_ltp(symbol_map.get(index, index), "latest", "latest")
        return float(ltp) if ltp else None
    except Exception as e:
        logger.error("Failed to fetch spot for %s: %s", index, e)
        return None
