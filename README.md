# MarketMind AI V18 — SMC 2.0 Decision Engine

V18 upgrades SMC from a simple alert into a backend decision module.

It calculates:
- SMC Context
- SMC Zone
- SMC Trigger
- SMC Invalidation
- SMC Confidence
- SMC Decision: BUY / SELL / NEUTRAL
- Final trade action after comparing SMC with RAVEN, Profile, Trend, History Memory, and Adaptive Edge

Required Railway variables:
DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

After deploy:
1. /api/v18/admin/backfill-six-months
2. /api/v18/admin/run-backtest
3. /api/v18/admin/recalculate-weights
4. /dashboard
5. /api/v18/best-action
