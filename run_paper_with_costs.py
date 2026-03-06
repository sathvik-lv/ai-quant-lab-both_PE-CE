# SOURCE_OF_TRUTH: SECTION_ALL -- IMMUTABLE
"""
Paper trading with simulated costs/slippage.
Runs indefinitely until Ctrl+C or kill.switch.
Permanent banner: PAPER MODE — SIMULATED COSTS/SLIPPAGE APPLIED — NOT REAL MONEY
"""

import os
import sys
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from config.frozen_params import INDICES
from config.live_params import KILL_SWITCH_FILE
from src.live.safety_wrapper import is_paper_allowed, apply_realistic_costs
from src.live.live_data_fetcher import fetch_live_chain, fetch_live_spot, resolve_live_symbols
from src.data.data_quality_gate import gate
from src.strategy.side_selector import select_sides
from src.strategy.filters import premium_ratio_gate
from src.strategy.risk_manager_minimal import check_total_exposure, check_concurrent_limit
from src.monitoring.summary_reporter import print_summary

WARNING_BANNER = (
    "PAPER MODE -- SIMULATED COSTS/SLIPPAGE APPLIED -- NOT REAL MONEY"
)

PAPER_LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "paper_with_costs.log")
DECISION_LOG_FILE = os.path.join(os.path.dirname(__file__), "decision_log.md")
POLL_INTERVAL = 180  # 3 minutes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PAPER_LOG_FILE),
    ],
)
logger = logging.getLogger("paper_costs")


def log_decision(bar_id: str, side: str, decision: str, reason: str) -> None:
    ts = datetime.now().isoformat()
    with open(DECISION_LOG_FILE, "a") as f:
        f.write(f"{ts} | {bar_id} | side={side} | decision={decision} | reason={reason}\n")


def make_bar_id(index: str, candle_time: datetime, timeframe: str = "5m") -> str:
    return f"{index}_{candle_time.strftime('%Y%m%d_%H%M')}_{timeframe}"


def extract_premium(chain: dict, strike: float, expiry: str, side: str) -> float:
    try:
        for row in chain["records"]["data"]:
            if row["strikePrice"] == strike and row.get("expiryDate") == expiry:
                return float(row.get(side, {}).get("lastPrice", 0))
    except (KeyError, TypeError, ValueError):
        pass
    return 0.0


def main():
    logger.info("=" * 60)
    logger.info("%s", WARNING_BANNER)
    logger.info("=" * 60)

    if not is_paper_allowed():
        print("PAPER TRADING NOT ALLOWED — safety checks failed. Aborting.")
        sys.exit(1)

    print(WARNING_BANNER)
    logger.info("Paper trading with simulated costs starting...")

    active_trades: list[dict] = []
    valid_count = 0

    while True:
        try:
            # Kill switch check
            kill_path = os.path.join(os.path.dirname(__file__), KILL_SWITCH_FILE)
            if os.path.exists(kill_path):
                logger.critical("KILL SWITCH DETECTED — HALTING IMMEDIATELY")
                print("KILL SWITCH ACTIVE — HALTING")
                break

            now = datetime.now()
            candle_time = now.replace(second=0, microsecond=0)

            logger.info("%s", WARNING_BANNER)

            for index in INDICES:
                bar_id = make_bar_id(index, candle_time)

                chain = fetch_live_chain(index)
                if not chain:
                    continue

                if not gate(chain, index):
                    log_decision(bar_id, "N/A", "REJECT", f"data_quality_fail_{index}")
                    continue

                spot = fetch_live_spot(index)
                if not spot:
                    continue

                sides = select_sides(chain, spot, index)
                for side in sides:
                    symbols = resolve_live_symbols(index, spot, chain, side)
                    if not symbols:
                        continue

                    w_premium = extract_premium(chain, symbols["strike"], symbols["weekly_expiry"], side)
                    m_premium = extract_premium(chain, symbols["strike"], symbols["monthly_expiry"], side)

                    passes, ratio = premium_ratio_gate(w_premium, m_premium, index, side)
                    if not passes:
                        log_decision(bar_id, side, "REJECT",
                                     f"premium_ratio_{ratio:.2f}_outside_0.9-1.1")
                        continue

                    if not check_total_exposure(active_trades, index, side):
                        log_decision(bar_id, side, "REJECT", "total_exposure_exceeded")
                        continue

                    if not check_concurrent_limit(active_trades, index, side):
                        log_decision(bar_id, side, "REJECT", f"concurrent_limit_{index}_{side}")
                        continue

                    # Apply simulated costs
                    adjusted_w = apply_realistic_costs(w_premium, side, 1)
                    adjusted_m = apply_realistic_costs(m_premium, side, 1)

                    valid_count += 1
                    active_trades.append({
                        "index": index, "side": side,
                        "entry_time": now.isoformat(), "bar_id": bar_id,
                    })

                    log_decision(bar_id, side, "ACCEPT", "passed_all_gates_with_costs")
                    logger.info("%s", WARNING_BANNER)
                    logger.info(
                        "PAPER TRADE #%d: %s %s | %s / %s | ratio=%.4f | "
                        "raw_W=%.2f adj_W=%.2f | raw_M=%.2f adj_M=%.2f",
                        valid_count, index, side,
                        symbols["weekly_symbol"], symbols["monthly_symbol"],
                        ratio, w_premium, adjusted_w, m_premium, adjusted_m
                    )

                    if valid_count % 5 == 0:
                        print_summary()

            logger.info("Sleeping %ds... (valid=%d)", POLL_INTERVAL, valid_count)
            logger.info("%s", WARNING_BANNER)
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Paper trading interrupted by user")
            break

    logger.info("=" * 60)
    logger.info("PAPER WITH COSTS COMPLETE — %d trades logged", valid_count)
    logger.info("%s", WARNING_BANNER)
    logger.info("=" * 60)
    print_summary()


if __name__ == "__main__":
    main()
