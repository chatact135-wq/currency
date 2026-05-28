# MarketMind AI V7 — Profile + SMC + SB + RAVEN

Focused version based on your feedback.

## Main changes
- Live data only, no fake/demo candles.
- Frequency/Volume Profile layer using price-frequency proxy when true volume is unavailable.
- Separate strategy alerts inside every asset card:
  - Frequency Profile alert
  - SB model alert
  - SMC model alert
  - RAVEN composite alert
- Each strategy can trigger independently; it does not require all strategies together.
- Buy entry interval displays ascending: low → high.
- Sell entry interval displays descending: high → low.
- Scalp plan includes exact entry, SL, TP1, TP2, full close, invalidation, timer.
- Weighted decision engine: trade can appear when one strong model or several medium models align.

## Required Railway variables
DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

Recommended:
NEWS_API_KEY
ACTIVE_ASSETS=EURUSD,GBPUSD,XAUUSD
DASHBOARD_REFRESH_SECONDS=15
MARKET_CACHE_SECONDS=180
NEWS_CACHE_SECONDS=600
MIN_TRADE_SCORE=54
