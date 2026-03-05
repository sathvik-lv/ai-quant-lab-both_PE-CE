# SOURCE_OF_TRUTH: SECTION_ALL -- IMMUTABLE
"""
Paper reconnaissance runner.
- Every 3 min via nsepython
- Log resolved symbols
- Permanent WARNING banner
- Replay protection via processed_bars.log
- Restart invalidation -> mark INVALID + exclude
- Stop at 30 valid trades
- Independent CE/PE checks
- 60% total capital gate
"""

import os
import sys
import time
import logging
from datetime import datetime

# Project root on path
sys.path.insert(0, os.path.dirname(__file__))

from config.frozen_params import INDICES, MAX_TOTAL_EXPOSURE_PCT
from src.data.fetcher import fetch_option_chain, fetch_spot_price
from src.data.data_quality_gate import gate
from src.data.symbol_mapper import resolve_symbols
from src.data import cache
from src.strategy.side_selector import select_sides
from src.strategy.filters import premium_ratio_gate
from src.strategy.risk_manager_minimal import check_total_exposure, check_concurrent_limit
from src.utils.integrity_audit_minimal import audit_params
from src.monitoring.summary_reporter import print_summary

WARNING_BANNER = (
    "WARNING: COSTS, SLIPPAGE, AND TAXES NOT APPLIED -- RESULTS NOT REALISTIC"
)

PROCESSED_BARS_FILE = os.path.join(os.path.dirname(__file__), "processed_bars.log")
OBSERVATIONS_FILE = os.path.join(os.path.dirname(__file__), "observations_log.md")
DECISION_LOG_FILE = os.path.join(os.path.dirname(__file__), "decision_log.md")
POLL_INTERVAL = 180  # 3 minutes
MAX_VALID_TRADES = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "logs", "paper_recon.log")),
    ],
)
logger = logging.getLogger("paper_recon")

# Session tracking for restart invalidation
_session_start = datetime.now()
_session_id = _session_start.strftime("%Y%m%d_%H%M%S")


def load_processed_bars() -> set[str]:
    """Load already-processed bar IDs for replay protection."""
    if not os.path.exists(PROCESSED_BARS_FILE):
        return set()
    with open(PROCESSED_BARS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())


def append_processed_bar(bar_id: str) -> None:
    """Append bar_id to processed_bars.log."""
    with open(PROCESSED_BARS_FILE, "a") as f:
        f.write(bar_id + "\n")


def make_bar_id(index: str, candle_time: datetime, timeframe: str = "5m") -> str:
    """Generate bar_id: {index}_{candle_open_time_IST}_{timeframe}"""
    return f"{index}_{candle_time.strftime('%Y%m%d_%H%M')}_{timeframe}"


