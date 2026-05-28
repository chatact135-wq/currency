# MarketMind AI V12 — TwelveData + ML Pro

This version returns to Twelve Data for market candles because Finnhub free access blocked forex/gold data.

## What V12 does

- Uses Twelve Data live candles for EURUSD, GBPUSD, XAUUSD
- Stores candles in Neon PostgreSQL
- Stores every generated signal in Neon
- Evaluates old signals after a configured time window
- Builds ML-ready datasets
- Provides ML probability when enough history exists
- Uses fallback statistical probability before ML has enough samples
- Keeps Master Bias, Execution Trigger, Confirmation/Risk, Grade, and exact-entry logic
- BUY interval = ascending
- SELL interval = descending
- WAIT/SETUP does not show fake exact entry

## Required Railway Variables

DATABASE_URL
SECRET_KEY
TWELVEDATA_API_KEY

Keep FINNHUB_API_KEY optional; not required for prices.

## Important API endpoints

/dashboard
/api/v12/signals
/api/v12/health
/api/v12/admin/download-history
/api/v12/admin/evaluate-signals
/api/v12/ml/stats
