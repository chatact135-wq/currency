# Railway Deploy Steps — V1.2 mise fix

This package fixes the Railway build error:

```text
mise ERROR Failed to install core:python@3.11.9
No GitHub artifact attestations found
```

Fixes included:
- Removed `runtime.txt` that forced exact Python 3.11.9.
- Added `mise.toml` with `python.github_attestations = false`.
- Added `nixpacks.toml` to use Python 3.11 and start with gunicorn.
- Kept `railway.json` start command.

After deploying, test:

```text
/health
```

Expected:

```json
{"status":"ok","app":"EdgeFlow Terminal Pro Backtest Lab V1"}
```

If Railway still uses cache:
1. Go to Railway project.
2. Settings or Deployments.
3. Trigger redeploy with cache cleared if available.
4. Or create a new Railway service from this ZIP/repo.
