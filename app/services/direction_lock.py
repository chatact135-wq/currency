
import os
from datetime import datetime, timezone

_LOCKS = {}

def _now():
    return datetime.now(timezone.utc)

def _num(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default

def _upper(v):
    return str(v or "").upper()

def _direction_from_result(result):
    tr = result.get("trade_readiness") or {}
    d = _upper(tr.get("direction"))
    if d in ["BUY","SELL"]:
        return d
    mm = result.get("market_map") or {}
    cs = mm.get("current_state") or {}
    b = _upper(cs.get("bias") or result.get("master_bias") or result.get("final_action"))
    if "BUY" in b and "SELL" not in b:
        return "BUY"
    if "SELL" in b and "BUY" not in b:
        return "SELL"
    probs = result.get("probabilities") or {}
    up, down = _num(probs.get("up")), _num(probs.get("down"))
    if up - down >= 10:
        return "BUY"
    if down - up >= 10:
        return "SELL"
    return "NEUTRAL"

def _score_for_direction(result, direction):
    probs = result.get("probabilities") or {}
    up, down = _num(probs.get("up")), _num(probs.get("down"))
    readiness = _num((result.get("trade_readiness") or {}).get("score"))
    if direction == "BUY":
        return readiness + max(0, up-down)
    if direction == "SELL":
        return readiness + max(0, down-up)
    return 0

def apply_direction_lock(result):
    if result.get("status") != "live":
        return result

    asset = result.get("asset") or "UNKNOWN"
    direction = _direction_from_result(result)
    now = _now()
    lock_seconds = int(os.getenv("DIRECTION_LOCK_SECONDS", "45"))
    flip_score_gap = float(os.getenv("DIRECTION_FLIP_SCORE_GAP", "18"))

    if direction == "NEUTRAL":
        result["direction_lock"] = {
            "status":"NO_LOCK","locked_direction":None,"current_direction":"NEUTRAL",
            "simple_message":"Direction is not clear. Do not buy or sell now.","flip_blocked":False
        }
        return result

    score = _score_for_direction(result, direction)
    mem = _LOCKS.get(asset)

    if not mem:
        _LOCKS[asset] = {
            "asset":asset,"locked_direction":direction,"locked_at":now,"last_seen_at":now,
            "score":score,"opposite_candidate":None,"opposite_first_seen_at":None,
            "opposite_score":0,"flip_count":0,"status":"LOCKED"
        }
        result["direction_lock"] = {
            "status":"LOCKED","locked_direction":direction,"current_direction":direction,
            "seconds_locked":0,
            "simple_message":f"{direction} idea is locked for now. The system will not change direction immediately.",
            "flip_blocked":False
        }
        return result

    locked = mem.get("locked_direction")
    seconds_locked = int((now - mem.get("locked_at", now)).total_seconds())

    if direction == locked:
        mem["last_seen_at"] = now
        mem["score"] = score
        mem["opposite_candidate"] = None
        mem["opposite_first_seen_at"] = None
        mem["opposite_score"] = 0
        mem["status"] = "LOCKED"
        result["direction_lock"] = {
            "status":"LOCKED","locked_direction":locked,"current_direction":direction,
            "seconds_locked":seconds_locked,
            "simple_message":f"{locked} idea is still the main idea.",
            "flip_blocked":False
        }
        return result

    # opposite direction appeared
    if mem.get("opposite_candidate") != direction or mem.get("opposite_first_seen_at") is None:
        mem["opposite_candidate"] = direction
        mem["opposite_first_seen_at"] = now
        mem["opposite_score"] = score
        opposite_seconds = 0
    else:
        opposite_seconds = int((now - mem["opposite_first_seen_at"]).total_seconds())
        mem["opposite_score"] = score

    score_gap = score - _num(mem.get("score"))
    can_flip = opposite_seconds >= lock_seconds and score_gap >= flip_score_gap

    if can_flip:
        old = locked
        mem["locked_direction"] = direction
        mem["locked_at"] = now
        mem["last_seen_at"] = now
        mem["score"] = score
        mem["opposite_candidate"] = None
        mem["opposite_first_seen_at"] = None
        mem["opposite_score"] = 0
        mem["flip_count"] = mem.get("flip_count",0)+1
        mem["status"] = "FLIPPED_CONFIRMED"
        result["direction_lock"] = {
            "status":"FLIPPED_CONFIRMED","locked_direction":direction,"previous_direction":old,
            "current_direction":direction,"seconds_waited":opposite_seconds,"score_gap":round(score_gap,1),
            "simple_message":f"Direction changed to {direction} because it stayed strong for enough time.",
            "flip_blocked":False
        }
        return result

    # block flip
    result["direction_lock"] = {
        "status":"FLIP_BLOCKED_WAIT_STABILITY",
        "locked_direction":locked,"current_direction":direction,
        "opposite_seconds":opposite_seconds,"required_seconds":lock_seconds,
        "score_gap":round(score_gap,1),"required_score_gap":flip_score_gap,
        "simple_message":f"The system tried to change to {direction}, but it is too early. Wait until it stays strong for {lock_seconds} seconds.",
        "flip_blocked":True
    }
    result["direction_unstable"] = True
    result["final_action"] = "DIRECTION UNSTABLE - WAIT"
    result["entry_permission"] = "NO_ENTRY"
    result["warning"] = f"Direction changed too quickly. Old idea: {locked}. New idea: {direction}. Wait for stability."

    tr = result.get("trade_readiness") or {}
    if tr:
        tr["state"] = "DIRECTION UNSTABLE - WAIT"
        tr["headline"] = "Direction changed too quickly. Wait before choosing buy or sell."
        tr["command"] = "WAIT"
        tr["direction_lock_note"] = result["direction_lock"]["simple_message"]
        result["trade_readiness"] = tr

    fd = result.get("final_decision") or {}
    if fd:
        fd["final_action"] = "DIRECTION UNSTABLE - WAIT"
        fd["command"] = "WAIT"
        fd["entry_permission"] = "NO_ENTRY"
        fd["summary"] = "Direction changed too quickly. Wait for stability."
        result["final_decision"] = fd

    return result

def direction_lock_report():
    out = []
    now = _now()
    for asset, mem in _LOCKS.items():
        out.append({
            "asset":asset,
            "locked_direction":mem.get("locked_direction"),
            "status":mem.get("status"),
            "locked_at":mem.get("locked_at").isoformat() if mem.get("locked_at") else None,
            "seconds_locked":int((now - mem.get("locked_at", now)).total_seconds()),
            "opposite_candidate":mem.get("opposite_candidate"),
            "opposite_first_seen_at":mem.get("opposite_first_seen_at").isoformat() if mem.get("opposite_first_seen_at") else None,
            "score":mem.get("score"),
            "opposite_score":mem.get("opposite_score"),
            "flip_count":mem.get("flip_count",0)
        })
    return {"locks":out}
