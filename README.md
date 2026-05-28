# MarketMind AI V6 Balanced Pro

This version fixes the V5 problem where it showed NO TRADE too often.

## Key changes
- Uses weighted scoring instead of requiring every strategy together
- Shows Matched Conditions and Missing Conditions
- Gives SELL/BUY if market direction is clear even without perfect SMC setup
- Adds momentum and candle pressure detection
- Keeps SMC/SB models but does not force all of them at once
- Exact scalp interval, SL, TP1, TP2, full close, invalidation
- Signal quality score and direction bias
- Live data only, no fake prices
- AJAX updates
- API cache protection

## Required Railway Variables
DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

Optional:
NEWS_API_KEY
ACTIVE_ASSETS=EURUSD,GBPUSD,XAUUSD
DASHBOARD_REFRESH_SECONDS=15
MARKET_CACHE_SECONDS=180
NEWS_CACHE_SECONDS=600
MIN_SIGNAL_SCORE=58
STRONG_SIGNAL_SCORE=78
