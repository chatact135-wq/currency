# EdgeFlow Terminal Pro — Live Test V1.3 Dual Version

This package keeps your **current live version** available on:

- `/`
- `/dashboard`

And adds a separate **experimental test version** on:

- `/test`

This lets you compare the current engine with a stricter test engine without losing the existing version.

## What is new in this package

### Current version stays unchanged
- Main live dashboard remains on `/`
- Same general workflow as before

### New test version added
- Experimental dashboard on `/test`
- Separate API endpoint: `/api/signals-test`
- Test engine is more selective and is designed for comparison
- Root/live and `/test` can run side by side

## Main idea of `/test`
The test version is meant to compare a stricter strategy engine against the current one.
It focuses more on:

- pullback continuation
- breakout follow-through
- cleaner confirmation
- reducing first-spike entries

## Main features

- Live dashboard
- TwelveData API support
- Current live engine on `/`
- Experimental test engine on `/test`
- Market Mode Detector
- Risk / reward filter
- Trade Manager
- Signal database and review page
- Review page: `/review`

## Commands

```text
TRADE NOW BUY
TRADE NOW SELL
SCALP NOW BUY
SCALP NOW SELL
PLAN ONLY — DO NOT ENTER
NO TRADE
MOVE MISSED — DO NOT CHASE
```

## Local run

```bash
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Then open:

- `http://127.0.0.1:8000/` → current version
- `http://127.0.0.1:8000/test` → test version
- `http://127.0.0.1:8000/review` → signal review

## Railway

This package includes Dockerfile and railway.json.

### Required env variable

```text
TWELVEDATA_API_KEY=your_key_here
```

### Optional

```text
EDGEFLOW_REFRESH_SECONDS=30
EDGEFLOW_MODE=live_test
```

## Deployment notes

You do **not** need a second Railway project.
Just redeploy this package over the current app.

After deploy:
- your current dashboard remains on `/`
- the new experimental version will be available on `/test`

## Important warning

This is still a testing system, not a guaranteed-profit system.
Use demo or very small live risk only.


## V1.4 Local Time Tracking

Added local device time tracking to help detect signal delay.

Each signal card now shows:
- Strategy time on this device
- First seen on this device
- Delay now in seconds
- Last refresh on this device

How it works:
- Server saves the signal time in UTC.
- Browser converts it to the device local time.
- Phone shows phone time.
- Laptop shows laptop time.

Routes:
- `/` or `/dashboard` = current live version
- `/test` = experimental test version
- `/testb` = test version with local-time/delay tracking label
- `/review` = signal database review
