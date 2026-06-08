# EdgeFlow V3 — A/B Comparison Test

This build keeps the original system unchanged and adds two separate test systems:

## Original system
- Dashboard: `/dashboard`
- Review: `/review`
- Database: `runtime_data/edgeflow_signals.db`

## Test A — Conservative
- Dashboard: `/test-a`
- Review: `/test-a/review`
- API: `/test-a/api/signals`
- Database: `runtime_data/edgeflow_signals_test_a.db`

Logic:
- Trend-aligned only.
- Pullback Continuation Buy/Sell.
- Break + Retest Continuation Buy/Sell.
- No Momentum Confirmation upgrade.
- First breakout/breakdown is blocked as PLAN ONLY.

## Test B — Controlled Momentum
- Dashboard: `/test-b`
- Review: `/test-b/review`
- API: `/test-b/api/signals`
- Database: `runtime_data/edgeflow_signals_test_b.db`

Logic:
- Same as Test A.
- Adds Momentum Confirmation Buy/Sell.
- Can upgrade strong PLAN ONLY setups into SCALP NOW when trend bias, EMA alignment, candle direction, and momentum confirm.

## Review improvements
- Each test has its own `/review` page.
- Each test stores results in a separate database.
- Review pips/moves are now clamped to avoid impossible negative adverse/favorable values.
- Review no longer uses demo fallback data, so fake review stats are not saved if live candle data fails.
- Duplicate signals are reduced using a 15-minute duplicate cooldown bucket.

## Suggested testing
Run each system for 3–4 hours, then compare:
- Total signals
- TP HIT
- SL HIT
- MISSED BUY/SELL MOVE
- GOOD BLOCK
- Average favorable/adverse moves
- Good rate %

