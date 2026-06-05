# EdgeFlow Terminal Pro Backtest Lab V1.7 — Docker CMD Only

This version fixes Railway override issues.

## Important change

`railway.json` no longer contains `deploy.startCommand`.

So Railway must use the Dockerfile CMD:

```bash
sh -c 'echo "Starting EdgeFlow on PORT=${PORT:-8000}" && python -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers'
```

## Deploy instructions

1. Deploy this package.
2. In Railway service settings, remove any custom Start Command.
3. Railway should show the Start Command value is no longer set by `railway.json`.
4. Open Deploy Logs and look for:

```text
Starting EdgeFlow on PORT=...
Uvicorn running on http://0.0.0.0:...
```

5. Test:

```text
/health
/debug
```

If it still fails, send the deploy logs line starting from "Starting EdgeFlow..." or the first red traceback.
