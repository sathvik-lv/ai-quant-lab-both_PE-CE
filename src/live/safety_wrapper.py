# SOURCE_OF_TRUTH: LIVE_SAFETY -- IMMUTABLE
"""Safety wrappers for live/paper trading. Never modifies strategy logic."""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# IST timezone offset
IST = timezone(timedelta(hours=5, minutes=30))


def is_live_allowed() -> bool:
    """
    Check all safety conditions before allowing live trading.
    Returns True only if ALL conditions pass.
    """
    from config.live_params import LIVE_MODE, KILL_SWITCH_FILE
    from src.utils.strategy_integrity import verify_strategy_hash

    # Check LIVE_MODE
    if not LIVE_MODE:
        logger.warning("SAFETY: LIVE_MODE is False — live trading not allowed")
        print("LIVE MODE DISABLED — set LIVE_MODE=True in config/live_params.py after full review")
        return False

    # Integrity hash check
    if not verify_strategy_hash():
        logger.error("SAFETY: Strategy integrity check FAILED — live trading blocked")
        return False

    # Kill switch
    kill_path = os.path.join(PROJECT_ROOT, KILL_SWITCH_FILE)
    if os.path.exists(kill_path):
        logger.critical("SAFETY: kill.switch FILE DETECTED — IMMEDIATE HALT")
        print("KILL SWITCH ACTIVE — delete kill.switch to resume")
        return False

    # Clock timezone check (must be in IST)
    now = datetime.now(IST)
    utc_now = datetime.now(timezone.utc)
    offset_hours = (now.utcoffset().total_seconds()) / 3600
    if abs(offset_hours - 5.5) > 0.1:
        logger.error("SAFETY: Clock not in IST timezone — offset=%.1fh", offset_hours)
        return False

    logger.info("SAFETY: All live checks passed — trading allowed")
    return True


def is_paper_allowed() -> bool:
    """
    Check safety conditions for paper trading (less strict than live).
    """
    from config.live_params import KILL_SWITCH_FILE
    from src.utils.strategy_integrity import verify_strategy_hash

    # Integrity hash check
    if not verify_strategy_hash():
        logger.error("SAFETY: Strategy integrity check FAILED — paper trading blocked")
        return False

    # Kill switch
    kill_path = os.path.join(PROJECT_ROOT, KILL_SWITCH_FILE)
    if os.path.exists(kill_path):
        logger.critical("SAFETY: kill.switch FILE DETECTED — IMMEDIATE HALT")
        print("KILL SWITCH ACTIVE — delete kill.switch to resume")
        return False

    logger.info("SAFETY: Paper trading checks passed")
    return True


def apply_realistic_costs(entry_premium: float, side: str, lots: int) -> float:
    """
    Apply simulated costs to a premium value.
    Returns adjusted premium after subtracting slippage + brokerage + STT.
    """
    from config.live_params import SLIPPAGE_BPS, BROKERAGE_PER_LOT, STT_PERCENT, SIMULATE_COSTS

    if not SIMULATE_COSTS:
        return entry_premium

    # Slippage (adverse fill)
    slippage = entry_premium * (SLIPPAGE_BPS / 10000)

    # Brokerage per lot
    brokerage = BROKERAGE_PER_LOT * lots

    # STT (applied on sell side for options)
    stt = entry_premium * (STT_PERCENT / 100)

    total_cost = slippage + stt
    cost_per_unit = total_cost
    adjusted = entry_premium - cost_per_unit

    logger.info("COSTS: premium=%.2f, slippage=%.2f, stt=%.2f, brokerage=%d, adjusted=%.2f",
                entry_premium, slippage, stt, brokerage, adjusted)

    return adjusted


def check_daily_loss_limit(current_pnl_pct: float) -> None:
    """
    Check if daily P&L has breached the max loss limit.
    If breached: log CRITICAL and exit immediately.
    """
    from config.live_params import MAX_DAILY_LOSS_PCT

    if current_pnl_pct < MAX_DAILY_LOSS_PCT:
        logger.critical(
            "DAILY LOSS LIMIT BREACHED: current=%.2f%% < limit=%.2f%% — EMERGENCY HALT",
            current_pnl_pct, MAX_DAILY_LOSS_PCT
        )
        print(f"EMERGENCY HALT: Daily loss {current_pnl_pct:.2f}% exceeds limit {MAX_DAILY_LOSS_PCT:.2f}%")
        sys.exit(1)
