# MarketMind AI V41 — Fast Start Detector

Goal:
Detect the beginning of a fast BUY/SELL move earlier, before the full move finishes.

Adds:
- FAST BUY STARTING
- FAST SELL STARTING
- FAST START BUY ALLOWED
- FAST START SELL ALLOWED
- FAST MOVE ALREADY HAPPENED — DO NOT ENTER LATE
- Moves/points display beside pips
- Faster scalping defaults for EUR/USD and GBP/USD

Important:
Fast start signals are early and higher risk. They must use small stop/cancel and small target.

Optional Railway variables:
- FAST_START_ENABLED=true
- FAST_START_MIN_MOVES=8
- FAST_START_CONFIRM_MOVES=12
- FAST_START_MAX_LATE_MOVES=18
- EARLY_MIN_REWARD_PIPS_FX=2
- EARLY_MAX_RISK_PIPS_FX=2
- EARLY_MIN_RR=1.1
- EARLY_MAX_LATE_DISTANCE_PIPS=1.5

Use:
- /dashboard
- /api/v41/signals
- /api/v41/fast-start
- /api/v41/usage
