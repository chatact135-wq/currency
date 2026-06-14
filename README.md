# EdgeFlow Pro v2 - High Confluence Forex System

Clean, professional trading signal system focused on **EUR/USD** and **GBP/USD**.

## Features
- High confluence multi-timeframe analysis (M15 + H1 + H4)
- Clear signals with Entry, Stop Loss, Take Profit
- Confidence scoring
- Clean architecture (no duplicated test versions)
- Ready for Railway deployment

## Quick Start (Local)

```bash
pip install -r requirements.txt
TWELVEDATA_API_KEY=your_key_here uvicorn app:app --reload
```

Then open: http://127.0.0.1:8000

## Environment Variables
- `TWELVEDATA_API_KEY` (required for live data)

## Deployment (Railway)
1. Upload this folder
2. Add environment variable: `TWELVEDATA_API_KEY`
3. Deploy

This is v2 - built clean from the beginning with better strategy logic.
