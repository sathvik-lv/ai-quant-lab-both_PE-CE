# SOURCE_OF_TRUTH: SECTION_11 -- IMMUTABLE
"""Simple in-memory cache for option chain data with staleness tracking."""

import time
import logging

logger = logging.getLogger(__name__)

_cache: dict[str, dict] = {}


def put(index: str, chain: dict) -> None:
    """Store chain data with fetch timestamp."""
    _cache[index] = {
        "chain": chain,
        "ts": time.time(),
    }


def get(index: str) -> dict | None:
    """Retrieve cached chain data. Returns None if not cached."""
    entry = _cache.get(index)
    if entry is None:
        return None
    return entry["chain"]


def get_age_seconds(index: str) -> float:
    """Return age of cached data in seconds. Returns inf if not cached."""
    entry = _cache.get(index)
    if entry is None:
        return float("inf")
    return time.time() - entry["ts"]


def clear() -> None:
    """Clear all cached data."""
    _cache.clear()
