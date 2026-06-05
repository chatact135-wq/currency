# Railway Deploy Steps — V1.5 uvicorn compatible

This version fixes:

```text
The executable `uvicorn` could not be found.
```

Fixes:
- Added `uvicorn` to requirements.
- Added `asgiref`.
- Wrapped Flask as an ASGI app using `WsgiToAsgi`.
- Dockerfile starts with `python -m uvicorn app:app`.

## Important Railway setting

If Railway has an old Start Command, set it to:

```bash
python -m uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers
```

Or remove the custom Start Command and let Dockerfile CMD run.

## Test

After deploy:

```text
/health
```

Expected:

```json
{"status":"ok","app":"EdgeFlow Terminal Pro Backtest Lab V1"}
```
