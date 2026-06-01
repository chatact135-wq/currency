# MarketMind AI V22 — Market Map Switch Engine

Adds always-on market map:
- Current bias
- Buy switch / Sell switch
- Distance in pips
- Aggressive entry / Safe entry
- Stop loss / TP1 / TP2 / Full close
- Flip rule from buy to sell or sell to buy

Required:
DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

Optional:
FMP_API_KEY

After deploy:
1. /api/v22/admin/backfill-six-months
2. /api/v22/admin/run-backtest
3. /api/v22/admin/recalculate-weights
4. /api/v22/market-map
5. /dashboard
