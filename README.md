# MarketMind AI V45 — Trigger Lock Engine

Purpose:
Stop trigger/entry numbers from moving away every refresh.

Adds:
- BUY trigger lock
- SELL trigger lock
- Trigger expiry
- Trigger reached detection
- Hold confirmation
- Prevents chasing a moving trigger

Optional Railway variables:
- TRIGGER_LOCK_SECONDS=300
- TRIGGER_HOLD_SECONDS=10
- TRIGGER_TOUCH_TOLERANCE_MOVES=2

Use:
- /dashboard
- /api/v45/signals
- /api/v45/trigger-lock
