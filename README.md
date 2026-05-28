# MarketMind AI V3 LIVE

Live-data-only trading signal dashboard for Railway + Neon.

## Required Railway variables
DATABASE_URL=your Neon PostgreSQL URL
SECRET_KEY=marketmind-secret-2026
TWELVEDATA_API_KEY=your Twelve Data API key

## Optional news variables
NEWS_API_KEY=your NewsAPI key
FINNHUB_API_KEY=your Finnhub key

## Features
- No fake/demo prices
- AJAX updates without full-page reload
- Backend cache to protect free API limits
- EUR/USD, GBP/USD, XAU/USD, WTI Oil
- Smart buy/sell zones
- Entry, SL, TP1, TP2
- News sentiment support
- UAE trading session filter

## URLs
/dashboard
/api/live-signals
/api/live-signal/EURUSD
/api/health
