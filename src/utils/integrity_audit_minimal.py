# SOURCE_OF_TRUTH: SECTION_ALL -- IMMUTABLE
"""Minimal integrity audit: verify frozen params match strategy file."""

import hashlib
import logging
import os

logger = logging.getLogger(__name__)

STRATEGY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "STRATEGY_LOCKED_V1.4_CE_PE.md"
)


def compute_strategy_hash() -> str:
    """Compute SHA-256 hash of the locked strategy file."""
    if not os.path.exists(STRATEGY_FILE):
        logger.error("INTEGRITY: Strategy file not found at %s", STRATEGY_FILE)
        return "MISSING"
    with open(STRATEGY_FILE, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def audit_params() -> dict:
    """Run minimal integrity audit. Returns audit result dict."""
    from config.frozen_params import (
        INDICES, CAPITAL_PCT, MAX_TOTAL_EXPOSURE_PCT,
        PREMIUM_RATIO_MIN, PREMIUM_RATIO_MAX,
    )

    issues = []

    # Check indices
    expected_indices = {"BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTY"}
    if set(INDICES) != expected_indices:
        issues.append(f"INDICES mismatch: got {INDICES}, expected {expected_indices}")

    # Check total capital allocations do not exceed max exposure
    total_capital = sum(CAPITAL_PCT.values())
    if total_capital > MAX_TOTAL_EXPOSURE_PCT + 0.01:
        issues.append(f"Capital sum {total_capital:.2f}% exceeds {MAX_TOTAL_EXPOSURE_PCT}%")

    # Check premium ratio bounds
    if PREMIUM_RATIO_MIN != 0.9 or PREMIUM_RATIO_MAX != 1.1:
        issues.append(f"Premium ratio bounds wrong: [{PREMIUM_RATIO_MIN}, {PREMIUM_RATIO_MAX}]")

    strategy_hash = compute_strategy_hash()

    result = {
        "strategy_hash": strategy_hash,
        "issues": issues,
        "passed": len(issues) == 0,
    }

    if issues:
        for issue in issues:
            logger.error("INTEGRITY AUDIT FAIL: %s", issue)
    else:
        logger.info("INTEGRITY AUDIT PASSED — strategy_hash=%s", strategy_hash[:16])

    return result
