# MarketMind AI V11 — Tick Memory Pro

This version fixes the Finnhub "You don't have access to this resource" error by NOT using Finnhub candle endpoints.

It uses:
- Finnhub live quote/rate endpoint only
- Neon PostgreSQL tick storage
- self-built candles from stored ticks
- fallback bootstrap candles from collected ticks only, not fake prices
- Master Bias + Execution Trigger + Risk Grade
- ML-ready signal memory

Important:
At first, the system needs a short time to collect ticks. It may show "collecting ticks" until enough ticks exist.

Routes:
- /dashboard
- /api/v11/signals
- /api/v11/collect-ticks
- /api/v11/health
