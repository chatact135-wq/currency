# Railway Deploy Steps — V1.3 pip fixed

This package fixes:

```text
/bin/bash: line 1: pip: command not found
```

Fix:
- `nixpacks.toml` now uses `python -m pip`, not `pip`.
- Start command uses `python -m gunicorn`.
- `runtime.txt` removed.
- `mise.toml` disables Python GitHub attestation verification.

After deploy, test:

```text
/health
```

Expected:

```json
{"status":"ok","app":"EdgeFlow Terminal Pro Backtest Lab V1"}
```

If Railway still shows old build commands, clear cache or create a new Railway service from this package.
