# MarketMind AI V21 — News Countdown + Final Decision

Adds:
- News countdown
- USD/EUR/GBP news risk mode
- Pre-news WAIT gate
- Post-news impulse warning
- /api/v21/news endpoint
- Keeps final decision and time forecast

Required:
DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

Optional:
FMP_API_KEY
NEWS_PRE_WINDOW_MINUTES=15
NEWS_POST_WINDOW_MINUTES=15

After deploy:
1. /api/v21/admin/backfill-six-months
2. /api/v21/admin/run-backtest
3. /api/v21/admin/recalculate-weights
4. /api/v21/news
5. /dashboard
