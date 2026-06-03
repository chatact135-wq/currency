# MarketMind AI V37 — Strong Move Detector + TP Manager

V37 fixes the issue where strong moves down/up are not detected clearly.

Adds:
- Strong single-candle move detection
- Multi-candle impulse detection
- Break of recent high/low detection
- Strong move alerts even if new entry is not allowed
- Take profit management guidance:
  - If already in trade direction: take partial profit / move stop
  - If not in trade: do not chase, wait for price to come back
- Dashboard panel: STRONG MOVE / TAKE PROFIT

Use:
- /dashboard
- /api/v37/signals
- /api/v37/strong-move
- /api/v37/usage

Optional Railway variables:
- STRONG_MOVE_PIPS_FX=7
- STRONG_CANDLE_PIPS_FX=5
