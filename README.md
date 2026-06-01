# MarketMind AI V19 — Signal Lock Pro

V19 fixes the dangerous issue where a signal can show BUY/SELL and then switch to NO TRADE too fast.

New logic:
- Market bias is separate from entry permission.
- No entry is allowed from probability alone.
- Entry is allowed only when action is EXECUTE / ACTIVE.
- Signal lock keeps a valid signal stable for a short period.
- If the signal weakens, it shows CANCEL / WAIT, not silent flip.
- If an active trade is invalidated, it shows EXIT / CANCEL.
- Adds "entry_permission" and "trade_state" clearly in the dashboard.

Required Railway variables:
DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

After deploy:
1. /api/v19/admin/backfill-six-months
2. /api/v19/admin/run-backtest
3. /api/v19/admin/recalculate-weights
4. /dashboard
5. /api/v19/best-action
