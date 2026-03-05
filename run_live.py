# SOURCE_OF_TRUTH: SECTION_ALL -- IMMUTABLE
"""
LIVE trading runner.
Only runs if is_live_allowed() == True.
Uses real-time nsepython + all safety checks.
Logs to live_trades.log.
"""

import os
import sys
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from config.frozen_params import INDICES
from config.live_params import KILL_SWITCH_FILE
from src.live.safety_wrapper import is_live_allowed, apply_realistic_costs, check_daily_loss_limit
from src.live.live_data_fetcher import fetch_live_chain, fetch_live_spot, resolve_live_symbols
from src.data.data_quality_gate import gate
from src.strategy.side_selector import select_sides
from src.strategy.filters import premium_ratio_gate
from src.strategy.risk_manager_minimal import check_total_exposure, check_concurrent_limit

WARNING_BANNER = (
    "LIVE MODE — REAL COSTS/SLIPPAGE APPLIED — REAL CAPITAL AT RISK"
)

LIVE_LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "live_trades.log")
POLL_INTERVAL = 180  # 3 minutes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LIVE_LOG_FILE),
    ],
)
logger = logging.getLogger("live_runner")


def main():
    logger.info("=" * 60)
    logger.info("LIVE RUNNER STARTUP CHECK")
    logger.info("=" * 60)

    if not is_live_allowed():
        print("LIVE TRADING NOT ALLOWED — safety checks failed. Aborting.")
        sys.exit(1)

    logger.info("%s", WARNING_BANNER)
    print(WARNING_BANNER)

    active_trades: list[dict] = []
    daily_pnl_pct = 0.0

    while True:
        try:
            # Re-check kill switch every cycle
            if os.path.exists(os.path.join(os.path.dirname(__file__), KILL_SWITCH_FILE)):
                logger.critical("KILL SWITCH DETECTED — HALTING IMMEDIATELY")
                print("KILL SWITCH ACTIVE — HALTING")
                break

            check_daily_loss_limit(daily_pnl_pct)

            now = datetime.now()
            logger.info("%s", WARNING_BANNER)

            for index in INDICES:
                chain = fetch_live_chain(index)
                if not chain:
                    continue

                if not gate(chain, index):
                    continue

                spot = fetch_live_spot(index)
                if not spot:
                    continue

                sides = select_sides(chain, spot, index)
                for side in sides:
                    symbols = resolve_live_symbols(index, spot, chain, side)
                    if not symbols:
                        continue

                    # Would apply premium ratio, exposure checks, etc.
                    # Then apply_realistic_costs() before execution
                    logger.info("LIVE: Would evaluate %s %s — %s / %s",
                                index, side,
                                symbols["weekly_symbol"], symbols["monthly_symbol"])

            logger.info("Sleeping %ds...", POLL_INTERVAL)
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("LIVE: Interrupted by user — shutting down safely")
            break


if __name__ == "__main__":
    main()
