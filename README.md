# MarketMind AI V7 — Clean Logic

Fixes from V6/V5:
- If RAVEN/SB/SMC triggers SELL, final status cannot stay WAIT silently.
- WAIT does not show a huge fake "exact entry".
- BUY interval always displays ascending.
- SELL interval always displays descending.
- Strategy alerts are separated from executable signals.
- Exact entry only appears for BUY/SELL/SCALP/STRONG signals.
- WATCH signals show trigger level, not fake entry.

## Deploy
Upload contents to GitHub root and Railway redeploys.

## Required Railway Variables
DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

Recommended:
ACTIVE_ASSETS=EURUSD,GBPUSD,XAUUSD
MARKET_CACHE_SECONDS=180
DASHBOARD_REFRESH_SECONDS=15
EXECUTE_SCORE=55
WATCH_SCORE=28
