
from datetime import datetime, timezone

_USAGE = {
    "total": 0,
    "by_key": {},
    "last_refresh": {},
    "refresh_count": 0,
    "started_at": datetime.now(timezone.utc).isoformat()
}

def track(key, count=1):
    try:
        count = int(count)
    except Exception:
        count = 1
    _USAGE["total"] += count
    _USAGE["by_key"][key] = _USAGE["by_key"].get(key, 0) + count
    return count

def begin_refresh(label="signals"):
    _USAGE["refresh_count"] += 1
    _USAGE["last_refresh"] = {
        "label": label,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "calls": {},
        "total": 0
    }

def track_refresh(key, count=1):
    track(key, count)
    lr = _USAGE.get("last_refresh") or {}
    if lr:
        lr["calls"][key] = lr["calls"].get(key, 0) + count
        lr["total"] = lr.get("total", 0) + count
    return count

def estimate(refresh_seconds=10):
    lr = _USAGE.get("last_refresh") or {}
    per_refresh = lr.get("total", 0)
    if not refresh_seconds or refresh_seconds <= 0:
        refresh_seconds = 10
    per_minute = per_refresh * (60 / refresh_seconds)
    per_hour = per_minute * 60
    per_day = per_hour * 24
    return {
        "per_refresh": per_refresh,
        "refresh_seconds": refresh_seconds,
        "estimated_per_minute": round(per_minute, 1),
        "estimated_per_hour": round(per_hour, 1),
        "estimated_per_day": round(per_day, 1)
    }

def report(refresh_seconds=10):
    return {
        "started_at": _USAGE["started_at"],
        "refresh_count": _USAGE["refresh_count"],
        "total_calls_since_start": _USAGE["total"],
        "by_key_since_start": _USAGE["by_key"],
        "last_refresh": _USAGE.get("last_refresh") or {},
        "estimate": estimate(refresh_seconds),
        "note": "Internal estimate. Provider billing may differ if retries/errors are counted differently."
    }
