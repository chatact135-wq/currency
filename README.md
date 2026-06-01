# MarketMind AI V16 — Historical Memory + Micro Trigger

V16 fixes the issue of far scalp trigger levels.

Main upgrades:
- Six-month history backfill endpoint
- Stored candle memory in Neon
- Historical level check before confirming triggers
- Micro scalp trigger zones:
  - EUR/USD and GBP/USD: close trigger levels, not huge 15+ pip zones
  - Gold: smaller practical dollar trigger zones
- Pullback and breakout triggers are displayed separately
- SCALP READY remains for aligned signals
- ACTIVE SCALP remains for cleaner triggers
- Adaptive backtest system kept

Required Railway variables:
DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

After deploy, run:
1. /api/v16/admin/backfill-six-months
2. /api/v16/admin/run-backtest
3. /api/v16/admin/recalculate-weights
4. /dashboard

Note:
The amount of six-month data downloaded depends on your Twelve Data plan/rate limits.
