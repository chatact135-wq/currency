
from datetime import datetime, timezone

_MASTER_MEMORY = {}

def _now():
    return datetime.now(timezone.utc)

def _upper(v):
    return str(v or "").upper()

def _num(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def _has_no_trade_text(result):
    parts = []
    for key in ["best_action", "action", "final_guard", "price_position", "early_risk", "trade_readiness", "final_decision"]:
        obj = result.get(key)
        if isinstance(obj, dict):
            parts += [str(v) for v in obj.values()]
        elif obj is not None:
            parts.append(str(obj))
    parts += [str(result.get("final_action","")), str(result.get("warning",""))]
    text = _upper(" ".join(parts))
    return ("NO TRADE" in text or "DO NOT ENTER" in text or "BLOCK" in text)

def _direction(result):
    for source in [
        result.get("fast_start") or {},
        result.get("early_risk") or {},
        result.get("early_trigger") or {},
        result.get("trade_readiness") or {},
        result.get("price_position") or {},
    ]:
        d = _upper(source.get("direction"))
        if d in ["BUY","SELL"]:
            return d
    fa = _upper(result.get("final_action"))
    if "BUY" in fa and "SELL" not in fa:
        return "BUY"
    if "SELL" in fa and "BUY" not in fa:
        return "SELL"
    return "NEUTRAL"

def _is_safe_entry(result, direction):
    # Safe entry means final action already says BUY/SELL, no lower block, and price position agrees.
    fa = _upper(result.get("final_action"))
    fg = result.get("final_guard") or {}
    pp = result.get("price_position") or {}
    er = result.get("early_risk") or {}
    dl = result.get("direction_lock") or {}
    news = result.get("news") or {}
    regime = result.get("regime_guard") or {}

    if fg.get("blocked"):
        return False, "Final safety check blocks entry."
    if regime.get("mode") == "BLOCK_TRADE":
        return False, "Market condition blocks trade."
    if news.get("mode") == "NEWS_WAIT":
        return False, "News is too close."
    if dl.get("flip_blocked") or result.get("direction_unstable"):
        return False, "Direction changed too quickly."
    if "PRICE IN MIDDLE" in _upper(pp.get("state")):
        return False, "Price is in the middle, not a clean entry."
    if "ALREADY HAPPENED" in _upper(pp.get("state")):
        return False, "Move already happened."
    if er and er.get("allowed") is False and ("BUY NOW" in fa or "SELL NOW" in fa):
        return False, "Early risk controller blocks entry."
    if _has_no_trade_text(result) and ("BUY NOW" in fa or "SELL NOW" in fa):
        return False, "Another part of the system says NO TRADE."

    # Safe entry only if all modules allow and final is explicit.
    if direction == "BUY" and ("BUY NOW" in fa or result.get("entry_permission") in ["ENTRY_ALLOWED", "TRIGGER_LOCK_CONFIRMED"]):
        return True, "Validated safe BUY."
    if direction == "SELL" and ("SELL NOW" in fa or result.get("entry_permission") in ["ENTRY_ALLOWED", "TRIGGER_LOCK_CONFIRMED"]):
        return True, "Validated safe SELL."

    return False, "No safe entry permission."

def apply_master_validator(result):
    if result.get("status") != "live":
        return result

    asset = result.get("asset") or "UNKNOWN"
    direction = _direction(result)
    reasons = []
    state = "DO NOT ENTER"
    command = "DO NOT ENTER"
    simple = "Do not enter now. The validated trade is not clean."

    fg = result.get("final_guard") or {}
    pp = result.get("price_position") or {}
    er = result.get("early_risk") or {}
    fs = result.get("fast_start") or {}
    dl = result.get("direction_lock") or {}
    news = result.get("news") or {}
    regime = result.get("regime_guard") or {}

    # hard blockers
    if fg.get("blocked"):
        reasons += fg.get("reasons", []) or ["Final safety check blocked."]
    if "PRICE IN MIDDLE" in _upper(pp.get("state")):
        reasons.append("Price is in the middle between area and confirmation.")
    if "ALREADY HAPPENED" in _upper(pp.get("state")):
        reasons.append("Move already happened; do not enter late.")
    if dl.get("flip_blocked") or result.get("direction_unstable"):
        reasons.append("Direction changed too quickly.")
    if news.get("mode") == "NEWS_WAIT":
        reasons.append("News is too close.")
    if regime.get("mode") == "BLOCK_TRADE":
        reasons.append("Market condition blocks trade.")

    safe_ok, safe_reason = _is_safe_entry(result, direction)
    if safe_ok and not reasons:
        state = f"ENTER {direction}"
        command = f"ENTER {direction}"
        simple = f"Validated {direction}. Entry allowed because all safety checks passed."
    else:
        # Check fast/early allowed, lower-risk but not "safe"
        if fs.get("allowed") and direction in ["BUY","SELL"] and not reasons:
            state = f"FAST START {direction} SMALL RISK"
            command = f"FAST START {direction}"
            simple = f"Fast start {direction.lower()} is allowed with small risk only."
        elif er.get("allowed") and direction in ["BUY","SELL"] and not reasons:
            state = f"EARLY {direction} SMALL RISK"
            command = f"EARLY {direction}"
            simple = f"Early {direction.lower()} is allowed with small risk only."
        else:
            if not reasons:
                reasons.append(safe_reason)
            # Watch state if idea exists but blocked
            if direction in ["BUY","SELL"]:
                state = f"WATCH {direction} - DO NOT ENTER"
                command = "DO NOT ENTER"
                simple = f"{direction} idea exists, but master validator does not allow entry."

    # If any reason is a hard block, force DO NOT ENTER.
    hard_words = " ".join(reasons).upper()
    if any(w in hard_words for w in ["MIDDLE", "ALREADY HAPPENED", "BLOCK", "NO TRADE", "NEWS", "DIRECTION CHANGED", "RISK"]):
        if not state.startswith("FAST START") and not state.startswith("EARLY"):
            state = "DO NOT ENTER"
            command = "DO NOT ENTER"
            simple = "Do not enter. The system blocked this trade."

    report = {
        "state": state,
        "command": command,
        "direction": direction,
        "simple_message": simple,
        "reasons": reasons,
        "price_position": pp.get("state"),
        "early_risk": er.get("state"),
        "fast_start": fs.get("state"),
        "final_guard": fg.get("final_state"),
        "note": "This is the only final decision to trust. If this says DO NOT ENTER, ignore any earlier BUY/SELL text.",
        "time": _now().isoformat()
    }

    result["master_decision"] = report
    _MASTER_MEMORY[asset] = report

    # Override all confusing top decisions with the validated one.
    result["final_action"] = state
    if state.startswith("ENTER"):
        result["entry_permission"] = "VALIDATED_ENTRY_ALLOWED"
    elif state.startswith("FAST START") or state.startswith("EARLY"):
        result["entry_permission"] = "VALIDATED_SMALL_RISK_ONLY"
    else:
        result["entry_permission"] = "NO_ENTRY"

    fd = result.get("final_decision") or {}
    if fd:
        fd["final_action"] = state
        fd["command"] = command
        fd["entry_permission"] = result["entry_permission"]
        fd["summary"] = simple
        result["final_decision"] = fd

    tr = result.get("trade_readiness") or {}
    if tr:
        tr["state"] = state
        tr["headline"] = simple
        tr["command"] = command
        result["trade_readiness"] = tr

    return result

def master_decision_report():
    return {"master_decisions": list(_MASTER_MEMORY.values())}
