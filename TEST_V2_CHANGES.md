# EdgeFlow Terminal Pro — TEST V2 Changes

This package keeps the original system unchanged and adds a separate test system under `/test`.

## Original system remains available
- Dashboard: `/dashboard` or `/`
- Review: `/review`
- API: `/api/signals`
- Database: `runtime_data/edgeflow_signals.db`

## New test system
- Test dashboard: `/test`
- Test review: `/test/review`
- Test API: `/test/api/signals`
- Test review API: `/test/api/review-signals`
- Test database: `runtime_data/edgeflow_signals_test.db`

## Strategy updates in TEST V2

### 1. New strategy added
`Momentum Confirmation Buy` and `Momentum Confirmation Sell`

Purpose: reduce missed moves where the old system said `PLAN ONLY — DO NOT ENTER` but the market later moved strongly in the expected direction.

The new strategy only upgrades to a real scalp signal when:
- market bias agrees with the direction,
- EMA20/EMA50 alignment confirms trend,
- current candle confirms the direction,
- recent momentum is strong,
- price is not too far extended from structure.

### 2. Breakout filter added
Old `Strong Trend Day Breakout` / `Strong Trend Day Breakdown` trades are blocked in TEST V2 and converted into watch-only signals:
- `Breakout Watch — Wait Pullback`
- `Breakdown Watch — Wait Pullback`

Reason: the review data showed many first-breakout entries hit stop loss quickly.

### 3. Separate test database
The `/test` system saves into a separate SQLite file so original review data does not mix with the new strategy results.

### 4. 5-minute duplicate cooldown in test DB
The test DB uses a wider duplicate bucket to reduce repeated counting of the same opportunity.

## How to compare
Run the original system and `/test` side-by-side:
1. Open `/dashboard`
2. Open `/test`
3. Let both collect data for several hours.
4. Review original results at `/review`.
5. Review V2 results at `/test/review`.

Recommended minimum sample before judging:
- 30+ signals per strategy for early reading,
- 50–100+ signals for more reliable evaluation.
