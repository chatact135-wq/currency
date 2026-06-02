# MarketMind AI V23 — Live Price Guard

Fixes stale price problem:
- Dashboard uses TwelveData live price endpoint, not only M5 candle close
- Candles remain for analysis/backtest
- Blocks trade if live price/cache is stale
- Shows live cache age, candle close, and difference

Required:
DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

Optional:
FMP_API_KEY
LIVE_PRICE_CACHE_SECONDS=8
MAX_LIVE_PRICE_AGE_SECONDS=20
MAX_CANDLE_CACHE_SECONDS=180

After deploy:
1. /api/v23/health
2. /api/v23/price-check
3. /dashboard
4. /api/v23/market-map
