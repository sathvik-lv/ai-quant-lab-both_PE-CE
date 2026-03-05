# SOURCE_OF_TRUTH: SECTION_1, SECTION_6, SECTION_15 -- IMMUTABLE

INDICES = ["BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTY"]

# AVWAP proximity threshold (% from AVWAP to qualify)
AVWAP_PROXIMITY_PCT = 1.5

# Value area: number of candles to compute value area
VALUE_AREA_CANDLES = {
    "BANKNIFTY": 60,
    "FINNIFTY": 60,
    "MIDCPNIFTY": 60,
    "NIFTY": 60,
}

# Max holding days per index (Section 9)
MAX_HOLD_DAYS = {
    "BANKNIFTY": 5,
    "FINNIFTY": 5,
    "MIDCPNIFTY": 5,
    "NIFTY": 5,
}

# Capital allocation per side per index (Section 6 -- locked)
CAPITAL_PCT = {
    "BANKNIFTY_PE": 17.34,
    "NIFTY_PE": 13.00,
    "FINNIFTY_PE": 8.67,
    "MIDCPNIFTY_PE": 4.34,
    "FINNIFTY_CE": 3.60,
    "BANKNIFTY_CE": 2.70,
    "NIFTY_CE": 1.80,
    "MIDCPNIFTY_CE": 0.90,
}

# Max total deployment across CE + PE (Section 6)
MAX_TOTAL_EXPOSURE_PCT = 60.0

# Max concurrent trades per index per side (Section 15)
MAX_CONCURRENT = {
    "BANKNIFTY_PE": 2,
    "BANKNIFTY_CE": 2,
    "FINNIFTY_PE": 2,
    "FINNIFTY_CE": 2,
    "MIDCPNIFTY_PE": 1,
    "MIDCPNIFTY_CE": 1,
    "NIFTY_PE": 2,
    "NIFTY_CE": 2,
}

# Premium ratio gate bounds (Section 3)
PREMIUM_RATIO_MIN = 0.9
PREMIUM_RATIO_MAX = 1.1

# Data staleness threshold in seconds
DATA_STALE_SECONDS = 300  # 5 minutes
