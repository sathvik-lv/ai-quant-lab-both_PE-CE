# SOURCE_OF_TRUTH: SECTION_6, SECTION_9 -- IMMUTABLE
"""
Minimal risk manager: breakeven check, time-based exit, 60% total exposure gate.
"""

import logging
from datetime import datetime

from config.frozen_params import (
    CAPITAL_PCT,
    MAX_TOTAL_EXPOSURE_PCT,
    MAX_HOLD_DAYS,
    MAX_CONCURRENT,
)

logger = logging.getLogger(__name__)


def check_total_exposure(active_trades: list[dict], new_index: str, new_side: str) -> bool:
    """
    Check if adding a new trade would exceed 60% total capital exposure.
    Returns True if trade is allowed, False if it would exceed the limit.
    """
    current_exposure = sum(
        CAPITAL_PCT.get(f"{t['index']}_{t['side']}", 0.0)
        for t in active_trades
    )

    new_alloc_key = f"{new_index}_{new_side}"
    new_alloc = CAPITAL_PCT.get(new_alloc_key, 0.0)
    projected = current_exposure + new_alloc

    if projected > MAX_TOTAL_EXPOSURE_PCT:
        logger.warning(
            "RISK: Projected exposure %.2f%% > %.2f%% limit — REJECTING %s %s",
            projected, MAX_TOTAL_EXPOSURE_PCT, new_index, new_side
        )
        return False

    logger.info("RISK: Projected exposure %.2f%% (current=%.2f%% + new=%.2f%%) — OK",
                projected, current_exposure, new_alloc)
    return True


def check_concurrent_limit(active_trades: list[dict], new_index: str, new_side: str) -> bool:
    """Check if adding a trade exceeds max concurrent for this index+side."""
    key = f"{new_index}_{new_side}"
    max_allowed = MAX_CONCURRENT.get(key, 1)
    current_count = sum(
        1 for t in active_trades
        if t["index"] == new_index and t["side"] == new_side
    )
    if current_count >= max_allowed:
        logger.warning("RISK: %s already at max concurrent (%d) — REJECTING", key, max_allowed)
        return False
    return True


def check_time_exit(trade: dict, now: datetime | None = None) -> bool:
    """Return True if trade should be exited due to max holding time."""
    now = now or datetime.now()
    entry_time = trade.get("entry_time")
    if not entry_time:
        return False

    if isinstance(entry_time, str):
        entry_time = datetime.fromisoformat(entry_time)

    max_days = MAX_HOLD_DAYS.get(trade["index"], 5)
    held_days = (now - entry_time).days

    if held_days >= max_days:
        logger.info("RISK: Time exit triggered for %s %s — held %d days (max=%d)",
                     trade["index"], trade["side"], held_days, max_days)
        return True
    return False


def check_breakeven(trade: dict, current_spread_value: float) -> bool:
    """
    Basic breakeven check: exit if spread value has decayed to breakeven or worse.
    Returns True if should exit.
    """
    entry_value = trade.get("entry_spread_value", 0)
    if entry_value <= 0:
        return False

    if current_spread_value <= 0:
        logger.info("RISK: Breakeven exit — spread value %.2f <= 0 for %s %s",
                     current_spread_value, trade["index"], trade["side"])
        return True
    return False
