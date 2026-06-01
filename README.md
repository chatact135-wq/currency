# MarketMind AI V17 — Decision Executor

V17 focuses on the exact problem found in V16: the system showed setup information but did not clearly say what to do.

V17 adds:
- Best Action panel: EXECUTE, CONDITIONAL BUY/SELL, or NO TRADE.
- Exact conditional order-style triggers:
  - Pullback reaction zone
  - Breakout/breakdown activation
- Exact stop, TP1, TP2, full close guidance even before ACTIVE, marked as conditional.
- Stronger confluence logic combining:
  - Master Bias
  - Execution pressure
  - Probability
  - Reward/Risk
  - Historical level memory
  - Adaptive backtest edge when available
- Best asset endpoint:
  /api/v17/best-action
- Six-month historical backfill retained.

Required Railway variables:
DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

After deploy, run:
1. /api/v17/admin/backfill-six-months
2. /api/v17/admin/run-backtest
3. /api/v17/admin/recalculate-weights
4. /dashboard
