# MarketMind AI V5 Sniper Pro

Professional live-only sniper/scalp assistant for Railway + Neon.

## Includes
- Live Twelve Data candles only; no fake fallback
- Sniper scalp engine with tight entry intervals
- TP1, TP2, full close, stop loss, invalidation
- Move SL to breakeven after TP1 logic
- Trade timer and signal expiry
- SB/SMC: liquidity sweep, FVG, BOS/CHOCH, order-block style zone
- No-trade filter for weak setups
- News sentiment and news countdown
- London/New York session timers
- AJAX UI with professional trade cards

## Required Railway variables
DATABASE_URL, SECRET_KEY, TWELVEDATA_API_KEY

## Recommended variables
NEWS_API_KEY, MARKET_CACHE_SECONDS=180, DASHBOARD_REFRESH_SECONDS=15, ACTIVE_ASSETS=EURUSD,GBPUSD,XAUUSD
