
import os
from datetime import datetime, timezone
from app.services.market import ASSETS, normalize

_LOCKS = {}

def _now():
    return datetime.now(timezone.utc)

def _num(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def _upper(v):
    return str(v or "").upper()

def _moves(sym, a, b):
    try:
        return abs(float(a) - float(b)) / (ASSETS[sym]["pip"] / 10)
    except Exception:
        return None

def _direction(result):
    for obj in [
        result.get("master_decision") or {},
        result.get("fast_start") or {},
        result.get("early_risk") or {},
        result.get("early_trigger") or {},
        result.get("price_position") or {},
        result.get("trade_readiness") or {},
    ]:
        d = _upper(obj.get("direction"))
        if d in ["BUY", "SELL"]:
            return d
        state = _upper(obj.get("state"))
        if "BUY" in state and "SELL" not in state:
            return "BUY"
        if "SELL" in state and "BUY" not in state:
            return "SELL"
    fa = _upper(result.get("final_action"))
    if "BUY" in fa and "SELL" not in fa:
        return "BUY"
    if "SELL" in fa and "BUY" not in fa:
        return "SELL"
    probs = result.get("probabilities") or {}
    up = _num(probs.get("up")) or 0
    down = _num(probs.get("down")) or 0
    if up - down >= 10:
        return "BUY"
    if down - up >= 10:
        return "SELL"
    return "NEUTRAL"

def _candidate_trigger(result, direction):
    mm = result.get("market_map") or {}
    sw = mm.get("switch_levels") or {}
    pp = result.get("price_position") or {}
    tr = result.get("trade_readiness") or {}
    tm = mm.get("trade_map") or {}
    if direction == "BUY":
        return _num(sw.get("buy_switch") or pp.get("confirmation_level") or tr.get("safe_entry") or tm.get("safe_entry"))
    if direction == "SELL":
        return _num(sw.get("sell_switch") or pp.get("confirmation_level") or tr.get("safe_entry") or tm.get("safe_entry"))
    return None

def _cancel_level(result):
    tr = result.get("trade_readiness") or {}
    mm = result.get("market_map") or {}
    tm = mm.get("trade_map") or {}
    return _num(tr.get("cancel_level") or tm.get("cancel_level") or tr.get("stop_loss") or tm.get("stop_loss"))

def _crossed(direction, price, trigger):
    if price is None or trigger is None:
        return False
    return price >= trigger if direction == "BUY" else price <= trigger

def _cancel_hit(direction, price, cancel):
    if price is None or cancel is None:
        return False
    return price <= cancel if direction == "BUY" else price >= cancel

def apply_trigger_lock(result):
    if result.get("status") != "live":
        return result

    sym = normalize(result.get("asset"))
    price = _num(result.get("price"))
    direction = _direction(result)
    candidate = _candidate_trigger(result, direction)
    cancel = _cancel_level(result)
    now = _now()

    lock_seconds = int(os.getenv("TRIGGER_LOCK_SECONDS", "300"))
    hold_seconds = int(os.getenv("TRIGGER_HOLD_SECONDS", "10"))
    tolerance_moves = float(os.getenv("TRIGGER_TOUCH_TOLERANCE_MOVES", "2"))

    if direction not in ["BUY", "SELL"] or price is None or candidate is None:
        result["trigger_lock"] = {
            "state": "NO TRIGGER LOCK",
            "simple_message": "No clear trigger to lock.",
            "direction": direction
        }
        return result

    lock = _LOCKS.get(sym)
    if lock:
        age = int((now - lock["created_at"]).total_seconds())
        expired = age > lock_seconds
        opposite = lock["direction"] != direction
        failed = _cancel_hit(lock["direction"], price, lock.get("cancel"))
        if expired or opposite or failed:
            _LOCKS.pop(sym, None)
            lock = None

    if not lock:
        lock = {
            "asset": sym,
            "direction": direction,
            "trigger": candidate,
            "cancel": cancel,
            "created_at": now,
            "reached_at": None,
            "confirmed_at": None,
            "state": f"{direction} TRIGGER LOCKED",
            "blocked_moves": 0
        }
        _LOCKS[sym] = lock

    # Do not chase price:
    # BUY trigger is not allowed to move higher. SELL trigger is not allowed to move lower.
    if candidate is not None:
        if lock["direction"] == "BUY" and candidate < lock["trigger"]:
            lock["trigger"] = candidate
        elif lock["direction"] == "SELL" and candidate > lock["trigger"]:
            lock["trigger"] = candidate
        elif (lock["direction"] == "BUY" and candidate > lock["trigger"]) or (lock["direction"] == "SELL" and candidate < lock["trigger"]):
            lock["blocked_moves"] += 1

    trigger = lock["trigger"]
    crossed = _crossed(lock["direction"], price, trigger)
    near_moves = _moves(sym, price, trigger)
    near = near_moves is not None and near_moves <= tolerance_moves

    if crossed or near:
        if lock["reached_at"] is None:
            lock["reached_at"] = now
            lock["state"] = "TRIGGER REACHED - WAIT HOLD"
        else:
            held = int((now - lock["reached_at"]).total_seconds())
            if held >= hold_seconds and crossed:
                lock["confirmed_at"] = now
                lock["state"] = f"{lock['direction']} LOCK CONFIRMED"
    else:
        if lock["reached_at"] is not None and not crossed:
            lock["reached_at"] = None
            lock["state"] = f"{lock['direction']} TRIGGER LOCKED"

    age = int((now - lock["created_at"]).total_seconds())
    hold_elapsed = int((now - lock["reached_at"]).total_seconds()) if lock["reached_at"] else 0
    dist = _moves(sym, price, trigger)

    if lock["state"].endswith("CONFIRMED"):
        simple = f"{lock['direction']} confirmed at locked trigger {trigger}. The trigger did not move away."
    elif lock["state"] == "TRIGGER REACHED - WAIT HOLD":
        simple = f"Price reached locked trigger {trigger}. Wait hold confirmation."
    else:
        simple = f"{lock['direction']} trigger locked at {trigger}. It will not chase price every refresh."

    result["trigger_lock"] = {
        "state": lock["state"],
        "direction": lock["direction"],
        "locked_trigger": trigger,
        "new_candidate_trigger": candidate,
        "cancel": lock.get("cancel"),
        "price": price,
        "distance_moves": round(dist, 1) if dist is not None else None,
        "expires_in_seconds": max(0, lock_seconds - age),
        "hold_elapsed_seconds": hold_elapsed,
        "hold_seconds_required": hold_seconds,
        "moving_trigger_blocked_count": lock["blocked_moves"],
        "simple_message": simple,
        "note": "BUY trigger will not keep moving higher; SELL trigger will not keep moving lower.",
        "time": now.isoformat()
    }

    if lock["state"].endswith("CONFIRMED"):
        result["entry_permission"] = "TRIGGER_LOCK_CONFIRMED"
        result["final_action"] = f"{lock['direction']} LOCK CONFIRMED"
        fd = result.get("final_decision") or {}
        if fd:
            fd["final_action"] = f"{lock['direction']} LOCK CONFIRMED"
            fd["command"] = f"{lock['direction']} LOCK CONFIRMED"
            fd["entry_permission"] = "TRIGGER_LOCK_CONFIRMED"
            fd["summary"] = simple
            result["final_decision"] = fd

    return result

def trigger_lock_report():
    out = []
    now = _now()
    for sym, lock in _LOCKS.items():
        out.append({
            "asset": sym,
            "direction": lock.get("direction"),
            "trigger": lock.get("trigger"),
            "cancel": lock.get("cancel"),
            "state": lock.get("state"),
            "age_seconds": int((now - lock.get("created_at", now)).total_seconds()),
            "moving_trigger_blocked_count": lock.get("blocked_moves", 0),
        })
    return {"trigger_locks": out}
