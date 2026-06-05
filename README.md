# EdgeFlow FX Pro V4 — Real Strategy Event Engine

This is not only text/UI change.

V4 adds a real event-based strategy engine:
- Detects fast impulse moves
- Detects break of BUY above / SELL below
- Detects velocity from last refresh
- Detects if move is already late/missed
- Creates its own small-risk scalp entry, stop, and target when momentum confirms
- Overrides PLAN ONLY when a real strategy event is active

Professional event states:
- FAST IMPULSE BUY / SELL
- BREAKOUT BUY / SELL
- PRE-BREAK MOMENTUM BUY / SELL
- SCALP NOW BUY / SELL
- TRADE NOW BUY / SELL
- MOVE MISSED — DO NOT CHASE
- PLAN ONLY — DO NOT ENTER
- NO STRATEGY

Key idea:
The system should not buy only because price is up.
It should buy only when a strategy event is detected and risk is controlled.

New endpoint:
- /api/pro/v4/strategy-events

Main:
- /dashboard
- /api/pro/v4/signals
- /api/pro/v4/strategy-events
