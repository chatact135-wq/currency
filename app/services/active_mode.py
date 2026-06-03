
import os

def _num(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default

def _upper(v):
    return str(v or "").upper()

def _direction(result):
    mm = result.get("market_map") or {}
    cs = mm.get("current_state") or {}
    bias = _upper(cs.get("bias") or result.get("master_bias") or result.get("final_action"))
    if "BUY" in bias and "SELL" not in bias:
        return "BUY"
    if "SELL" in bias and "BUY" not in bias:
        return "SELL"
    probs = result.get("probabilities") or {}
    up = _num(probs.get("up"))
    down = _num(probs.get("down"))
    if up - down >= 10:
        return "BUY"
    if down - up >= 10:
        return "SELL"
    return "NEUTRAL"

def _score(result, direction):
    score = 0
    reasons = []

    if result.get("data_fresh", True):
        score += 15
        reasons.append("Data fresh +15")
    else:
        score -= 40
        reasons.append("Data stale -40")

    news = result.get("news") or {}
    if news.get("mode") == "NEWS_WAIT":
        score -= 25
        reasons.append("News wait -25")
    elif news.get("mode") == "POST_NEWS_IMPULSE":
        score -= 10
        reasons.append("Post-news caution -10")
    else:
        score += 10
        reasons.append("News okay +10")

    probs = result.get("probabilities") or {}
    up = _num(probs.get("up"))
    down = _num(probs.get("down"))
    edge = (up - down) if direction == "BUY" else (down - up) if direction == "SELL" else 0

    if edge >= 35:
        score += 25
        reasons.append("Strong probability edge +25")
    elif edge >= 20:
        score += 18
        reasons.append("Good probability edge +18")
    elif edge >= 10:
        score += 10
        reasons.append("Small probability edge +10")
    else:
        reasons.append("Weak probability edge +0")

    adaptive = _num(result.get("adaptive_edge"))
    if adaptive > 0:
        score += 10
        reasons.append("Adaptive edge positive +10")
    elif adaptive < 0:
        score -= 10
        reasons.append("Adaptive edge negative -10")

    tstate = result.get("trigger_state") or {}
    state = _upper(tstate.get("state"))
    perm = _upper(tstate.get("entry_permission"))
    if "ENTRY_ALLOWED" in perm:
        score += 30
        reasons.append("Trigger active +30")
    elif state == "BROKEN_WAIT_HOLD":
        score += 18
        reasons.append("Trigger broken, wait hold +18")
    elif state == "NOT_REACHED":
        score += 8
        reasons.append("Trigger not reached yet +8")
    elif state == "TOO_LATE_DO_NOT_CHASE":
        score -= 35
        reasons.append("Too late / no chase -35")
    elif state == "FAILED_CANCEL":
        score -= 50
        reasons.append("Trigger failed -50")

    regime = result.get("regime_guard") or {}
    mode = _upper(regime.get("mode"))
    if mode == "BLOCK_TRADE":
        score -= 50
        reasons.append("Regime block -50")
    elif mode == "REDUCE_RISK":
        score -= 20
        reasons.append("Regime reduce risk -20")
    elif mode == "CAUTION":
        score -= 8
        reasons.append("Regime caution -8")
    else:
        score += 5
        reasons.append("Regime normal +5")

    return max(0, min(100, int(score))), reasons

def apply_active_mode(result):
    if result.get("status") != "live":
        return result

    mode = os.getenv("TRADE_SENSITIVITY", "balanced").lower()
    direction = _direction(result)
    score, reasons = _score(result, direction)

    mm = result.get("market_map") or {}
    tm = mm.get("trade_map") or {}
    tstate = result.get("trigger_state") or {}
    state = _upper(tstate.get("state"))
    perm = _upper(tstate.get("entry_permission"))
    regime = result.get("regime_guard") or {}

    if direction == "NEUTRAL":
        readiness_state = "NO TRADE"
        headline = "No clear direction yet."
        command = "WAIT"
    elif regime.get("mode") == "BLOCK_TRADE":
        readiness_state = "NO TRADE - REGIME BLOCK"
        headline = "Market condition is not safe."
        command = "WAIT"
    elif state == "FAILED_CANCEL":
        readiness_state = f"{direction} FAILED"
        headline = "Trigger failed. Do not enter."
        command = "WAIT"
    elif state == "TOO_LATE_DO_NOT_CHASE":
        readiness_state = f"{direction} TOO LATE"
        headline = "Move already happened. Do not chase."
        command = "WAIT RETEST"
    elif "ENTRY_ALLOWED" in perm or score >= (72 if mode == "balanced" else 82):
        readiness_state = f"{direction} ACTIVE"
        headline = f"{direction} trigger is active. Entry allowed only with valid SL and small risk."
        command = f"{direction} ACTIVE"
    elif state == "BROKEN_WAIT_HOLD" or score >= (55 if mode == "balanced" else 65):
        readiness_state = f"PREPARE {direction}"
        headline = f"Prepare {direction}. Trigger is close or partly confirmed, but wait hold/retest."
        command = f"PREPARE {direction}"
    elif score >= 40:
        readiness_state = f"WATCH {direction}"
        headline = f"{direction} idea exists but it is not ready."
        command = f"WATCH {direction}"
    else:
        readiness_state = "NO TRADE"
        headline = "Conditions are still weak."
        command = "WAIT"

    result["trade_readiness"] = {
        "mode": mode,
        "direction": direction,
        "score": score,
        "state": readiness_state,
        "headline": headline,
        "command": command,
        "reasons": reasons,
        "entry": tm.get("aggressive_entry"),
        "safe_entry": tm.get("safe_entry"),
        "stop_loss": tm.get("stop_loss"),
        "tp1": tm.get("tp1_partial_close"),
        "tp2": tm.get("tp2"),
        "cancel_level": tm.get("cancel_level"),
        "note": "V34 separates direction, prepare mode, active trigger, and no-chase so the system is not always late."
    }

    old = _upper(result.get("final_action"))
    if readiness_state.startswith("PREPARE") and ("NO TRADE" in old or "WAIT" in old):
        result["final_action"] = readiness_state
        fd = result.get("final_decision") or {}
        if fd:
            fd["final_action"] = readiness_state
            fd["command"] = command
            fd["summary"] = headline
            result["final_decision"] = fd
    elif readiness_state.endswith("ACTIVE"):
        result["final_action"] = readiness_state
        result["entry_permission"] = "ENTRY_ALLOWED"
        fd = result.get("final_decision") or {}
        if fd:
            fd["final_action"] = readiness_state
            fd["command"] = command
            fd["entry_permission"] = "ENTRY_ALLOWED"
            fd["summary"] = headline
            result["final_decision"] = fd
    return result
