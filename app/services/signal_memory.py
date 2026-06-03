
from datetime import datetime, timezone, timedelta
from app.models import SignalMemory
from app.services.market import ASSETS, normalize


def _now():
    return datetime.now(timezone.utc)


def _num(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _ttl_minutes(result):
    news = result.get("news") or {}
    final_action = str(result.get("final_action") or "").upper()
    stage = str(result.get("stage") or "").upper()
    # News/fast move plans expire faster.
    if news.get("mode") in ["NEWS_WAIT", "POST_NEWS_IMPULSE"]:
        return 10
    # Active scalp should be fresh.
    if "ACTIVE" in final_action or "ACTIVE" in stage:
        return 15
    # Watch/setup stays valid a little longer but not forever.
    return 25


def _round_entry(sym, entry):
    if entry is None:
        return "none"
    pip = ASSETS[sym]["pip"]
    # Use a 2 pip bucket for forex, practical bucket for gold/other.
    bucket = 2 * pip if pip == 0.0001 else 1.0 if pip >= 0.1 else 0.05
    return str(round(round(float(entry) / bucket) * bucket, 5 if pip == 0.0001 else 2))


def _build_key(sym, direction, entry):
    return f"{sym}:{direction}:{_round_entry(sym, entry)}"


def _status(now, expires_at):
    if expires_at and now >= expires_at:
        return "EXPIRED"
    return "ACTIVE"


def apply_signal_memory(db, result):
    if result.get("status") != "live":
        return result

    sym = normalize(result.get("asset"))
    mm = result.get("market_map") or {}
    cs = mm.get("current_state") or {}
    tm = mm.get("trade_map") or {}
    direction = cs.get("bias") or result.get("master_bias") or "NEUTRAL"
    entry = _num(tm.get("aggressive_entry"))
    safe_entry = _num(tm.get("safe_entry"))
    cancel = _num(tm.get("cancel_level"))

    if direction not in ["BUY", "SELL"] or entry is None:
        result["signal_memory"] = {
            "status": "NO_ACTIVE_SIGNAL",
            "message": "No clear trade plan to expire.",
            "expiry_reset_on_refresh": False
        }
        return result

    now = _now()
    ttl = _ttl_minutes(result)
    key = _build_key(sym, direction, entry)
    existing = db.query(SignalMemory).filter(SignalMemory.asset == sym).first()

    if existing and existing.signal_key == key:
        existing.last_seen_at = now
        existing.updated_at = now
        existing.status = _status(now, existing.expires_at)
        db.commit()
        mem = existing
    else:
        # New direction or materially different trigger creates a new expiry anchor.
        if not existing:
            existing = SignalMemory(asset=sym)
            db.add(existing)
        existing.direction = direction
        existing.entry = entry
        existing.safe_entry = safe_entry
        existing.cancel_level = cancel
        existing.signal_key = key
        existing.status = "ACTIVE"
        existing.ttl_minutes = ttl
        existing.created_at = now
        existing.expires_at = now + timedelta(minutes=ttl)
        existing.last_seen_at = now
        existing.updated_at = now
        existing.reason = "New signal anchor created. Refresh will not reset expiry."
        db.commit()
        mem = existing

    seconds_left = int((mem.expires_at - now).total_seconds()) if mem.expires_at else None
    if seconds_left is not None and seconds_left < 0:
        seconds_left = 0
    expired = mem.status == "EXPIRED"

    result["signal_memory"] = {
        "status": mem.status,
        "direction": mem.direction,
        "entry": mem.entry,
        "safe_entry": mem.safe_entry,
        "cancel_level": mem.cancel_level,
        "signal_key": mem.signal_key,
        "created_at": mem.created_at.isoformat() if mem.created_at else None,
        "expires_at": mem.expires_at.isoformat() if mem.expires_at else None,
        "seconds_left": seconds_left,
        "minutes_left": round(seconds_left / 60, 1) if seconds_left is not None else None,
        "ttl_minutes": mem.ttl_minutes,
        "expiry_reset_on_refresh": False,
        "message": "Expiry is persistent. Refreshing the page/API will not reset it."
    }

    if expired:
        result["final_action"] = "SIGNAL EXPIRED - RECALCULATE / WAIT"
        result["entry_permission"] = "NO_ENTRY"
        result["warning"] = "Signal expired. Do not use this old trigger unless a new trigger/direction appears."
        fd = result.get("final_decision") or {}
        if fd:
            fd["final_action"] = "SIGNAL EXPIRED"
            fd["command"] = "WAIT - OLD SIGNAL EXPIRED"
            fd["entry_permission"] = "NO_ENTRY"
            result["final_decision"] = fd
    return result
