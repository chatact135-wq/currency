# MarketMind AI V4 PRO LIVE

Advanced live-market trading assistant for Railway + Neon.

## Included
- LIVE DATA ONLY: no fake/demo price fallback
- AJAX card update without full page refresh
- API-limit protection with server-side cache
- SB/SMC analysis: liquidity sweep, Fair Value Gap, BOS/CHOCH, order-block style zones
- Dynamic scalp/intraday entry intervals
- Scalp countdown timer and signal expiry
- News countdown / high-impact news window
- London/New York/overlap timers
- Exact Entry, Stop Loss, TP1, TP2, Invalidation
- News sentiment from NewsAPI when key is provided
- Clear LIVE DATA ERROR when API key/limit fails

## Railway variables
Required:
DATABASE_URL, SECRET_KEY, TWELVEDATA_API_KEY

Recommended:
NEWS_API_KEY, DASHBOARD_REFRESH_SECONDS=15, MARKET_CACHE_SECONDS=180, NEWS_CACHE_SECONDS=600, ACTIVE_ASSETS=EURUSD,GBPUSD,XAUUSD

## URLs
/dashboard
/api/v4/signals
/api/v4/signal/EURUSD
/api/v4/health

Educational assistant only. No system can guarantee profit.
