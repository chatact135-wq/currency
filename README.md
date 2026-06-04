# MarketMind AI V44 — Move Completion Detector

Purpose:
Detect whether a BUY or SELL move is still early/active, or already extended/finished.

V44 adds:
- MOVE STARTING
- MOVE ACTIVE
- MOVE EXTENDED
- MOVE LIKELY FINISHED
- DO NOT ENTER LATE
- TAKE PROFIT / PROTECT PROFIT
- Blocks master decision if move is likely finished

Uses moves/points:
- 10 moves = 1 pip on EUR/USD and GBP/USD

Optional Railway variables:
- MOVE_STARTING_MOVES=12
- MOVE_ACTIVE_MOVES=25
- MOVE_EXTENDED_MOVES=40
- MOVE_FINISHED_MOVES=55
- MOVE_WEAK_CANDLE_MOVES=6

Use:
- /dashboard
- /api/v44/signals
- /api/v44/move-completion
- /api/v44/usage
