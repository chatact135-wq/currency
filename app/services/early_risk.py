
import os
from datetime import datetime, timezone
from app.services.market import ASSETS, normalize

_EARLY_RISK_MEMORY = {}

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

def _pips(sym, a, b):
    try:
        return abs(float(a)-float(b)) / ASSETS[sym]["pip"]
    except Exception:
        return None

def _levels(result):
    et = result.get("early_trigger") or {}
    tr = result.get("trade_readiness") or {}
    mm = result.get("market_map") or {}
    tm = mm.get("trade_map") or {}
    return {
        "entry": _num(et.get("price") or result.get("price")),
        "early_price": _num(et.get("early_price") or tr.get("entry") or tm.get("aggressive_entry")),
        "confirm": _num(et.get("confirm_price") or tr.get("safe_entry") or tm.get("safe_entry")),
        "invalidation": _num(et.get("invalidation") or tr.get("cancel_level") or tm.get("cancel_level") or tr.get("stop_loss") or tm.get("stop_loss")),
        "tp1": _num(tr.get("tp1") or tm.get("tp1_partial_close")),
        "tp2": _num(tr.get("tp2") or tm.get("tp2")),
    }

def _pick_target(direction, entry, tp1, tp2):
    # Prefer TP1 if it is in correct direction and not behind price, else TP2.
    if entry is None:
        return None
    if direction == "BUY":
        if tp1 is not None and tp1 > entry:
            return tp1
        if tp2 is not None and tp2 > entry:
            return tp2
    if direction == "SELL":
        if tp1 is not None and tp1 < entry:
            return tp1
        if tp2 is not None and tp2 < entry:
            return tp2
    return None

def apply_early_risk_controller(result):
    if result.get("status") != "live":
        return result

    sym = normalize(result.get("asset"))
    early = result.get("early_trigger") or {}
    direction = _upper(early.get("direction"))

    if direction not in ["BUY","SELL"]:
        result["early_risk"] = {
            "state": "NO EARLY TRADE",
            "allowed": False,
            "simple_message": "No early buy or sell now.",
            "reasons": ["No early direction."]
        }
        return result

    min_reward = float(os.getenv("EARLY_MIN_REWARD_PIPS_FX","5"))
    max_risk = float(os.getenv("EARLY_MAX_RISK_PIPS_FX","4"))
    min_rr = float(os.getenv("EARLY_MIN_RR","1.2"))
    max_late = float(os.getenv("EARLY_MAX_LATE_DISTANCE_PIPS","3.5"))
    require_stable = os.getenv("EARLY_REQUIRE_STABLE_DIRECTION","true").lower() in ["1","true","yes","on"]

    lv = _levels(result)
    entry = lv["entry"]
    invalid = lv["invalidation"]
    target = _pick_target(direction, entry, lv["tp1"], lv["tp2"])

    reasons = []
    allowed = True

    # Early trigger itself must be detected.
    if not early.get("detected"):
        allowed = False
        reasons.append("Early signal is not detected.")

    reward = _pips(sym, entry, target) if entry is not None and target is not None else None
    risk = _pips(sym, entry, invalid) if entry is not None and invalid is not None else None
    rr = (reward / risk) if reward is not None and risk and risk > 0 else None

    if reward is None:
        allowed = False
        reasons.append("No valid target found.")
    elif reward < min_reward:
        allowed = False
        reasons.append(f"Target is too close: {round(reward,1)} pips. Need at least {min_reward} pips.")

    if risk is None:
        allowed = False
        reasons.append("No valid stop/cancel level found.")
    elif risk > max_risk:
        allowed = False
        reasons.append(f"Risk is too big: {round(risk,1)} pips. Max allowed is {max_risk} pips.")

    if rr is None:
        allowed = False
        reasons.append("Reward/risk cannot be calculated.")
    elif rr < min_rr:
        allowed = False
        reasons.append(f"Reward/risk is weak: {round(rr,2)}. Need at least {min_rr}.")

    # Price too far from early price = late
    late_distance = None
    if entry is not None and lv["early_price"] is not None:
        late_distance = _pips(sym, entry, lv["early_price"])
        if late_distance is not None and late_distance > max_late:
            allowed = False
            reasons.append(f"Price is already late: {round(late_distance,1)} pips from early area.")

    # Direction lock / unstable gate
    dl = result.get("direction_lock") or {}
    if require_stable and (result.get("direction_unstable") or dl.get("flip_blocked")):
        allowed = False
        reasons.append("Direction changed too quickly. Wait for stability.")

    # Regime/news gate
    regime = result.get("regime_guard") or {}
    if regime.get("mode") == "BLOCK_TRADE":
        allowed = False
        reasons.append("Market condition blocks trade.")

    news = result.get("news") or {}
    if news.get("mode") == "NEWS_WAIT":
        allowed = False
        reasons.append("News is too close. Early trade blocked.")

    state = f"EARLY {direction} ALLOWED" if allowed else f"EARLY {direction} BLOCKED"

    if allowed:
        simple = f"Early {direction.lower()} is allowed with small risk. This is faster than safe entry, but still higher risk."
        action = f"{direction} early only with small lot. Stop/cancel near {invalid}. First target near {target}."
    else:
        simple = f"Early {direction.lower()} is blocked because risk is not good enough."
        action = "Do not enter early. Wait for better price or safe confirmation."

    report = {
        "state": state,
        "allowed": allowed,
        "direction": direction,
        "entry": entry,
        "target": target,
        "invalidation": invalid,
        "reward_pips": round(reward,1) if reward is not None else None,
        "risk_pips": round(risk,1) if risk is not None else None,
        "rr": round(rr,2) if rr is not None else None,
        "late_distance_pips": round(late_distance,1) if late_distance is not None else None,
        "min_reward_pips": min_reward,
        "max_risk_pips": max_risk,
        "min_rr": min_rr,
        "simple_message": simple,
        "action": action,
        "reasons": reasons,
        "time": _now().isoformat()
    }

    result["early_risk"] = report
    _EARLY_RISK_MEMORY[sym] = report

    # If allowed, display a clear early-entry state, but keep it separate from safe entry.
    if allowed:
        result["final_action"] = state + " - SMALL RISK ONLY"
        result["entry_permission"] = "EARLY_ENTRY_ALLOWED_SMALL_RISK"
        fd = result.get("final_decision") or {}
        if fd:
            fd["final_action"] = state + " - SMALL RISK ONLY"
            fd["command"] = state
            fd["entry_permission"] = "EARLY_ENTRY_ALLOWED_SMALL_RISK"
            fd["summary"] = simple
            result["final_decision"] = fd
    else:
        # If early trigger wanted entry, make sure dashboard says blocked.
        if early.get("detected"):
            result["warning"] = "Early entry blocked: " + " | ".join(reasons)

    return result

def early_risk_report():
    return {"early_risk": list(_EARLY_RISK_MEMORY.values())}
