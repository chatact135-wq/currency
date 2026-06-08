# EdgeFlow Terminal Pro — Live Test V1

Professional live-test trading terminal for EUR/USD and GBP/USD.

This is not a "guaranteed profit" system. It is a controlled live-test platform using what we learned from the real-data backtest:

- Do not trust raw mixed signals.
- Detect market mode first.
- Avoid random reversals in strong trend days.
- Use breakout/retest and pullback continuation only when risk is controlled.
- Block chasing late moves.
- Use micro risk only until more results are proven.

## Main features

- Live dashboard
- TwelveData API support
- Market Mode Detector
  - TREND BUY
  - TREND SELL
  - NORMAL
  - CHOPPY
  - DANGER / HIGH VOLATILITY
- Strategy Engine
  - Break + Retest Continuation
  - Pullback Continuation
  - Strong Trend Day Continuation
  - Liquidity Sweep Reversal only when allowed
- No-Chase filter
- Risk / reward filter
- Trade Manager
- Daily Safety Guard
- Signal Journal

## Commands

The system only gives these commands:

```text
TRADE NOW BUY
TRADE NOW SELL
SCALP NOW BUY
SCALP NOW SELL
PLAN ONLY — DO NOT ENTER
NO TRADE
MOVE MISSED — DO NOT CHASE
MANAGE OPEN TRADE
```

## Run locally

```bash
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Railway

This package includes Dockerfile and railway.json.

Set environment variable:

```text
TWELVEDATA_API_KEY=your_key_here
```

Optional:

```text
EDGEFLOW_REFRESH_SECONDS=30
EDGEFLOW_MODE=live_test
```

## Important risk warning

Use demo or micro real-money testing only.

Recommended rules:
- Max 0.25% risk per trade.
- Max 1–2 trades per day.
- Stop after 2 losses.
- No trade when command is PLAN ONLY / NO TRADE / MOVE MISSED.

## V1.2 Signal Database + Strategy Review

Added SQLite database:
- runtime_data/edgeflow_signals.db

New pages:
- /review

New APIs:
- /api/signal-db
- /api/review-signals
- /api/reviews
- /api/strategy-performance

The system now saves every command and later reviews what happened after 15m / 1h / 4h.


## V1.3 Review Fixed
- Saves live price snapshots every refresh.
- Reviews saved signals using snapshots first.
- Uses TwelveData candles as backup.
- This reduces NO DATA results.
