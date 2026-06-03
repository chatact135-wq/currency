# MarketMind AI V32 — Stable Expiry

Fixes:
- Removes the broken /api/v31_1 route issue.
- Uses clean /api/v32 routes.
- Adds safe persistent signal expiry using server memory.
- Refreshing dashboard/API does not reset expiry while the server is running.
- No new DB table is required, so it will not crash because of missing migrations.
- Keeps V30 usage meter and dashboard alerts.

Use:
- /dashboard
- /api/v32/signals
- /api/v32/signal-memory
- /api/v32/usage
- /api/v32/price-check
