# MarketMind AI V27 — Regime Guard + Trigger State

Adds:
- Trigger state:
  NOT_REACHED, BROKEN_WAIT_HOLD, ACTIVE, TOO_LATE_DO_NOT_CHASE, FAILED_CANCEL
- Market regime guard:
  NEWS_WAIT, POST_NEWS_IMPULSE, DATA_STALE, LOW_LIQUIDITY, LIQUIDITY_SWEEP_RISK, VOLATILITY_SPIKE
- No-chase logic
- Blocks entries during dangerous regimes

Note:
Real spread/slippage/broker-delay detection needs broker bid/ask feed.
Without broker feed, V27 estimates risk from live cache, candles, wicks, volatility, and news mode.

Links:
- /api/v27/price-check
- /api/v27/market-map
- /api/v27/signals
- /dashboard
