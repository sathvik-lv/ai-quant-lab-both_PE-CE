# SOURCE_OF_TRUTH: MONITORING_ONLY -- IMMUTABLE
"""
Passive summary reporter: reads decision_log.md + observations_log.md.
Produces stats only. Never writes back to decision logic files.
"""

import os
import re
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DECISION_LOG_FILE = os.path.join(PROJECT_ROOT, "decision_log.md")
OBSERVATIONS_FILE = os.path.join(PROJECT_ROOT, "observations_log.md")


def generate_recon_summary() -> dict:
    """
    Read decision_log.md and observations_log.md.
    Returns summary dict with counts and breakdowns.
    """
    accept_count = 0
    reject_count = 0
    reject_breakdown: dict[str, int] = defaultdict(int)
    accept_by_side: dict[str, int] = defaultdict(int)
    accept_by_index: dict[str, int] = defaultdict(int)
    last_accept_timestamp = ""
    total_lines = 0

    if os.path.exists(DECISION_LOG_FILE):
        with open(DECISION_LOG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total_lines += 1

                # Parse: timestamp | bar_id | side=X | decision=Y | reason=Z
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < 5:
                    continue

                timestamp = parts[0]
                bar_id = parts[1]
                side_part = parts[2]    # side=CE
                decision_part = parts[3]  # decision=ACCEPT
                reason_part = parts[4]   # reason=...

                side = side_part.replace("side=", "")
                decision = decision_part.replace("decision=", "")
                reason = reason_part.replace("reason=", "")

                # Extract index from bar_id (e.g. BANKNIFTY_20230102_0940_5m)
                index = bar_id.split("_")[0] if "_" in bar_id else "UNKNOWN"

                if decision == "ACCEPT":
                    accept_count += 1
                    accept_by_side[side] += 1
                    accept_by_index[index] += 1
                    last_accept_timestamp = timestamp
                elif decision == "REJECT":
                    reject_count += 1
                    # Bucket reasons
                    if "premium_ratio" in reason:
                        reject_breakdown["premium_ratio_outside"] += 1
                    elif "total_exposure" in reason:
                        reject_breakdown["total_exposure_exceeded"] += 1
                    elif "concurrent_limit" in reason:
                        reject_breakdown["concurrent_limit"] += 1
                    elif "data_quality" in reason:
                        reject_breakdown["data_quality_fail"] += 1
                    elif "stale_data" in reason:
                        reject_breakdown["stale_data"] += 1
                    else:
                        reject_breakdown[reason] += 1

    return {
        "total_bars_processed": total_lines,
        "accept_count": accept_count,
        "reject_count": reject_count,
        "reject_breakdown": dict(reject_breakdown),
        "accept_by_side": dict(accept_by_side),
        "accept_by_index": dict(accept_by_index),
        "last_accept_timestamp": last_accept_timestamp,
    }


def print_summary() -> dict:
    """Pretty-print the recon summary to console. Returns the summary dict."""
    summary = generate_recon_summary()

    try:
        from tabulate import tabulate
        _has_tabulate = True
    except ImportError:
        _has_tabulate = False

    print("\n" + "=" * 60)
    print("RECON SUMMARY REPORT")
    print("=" * 60)
    print(f"Total decisions logged:  {summary['total_bars_processed']}")
    print(f"ACCEPT:                 {summary['accept_count']}")
    print(f"REJECT:                 {summary['reject_count']}")
    print(f"Last ACCEPT at:         {summary['last_accept_timestamp']}")

    print("\n--- Reject Breakdown ---")
    if _has_tabulate:
        reject_rows = sorted(summary["reject_breakdown"].items(), key=lambda x: -x[1])
        print(tabulate(reject_rows, headers=["Reason", "Count"], tablefmt="simple"))
    else:
        for reason, count in sorted(summary["reject_breakdown"].items(), key=lambda x: -x[1]):
            print(f"  {reason:40s} {count:>8d}")

    print("\n--- Accept by Side ---")
    if _has_tabulate:
        side_rows = sorted(summary["accept_by_side"].items())
        print(tabulate(side_rows, headers=["Side", "Count"], tablefmt="simple"))
    else:
        for side, count in sorted(summary["accept_by_side"].items()):
            print(f"  {side:10s} {count:>6d}")

    print("\n--- Accept by Index ---")
    if _has_tabulate:
        index_rows = sorted(summary["accept_by_index"].items(), key=lambda x: -x[1])
        print(tabulate(index_rows, headers=["Index", "Count"], tablefmt="simple"))
    else:
        for index, count in sorted(summary["accept_by_index"].items(), key=lambda x: -x[1]):
            print(f"  {index:15s} {count:>6d}")

    print("=" * 60 + "\n")
    return summary
