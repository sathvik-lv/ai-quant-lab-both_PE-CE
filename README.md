# ATM CE & PE Calendar Spread -- v1.4 Reconnaissance Core

Strategy: `STRATEGY_LOCKED_V1.4_CE_PE.md` (LOCKED -- DO NOT EDIT)

## RECONNAISSANCE RULES

- If any infra question (symbols, data freshness, restart, replay) fails in a session, void ALL logic observations (side selector, premium ratio, capital exposure) from that session.
- Distrust any recon results if system slept, timezone changed, or clock synced mid-session.
- Must observe at least one weekly expiry adjacency week and one monthly overlap week before declaring recon complete (continue beyond 30 valid trades if needed).
- Recon must feel boring. Exciting recon = suspect.

## RECONNAISSANCE QUESTION CHECKLIST

1. Side selector producing expected CE or PE independently?
2. Premium ratio gate rejecting correctly for both CE and PE?
3. Resolved symbols correct (weekly + monthly per side)?
4. Data freshness caught?
5. Restart/replay behavior correct?
6. Total capital exposure check enforcing 60% across CE+PE?

## Observations log rule

timestamp + bar_id + concrete artifact only (e.g. "BANKNIFTY26MAR60000CE / BANKNIFTYAPR60000CE, ratio=1.08, weekly_premium=142.5, side=CE"). No opinions.

See `observations_log.md` for logged observations.

## Project Structure

```
STRATEGY_LOCKED_V1.4_CE_PE.md   -- Locked strategy (NEVER EDIT)
README.md                        -- This file
observations_log.md              -- Recon observations (artifacts only)
processed_bars.log               -- Replay protection (bar_id per line)
requirements.txt
config/frozen_params.py          -- Locked parameters
src/data/                        -- fetcher, symbol_mapper, cache, data_quality_gate
src/strategy/                    -- side_selector, filters, risk_manager_minimal
src/utils/                       -- integrity_audit_minimal
reports/
run_paper_recon.py               -- Paper reconnaissance (3 min intervals)
run_backtest_recon.py            -- Historical backtest (2023-Mar 2026)
```

## Running

```bash
pip install -r requirements.txt
python run_backtest_recon.py
python run_paper_recon.py
```

## HUMAN REVIEW CHECKPOINT 2 -- EXPANSION PHASE

- Only visibility/logging additions allowed from this point
- Core logic remains frozen per STRATEGY_LOCKED_V1.4_CE_PE.md
- Any commit that modifies side_selector.py, filters.py, or frozen_params.py logic = INVALID
- decision_log.md must remain factual, timestamped, mechanical only
- Goal: build full visibility into why 83,990+ bars are rejected without changing why
