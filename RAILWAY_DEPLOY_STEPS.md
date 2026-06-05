# Railway Deploy Steps — V1.4 Docker fixed

This version avoids the Railway `mise` / `pip not found` problem completely by using an official Docker image:

```dockerfile
FROM python:3.11-slim
```

So Python and pip are available normally.

## Fixed errors

Previous errors:
```text
No GitHub artifact attestations found for python@3.11.9
pip: command not found
No module named pip
```

V1.4 fix:
- Removed `runtime.txt`
- Removed `mise.toml`
- Removed `nixpacks.toml`
- Added `Dockerfile`
- `railway.json` now uses Dockerfile builder

## Deploy

Upload/deploy this package to Railway.

After deploy, test:

```text
/health
```

Expected:

```json
{"status":"ok","app":"EdgeFlow Terminal Pro Backtest Lab V1"}
```

If Railway still uses Nixpacks, create a new Railway service from this package so it detects the Dockerfile cleanly.
