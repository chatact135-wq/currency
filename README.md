# MarketMind AI V15 — Practical Precision

V15 improves V14 based on live testing:

- Adds SCALP READY between WATCH and ACTIVE.
- Does not wait forever when Master Bias + Execution agree.
- Separates BUY pullback trigger from BUY breakout trigger.
- Separates SELL pullback trigger from SELL breakdown trigger.
- Keeps adaptive backtest learning and expected edge.
- Keeps reward/risk filtering before ACTIVE.
- Adds clearer close/exit rules.

Required Railway variables:
DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

After deploy:
/api/v15/admin/download-history
/api/v15/admin/run-backtest
/api/v15/admin/recalculate-weights
/dashboard
