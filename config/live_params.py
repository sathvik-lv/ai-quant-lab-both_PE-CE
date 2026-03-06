# SOURCE_OF_TRUTH: LIVE_CONFIG -- IMMUTABLE
"""Live/paper trading parameters. Change LIVE_MODE only after full review."""

LIVE_MODE = False  # change to True only manually after full review
SIMULATE_COSTS = True  # toggle for paper vs dry-run
SLIPPAGE_BPS = 5  # conservative estimate (basis points)
BROKERAGE_PER_LOT = 20  # INR per lot
STT_PERCENT = 0.125  # Securities Transaction Tax percent
MAX_DAILY_LOSS_PCT = -2.0  # auto-kill if breached
KILL_SWITCH_FILE = "kill.switch"  # touch this file to immediate halt
