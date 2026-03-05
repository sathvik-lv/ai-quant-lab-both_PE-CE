# SOURCE_OF_TRUTH: SECTION_3 -- IMMUTABLE
"""
Premium ratio filter (Section 3 only).
TRADE_ALLOWED_ONLY_IF: 0.9 <= (W / M) <= 1.1
Checked independently for CE and PE.
"""

import logging

from config.frozen_params import PREMIUM_RATIO_MIN, PREMIUM_RATIO_MAX

logger = logging.getLogger(__name__)


def premium_ratio_gate(weekly_premium: float, monthly_premium: float,
                       index: str, side: str) -> tuple[bool, float]:
    """
    Check premium ratio gate for a specific side.

    Returns (passes: bool, ratio: float).
    If monthly_premium <= 0 or data invalid, returns (False, 0.0).
    """
    if monthly_premium <= 0:
        logger.warning("PREMIUM_RATIO %s %s: monthly_premium=%.2f invalid — NO_TRADE",
                        index, side, monthly_premium)
        return False, 0.0

    if weekly_premium < 0:
        logger.warning("PREMIUM_RATIO %s %s: weekly_premium=%.2f invalid — NO_TRADE",
                        index, side, weekly_premium)
        return False, 0.0

    ratio = weekly_premium / monthly_premium

    passes = PREMIUM_RATIO_MIN <= ratio <= PREMIUM_RATIO_MAX

    if passes:
        logger.info("PREMIUM_RATIO %s %s: ratio=%.4f PASS (W=%.2f, M=%.2f)",
                     index, side, ratio, weekly_premium, monthly_premium)
    else:
        logger.info("PREMIUM_RATIO %s %s: ratio=%.4f REJECT (W=%.2f, M=%.2f, bounds=[%.2f, %.2f])",
                     index, side, ratio, weekly_premium, monthly_premium,
                     PREMIUM_RATIO_MIN, PREMIUM_RATIO_MAX)

    return passes, ratio
