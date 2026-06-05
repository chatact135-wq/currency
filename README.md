# EdgeFlow Terminal Pro — Backtest Lab V1

A professional-style backtesting lab for forex scalping strategy research.

This is **not a live signal system**. It is a strategy testing platform.

## What it does

- Upload EUR/USD or GBP/USD BID and ASK M1 CSV files.
- Merge BID/ASK data.
- Include spread in testing.
- Test multiple strategy families:
  - Fast Impulse Breakout
  - Fast Reversal
  - Pullback Continuation
- Compare presets:
  - Raw Balanced
  - Stricter All
  - Breakout Only
  - Reversal Only
  - Pullback Only
- Show:
  - trades
  - wins/losses
  - win rate
  - net moves
  - average moves
  - profit factor
  - max losing streak
  - average hold time
- Export CSV reports and HTML report.

## Why this exists

The earlier EUR/USD backtest showed the simple fast breakout/reversal logic was negative.  
So before building another live dashboard, this lab tests strategies on real historical BID/ASK data first.

## Quick start

```bash
pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Upload data

Upload pairs of files:

```text
EUR-USD_1Minute_BID_2026-06-02_...
EUR-USD_1Minute_ASK_2026-06-02_...
```

You can upload many days at once.

## Important backtest assumptions

- BUY entry uses ASK close.
- BUY exit uses BID high/low.
- SELL entry uses BID close.
- SELL exit uses ASK high/low.
- If stop and target are both hit in the same M1 candle, the test assumes stop first. This is conservative.
- M1 data cannot perfectly know intra-minute order. Tick data is better for fast scalping.

## Folder structure

```text
app.py
backtest_engine.py
templates/
static/
uploads/
results/
sample_data/
```

## Professional rule

A strategy is not allowed in live trading until it shows acceptable backtest results across enough data.
