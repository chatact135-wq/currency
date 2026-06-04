
from app.services.market import ASSETS, normalize

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

def _dir(result):
    tr = result.get("trade_readiness") or {}
    d = _upper(tr.get("direction"))
    if d in ["BUY","SELL"]:
        return d
    fa = _upper(result.get("final_action"))
    if "BUY" in fa and "SELL" not in fa:
        return "BUY"
    if "SELL" in fa and "BUY" not in fa:
        return "SELL"
    mm = result.get("market_map") or {}
    b = _upper((mm.get("current_state") or {}).get("bias"))
    if b in ["BUY","SELL"]:
        return b
    return "NEUTRAL"

def _levels(result):
    mm = result.get("market_map") or {}
    tm = mm.get("trade_map") or {}
    tr = result.get("trade_readiness") or {}
    return {
        "entry": _num(tr.get("entry") or tm.get("aggressive_entry")),
        "safe": _num(tr.get("safe_entry") or tm.get("safe_entry")),
        "sl": _num(tr.get("stop_loss") or tm.get("stop_loss")),
        "tp1": _num(tr.get("tp1") or tm.get("tp1_partial_close")),
        "tp2": _num(tr.get("tp2") or tm.get("tp2")),
        "cancel": _num(tr.get("cancel_level") or tm.get("cancel_level")),
    }

def _best_action_text(result):
    pieces = []
    for key in ["best_action", "action"]:
        obj = result.get(key)
        if isinstance(obj, dict):
            pieces += [str(v) for v in obj.values()]
        elif obj is not None:
            pieces.append(str(obj))
    for key in ["best_action_text", "warning"]:
        if result.get(key):
            pieces.append(str(result.get(key)))
    return _upper(" ".join(pieces))

def apply_final_guard(result):
    if result.get("status") != "live":
        return result

    sym = normalize(result.get("asset"))
    price = _num(result.get("price"))
    direction = _dir(result)
    lv = _levels(result)
    fd = result.get("final_decision") or {}
    tr = result.get("trade_readiness") or {}

    text_top = _upper(str(result.get("final_action")) + " " + str(fd.get("final_action")) + " " + str(fd.get("command")))
    best_text = _best_action_text(result)

    fast_start_allowed = result.get("entry_permission") == "FAST_START_ALLOWED_SMALL_RISK"

    top_says_entry = (
        "BUY NOW" in text_top or "SELL NOW" in text_top or 
        "ENTRY_ALLOWED" in _upper(result.get("entry_permission"))
    )
    lower_says_no = "NO TRADE" in best_text or "DO NOT ENTER" in best_text

    reasons = []
    block = False
    tp_dist = None

    if top_says_entry and lower_says_no and not fast_start_allowed:
        block = True
        reasons.append("Conflict: top says enter, but lower card says NO TRADE.")

    if price is not None and direction in ["BUY","SELL"]:
        tp = lv.get("tp1") or lv.get("tp2")
        sl = lv.get("sl") or lv.get("cancel")
        if tp is not None:
            tp_dist = _pips(sym, price, tp)
            if tp_dist is not None and tp_dist < 3:
                block = True
                reasons.append(f"TP is too close: only {round(tp_dist,1)} pips away.")
        if tp is not None and sl is not None:
            reward = _pips(sym, price, tp)
            risk = _pips(sym, price, sl)
            if reward is not None and risk is not None and risk > 0:
                rr = reward / risk
                if rr < 0.8:
                    block = True
                    reasons.append(f"Reward is smaller than risk. R/R about {round(rr,2)}.")

    mm = result.get("market_map") or {}
    sw = mm.get("switch_levels") or {}
    buy_switch = _num(sw.get("buy_switch"))
    sell_switch = _num(sw.get("sell_switch"))

    if price is not None and direction == "BUY" and lv.get("entry") is not None and buy_switch is not None:
        if price > lv["entry"] and price < buy_switch:
            block = True
            reasons.append("Price is in the middle between first buy area and buy confirmation.")
    if price is not None and direction == "SELL" and lv.get("entry") is not None and sell_switch is not None:
        if price < lv["entry"] and price > sell_switch:
            block = True
            reasons.append("Price is in the middle between first sell area and sell confirmation.")

    if result.get("direction_unstable"):
        block = True
        reasons.append("Direction changed too quickly. Wait for stability.")

    strong = result.get("strong_move") or {}
    if strong.get("detected") and top_says_entry and "ACTIVE" not in _upper(tr.get("state")):
        block = True
        reasons.append("Strong move already happened. Do not enter late.")

    if block:
        result["final_guard"] = {
            "blocked": True,
            "final_state": "NO TRADE - CONFLICT/RISK BLOCK",
            "simple_message": "Do not enter. The system found a conflict or bad risk.",
            "reasons": reasons,
            "direction": direction,
            "price": price,
            "entry": lv.get("entry"),
            "tp1": lv.get("tp1"),
            "tp_distance_pips": round(tp_dist,1) if tp_dist is not None else None
        }
        result["final_action"] = "NO TRADE - CONFLICT/RISK BLOCK"
        result["entry_permission"] = "NO_ENTRY"
        result["warning"] = "Blocked by final guard: " + " | ".join(reasons)

        fd = result.get("final_decision") or {}
        if fd:
            fd["final_action"] = "NO TRADE - CONFLICT/RISK BLOCK"
            fd["command"] = "DO NOT ENTER"
            fd["entry_permission"] = "NO_ENTRY"
            fd["summary"] = "Do not enter because top decision conflicts with risk or best action."
            result["final_decision"] = fd

        tr = result.get("trade_readiness") or {}
        if tr:
            tr["state"] = "NO TRADE - CONFLICT/RISK BLOCK"
            tr["headline"] = "Do not enter. Entry is blocked by conflict/risk check."
            tr["command"] = "DO NOT ENTER"
            tr["final_guard_reasons"] = reasons
            result["trade_readiness"] = tr
    else:
        result["final_guard"] = {
            "blocked": False,
            "final_state": "OK",
            "simple_message": "No major conflict found.",
            "reasons": []
        }

    return result
