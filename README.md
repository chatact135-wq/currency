# MarketMind AI V2 — Smart Zones

Upgraded Railway + Neon ready version.

## New features
- Smart BUY zone and SELL zone
- Do-not-buy / do-not-sell warnings
- Support / resistance and daily high/low
- Entry zone, stop-loss, take-profit 1 and 2
- Expected move time
- Optional real Twelve Data API support
- Safe fallback data if API key is missing
- Auto-refresh dashboard

## Railway variables
Required:
DATABASE_URL=your Neon connection string
SECRET_KEY=marketmind-secret-2026

Optional:
TWELVEDATA_API_KEY=your Twelve Data key

## Test URLs
/dashboard
/api/smart-signal/EURUSD
/api/smart-signals
/api/history