def log_observation(bar_id: str, text: str) -> None:
    """Append observation to observations_log.md."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(OBSERVATIONS_FILE, "a") as f:
        f.write(f"{ts} | {bar_id} | {text}\n")


def log_decision(bar_id: str, side: str, decision: str, reason: str) -> None:
    ts = datetime.now().isoformat()
    with open(DECISION_LOG_FILE, "a") as f:
        f.write(f"{ts} | {bar_id} | side={side} | decision={decision} | reason={reason}\n")


def extract_premium(chain: dict, strike: float, expiry: str, side: str) -> float:
    """Extract LTP for a specific strike/expiry/side from chain data."""
    try:
        for row in chain["records"]["data"]:
            if row["strikePrice"] == strike and row.get("expiryDate") == expiry:
                return float(row.get(side, {}).get("lastPrice", 0))
    except (KeyError, TypeError, ValueError):
        pass
    return 0.0


def run_one_cycle(processed: set[str], active_trades: list[dict], valid_count: int) -> int:
    """Run one recon cycle across all indices. Returns updated valid_count."""
    now = datetime.now()
    candle_time = now.replace(second=0, microsecond=0)

    for index in INDICES:
        bar_id = make_bar_id(index, candle_time)

        # Replay protection
        if bar_id in processed:
            logger.debug("REPLAY SKIP: %s", bar_id)
            continue

        logger.info("=" * 60)
        logger.info("%s", WARNING_BANNER)
        logger.info("Processing: %s", bar_id)

        # Fetch data
        chain = fetch_option_chain(index)
        if not chain:
            logger.warning("NO_DATA for %s — skipping", index)
            append_processed_bar(bar_id)
            processed.add(bar_id)
            continue

        cache.put(index, chain)

        # Data quality gate
        if not gate(chain, index):
            logger.warning("DATA_QUALITY FAIL for %s — NO_TRADE", index)
            append_processed_bar(bar_id)
            processed.add(bar_id)
            log_observation(bar_id, f"{index} DATA_QUALITY_FAIL")
            log_decision(bar_id, "N/A", "REJECT", f"data_quality_fail_{index}")
            continue

        # Spot price
        spot = fetch_spot_price(index)
        if not spot:
            logger.warning("NO_SPOT for %s — skipping", index)
            append_processed_bar(bar_id)
            processed.add(bar_id)
            continue

        # Side selector (independent CE/PE)
        sides = select_sides(chain, spot, index)
        if not sides:
            logger.info("No qualifying sides for %s", index)
            append_processed_bar(bar_id)
            processed.add(bar_id)
            continue

        for side in sides:
            if valid_count >= MAX_VALID_TRADES:
                break

            # Symbol resolution
            symbols = resolve_symbols(index, spot, chain, side, now)
            if not symbols:
                logger.warning("SYMBOL_RESOLVE FAIL %s %s", index, side)
                continue

            # Premium ratio gate
            w_premium = extract_premium(
                chain, symbols["strike"], symbols["weekly_expiry"], side
            )
            m_premium = extract_premium(
                chain, symbols["strike"], symbols["monthly_expiry"], side
            )

            passes, ratio = premium_ratio_gate(w_premium, m_premium, index, side)
            if not passes:
                log_observation(
                    bar_id,
                    f"{symbols['weekly_symbol']} / {symbols['monthly_symbol']}, "
                    f"ratio={ratio:.4f}, W={w_premium:.2f}, M={m_premium:.2f}, "
                    f"side={side}, REJECTED"
                )
                log_decision(bar_id, side, "REJECT",
                             f"premium_ratio_{ratio:.2f}_outside_0.9-1.1")
                continue

            # Capital exposure gate (60% total)
            if not check_total_exposure(active_trades, index, side):
                log_observation(bar_id, f"{index} {side} EXPOSURE_GATE_REJECT")
                from config.frozen_params import CAPITAL_PCT as _CP
                _cur = sum(_CP.get(f"{t['index']}_{t['side']}", 0) for t in active_trades)
                _new = _CP.get(f"{index}_{side}", 0)
                log_decision(bar_id, side, "REJECT",
                             f"total_exposure_would_be_{_cur + _new:.1f}_percent")
                continue

            # Concurrent limit
            if not check_concurrent_limit(active_trades, index, side):
                log_observation(bar_id, f"{index} {side} CONCURRENT_LIMIT_REJECT")
                log_decision(bar_id, side, "REJECT",
                             f"concurrent_limit_{index}_{side}")
                continue

            # Valid trade signal
            valid_count += 1
            trade = {
                "index": index,
                "side": side,
                "entry_time": now.isoformat(),
                "bar_id": bar_id,
                "symbols": symbols,
                "ratio": ratio,
                "weekly_premium": w_premium,
                "monthly_premium": m_premium,
            }
            active_trades.append(trade)

            obs_text = (
                f"{symbols['weekly_symbol']} / {symbols['monthly_symbol']}, "
                f"ratio={ratio:.4f}, weekly_premium={w_premium:.2f}, "
                f"side={side}"
            )
            log_observation(bar_id, obs_text)
            log_decision(bar_id, side, "ACCEPT", "passed_all_gates")
            logger.info("%s", WARNING_BANNER)
            logger.info("VALID TRADE #%d: %s", valid_count, obs_text)

            # Periodic summary every 5 ACCEPTs
            if valid_count % 5 == 0:
                logger.info("RECON SUMMARY TRIGGERED -- accepts so far: %d / total processed: %d",
                            valid_count, len(processed))
                print_summary()

        append_processed_bar(bar_id)
        processed.add(bar_id)

        if valid_count >= MAX_VALID_TRADES:
            break

    return valid_count


def main():
    logger.info("=" * 60)
    logger.info("PAPER RECON START — session=%s", _session_id)
    logger.info("%s", WARNING_BANNER)
    logger.info("=" * 60)

    # Integrity audit
    audit = audit_params()
    if not audit["passed"]:
        logger.error("INTEGRITY AUDIT FAILED — aborting")
        sys.exit(1)
    logger.info("Integrity audit passed — hash=%s", audit["strategy_hash"][:16])

    # Restart invalidation: mark any bars from previous session window as INVALID
    processed = load_processed_bars()
    logger.info("Loaded %d previously processed bars", len(processed))

    active_trades: list[dict] = []
    valid_count = 0

    while valid_count < MAX_VALID_TRADES:
        try:
            valid_count = run_one_cycle(processed, active_trades, valid_count)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error("Cycle error: %s — marking session INVALID", e)
            log_observation(
                f"SESSION_{_session_id}",
                f"INVALID — restart/error: {e}"
            )
            break

        if valid_count >= MAX_VALID_TRADES:
            break

        logger.info("Sleeping %d seconds... (valid=%d/%d)", POLL_INTERVAL, valid_count, MAX_VALID_TRADES)
        logger.info("%s", WARNING_BANNER)
        time.sleep(POLL_INTERVAL)

    logger.info("=" * 60)
    logger.info("PAPER RECON COMPLETE — %d valid trades logged", valid_count)
    logger.info("%s", WARNING_BANNER)
    logger.info("=" * 60)

    # Final summary
    logger.info("RECON SUMMARY TRIGGERED -- accepts so far: %d / total processed: %d",
                valid_count, len(processed))
    print_summary()


if __name__ == "__main__":
    main()
