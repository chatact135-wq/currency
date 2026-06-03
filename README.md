# MarketMind AI V31 — Persistent Signal Expiry

V31 fixes the expiry reset problem.

Problem before:
- Every API refresh recalculated the signal.
- Expiry/timer could reset or disappear.

V31 solution:
- Signal creation time and expiry are stored in the database.
- Refreshing /signals or the dashboard does NOT reset expiry.
- Same asset + direction + close entry keeps the same expiry.
- If the signal expires, it stays expired until the trigger/direction changes.
- Dashboard shows persistent expiry state.

Links:
- /dashboard
- /api/v31/signals
- /api/v31/usage
