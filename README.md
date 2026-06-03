# MarketMind AI V31.1 — Persistent Expiry Fix

Fixes V31 dashboard error:
- API no longer depends on a new DB table for signal expiry.
- Expiry uses safe server memory, so page/API refresh does not reset it.
- Dashboard fetch now checks HTTP status and JSON parsing safely.

Use:
- /dashboard
- /api/v31_1/signals
- /api/v31_1/signal-memory
- /api/v31_1/usage
