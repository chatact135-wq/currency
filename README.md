# MarketMind AI V20 — Final Decision + Time Forecast

V20 changes the dashboard from "many signals" to a real command-style output.

It shows:
- FINAL ACTION: ENTER BUY / ENTER SELL / WAIT / MANAGE / CANCEL
- Direction forecast: UP / DOWN / SIDEWAYS
- Estimated time to trigger
- Estimated time to TP1
- Estimated time to invalidation risk
- Entry permission
- Trigger, entry, stop loss, TP1, TP2, full close
- Reason for the decision

Important:
No system can know the future exactly. V20 estimates time using:
- recent candle speed
- ATR
- distance to trigger/TP/SL
- momentum
- historical memory
- adaptive backtest data

Required Railway variables:
DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

After deploy:
1. /api/v20/admin/backfill-six-months
2. /api/v20/admin/run-backtest
3. /api/v20/admin/recalculate-weights
4. /dashboard
5. /api/v20/best-action
