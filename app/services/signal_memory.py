
from datetime import datetime, timezone, timedelta
from app.services.market import ASSETS, normalize

_MEMORY = {}

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
    if news.get("mode") in ["NEWS_WAIT", "POST_NEWS_IMPULSE"]:
        return 10
    if "ACTIVE" in final_action or "ACTIVE" in stage:
        return 15
    return 25

def _round_entry(sym, entry):
    if entry is None:
        return "none"
    pip = ASSETS[sym]["pip"]
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
            "expiry_reset_on_refresh": False,
            "storage": "server_memory_safe"
        }
        return result

    now = _now()
    ttl = _ttl_minutes(result)
    key = _build_key(sym, direction, entry)
    mem = _MEMORY.get(sym)

    if mem and mem.get("signal_key") == key:
        mem["last_seen_at"] = now
        mem["updated_at"] = now
        mem["status"] = _status(now, mem.get("expires_at"))
    else:
        mem = {
            "asset": sym,
            "direction": direction,
            "entry": entry,
            "safe_entry": safe_entry,
            "cancel_level": cancel,
            "signal_key": key,
            "status": "ACTIVE",
            "ttl_minutes": ttl,
            "created_at": now,
            "expires_at": now + timedelta(minutes=ttl),
            "last_seen_at": now,
            "updated_at": now,
            "reason": "New signal anchor created. Refresh will not reset expiry."
        }
        _MEMORY[sym] = mem

    seconds_left = int((mem["expires_at"] - now).total_seconds()) if mem.get("expires_at") else None
    if seconds_left is not None and seconds_left < 0:
        seconds_left = 0
    expired = mem.get("status") == "EXPIRED"

    result["signal_memory"] = {
        "status": mem.get("status"),
        "direction": mem.get("direction"),
        "entry": mem.get("entry"),
        "safe_entry": mem.get("safe_entry"),
        "cancel_level": mem.get("cancel_level"),
        "signal_key": mem.get("signal_key"),
        "created_at": mem.get("created_at").isoformat() if mem.get("created_at") else None,
        "expires_at": mem.get("expires_at").isoformat() if mem.get("expires_at") else None,
        "seconds_left": seconds_left,
        "minutes_left": round(seconds_left / 60, 1) if seconds_left is not None else None,
        "ttl_minutes": mem.get("ttl_minutes"),
        "expiry_reset_on_refresh": False,
        "storage": "server_memory_safe",
        "message": "Expiry is persistent during server runtime. Refreshing page/API will not reset it."
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

def memory_report():
    out = []
    now = _now()
    for sym, mem in _MEMORY.items():
        seconds_left = int((mem["expires_at"] - now).total_seconds()) if mem.get("expires_at") else None
        if seconds_left is not None and seconds_left < 0:
            seconds_left = 0
        out.append({
            "asset": sym,
            "direction": mem.get("direction"),
            "entry": mem.get("entry"),
            "status": _status(now, mem.get("expires_at")),
            "created_at": mem.get("created_at").isoformat() if mem.get("created_at") else None,
            "expires_at": mem.get("expires_at").isoformat() if mem.get("expires_at") else None,
            "seconds_left": seconds_left,
            "minutes_left": round(seconds_left/60,1) if seconds_left is not None else None,
            "signal_key": mem.get("signal_key"),
            "storage": "server_memory_safe"
        })
    return {"signals": out}
