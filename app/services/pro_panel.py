
from datetime import datetime, timezone
from app.services.market import ASSETS, normalize

_PRO_PANEL_MEMORY = {}

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
        return abs(float(a)-float(b)) / (ASSETS[sym]["pip"]/10)
    except Exception:
        return None

def _pips(sym, a, b):
    try:
        return abs(float(a)-float(b)) / ASSETS[sym]["pip"]
    except Exception:
        return None

def _dist(sym, a, b):
    return {
        "moves": round(_moves(sym,a,b),1) if a is not None and b is not None else None,
        "pips": round(_pips(sym,a,b),1) if a is not None and b is not None else None
    }

def _levels(result):
    se = result.get("scalp_entry") or {}
    tr = result.get("trade_readiness") or {}
    mm = result.get("market_map") or {}
    tm = mm.get("trade_map") or {}
    sw = mm.get("switch_levels") or {}
    tl = result.get("trigger_lock") or {}

    buy_above = _num(se.get("buy_above") or sw.get("buy_switch") or tl.get("locked_trigger") if _upper(tl.get("direction"))=="BUY" else None)
    sell_below = _num(se.get("sell_below") or sw.get("sell_switch") or tl.get("locked_trigger") if _upper(tl.get("direction"))=="SELL" else None)

    if buy_above is None:
        buy_above = _num(sw.get("buy_switch") or tr.get("safe_entry") or tm.get("safe_entry"))
    if sell_below is None:
        sell_below = _num(sw.get("sell_switch") or tr.get("cancel_level") or tm.get("cancel_level") or tr.get("entry") or tm.get("aggressive_entry"))

    return {
        "buy_above": buy_above,
        "sell_below": sell_below,
        "entry": _num(tr.get("entry") or tm.get("aggressive_entry")),
        "safe": _num(tr.get("safe_entry") or tm.get("safe_entry")),
        "stop": _num(tr.get("stop_loss") or tm.get("stop_loss") or tr.get("cancel_level") or tm.get("cancel_level")),
        "cancel": _num(tr.get("cancel_level") or tm.get("cancel_level")),
        "tp1": _num(tr.get("tp1") or tm.get("tp1_partial_close")),
        "tp2": _num(tr.get("tp2") or tm.get("tp2")),
    }

def _direction(result):
    for obj in [result.get("master_decision") or {}, result.get("scalp_entry") or {}, result.get("fast_start") or {}, result.get("early_risk") or {}, result.get("trade_readiness") or {}]:
        d = _upper(obj.get("direction"))
        if d in ["BUY","SELL"]:
            return d
        s = _upper(obj.get("state"))
        if "BUY" in s and "SELL" not in s:
            return "BUY"
        if "SELL" in s and "BUY" not in s:
            return "SELL"
    probs = result.get("probabilities") or {}
    up = _num(probs.get("up")) or 0
    down = _num(probs.get("down")) or 0
    if up - down >= 10:
        return "BUY"
    if down - up >= 10:
        return "SELL"
    return "NEUTRAL"

def _target(direction, price, lv):
    if price is None:
        return None
    if direction == "BUY":
        if lv.get("tp1") is not None and lv["tp1"] > price: return lv["tp1"]
        if lv.get("tp2") is not None and lv["tp2"] > price: return lv["tp2"]
    if direction == "SELL":
        if lv.get("tp1") is not None and lv["tp1"] < price: return lv["tp1"]
        if lv.get("tp2") is not None and lv["tp2"] < price: return lv["tp2"]
    return None

def _main_block_reason(result):
    # Return one clear reason only, professional style.
    md = result.get("master_decision") or {}
    fg = result.get("final_guard") or {}
    pp = result.get("price_position") or {}
    mc = result.get("move_completion") or {}
    se = result.get("scalp_entry") or {}
    tl = result.get("trigger_lock") or {}
    news = result.get("news") or {}
    regime = result.get("regime_guard") or {}

    if news.get("mode") == "NEWS_WAIT":
        return "News is too close."
    if regime.get("mode") == "BLOCK_TRADE":
        return "Market condition blocks trade."
    if result.get("direction_unstable") or (result.get("direction_lock") or {}).get("flip_blocked"):
        return "Direction changed too quickly."
    if mc.get("block_entry"):
        return "Move already extended or finished."
    if "PRICE IN MIDDLE" in _upper(pp.get("state")):
        return "Price is in the middle."
    if fg.get("blocked"):
        rs = fg.get("reasons") or []
        return rs[0] if rs else "Final safety check blocks trade."
    if se and not se.get("allowed"):
        rs = se.get("reasons") or []
        return rs[0] if rs else "Scalp conditions are not enough."
    if "WAIT" in _upper(tl.get("state")):
        return "Trigger reached, waiting hold."
    if md.get("reasons"):
        return md.get("reasons")[0]
    return "No clean entry yet."

def apply_pro_panel(result):
    if result.get("status") != "live":
        return result

    sym = normalize(result.get("asset"))
    price = _num(result.get("price"))
    lv = _levels(result)
    direction = _direction(result)

    md = result.get("master_decision") or {}
    se = result.get("scalp_entry") or {}
    tl = result.get("trigger_lock") or {}
    mc = result.get("move_completion") or {}
    fg = result.get("final_guard") or {}

    raw_state = _upper(md.get("state") or result.get("final_action"))
    scalp_allowed = bool(se.get("allowed"))
    safe_allowed = result.get("entry_permission") in ["VALIDATED_ENTRY_ALLOWED","TRIGGER_LOCK_CONFIRMED","ENTRY_ALLOWED"]
    trigger_confirmed = "CONFIRMED" in _upper(tl.get("state"))
    blocked = bool(fg.get("blocked")) or bool(mc.get("block_entry")) or result.get("direction_unstable")

    decision = "DO NOT ENTER"
    decision_type = "NO_TRADE"

    if blocked:
        decision = "DO NOT ENTER"
        decision_type = "BLOCKED"
    elif "ENTER BUY" in raw_state or (safe_allowed and direction=="BUY") or (trigger_confirmed and direction=="BUY"):
        decision = "ENTER BUY"
        decision_type = "SAFE_ENTRY"
    elif "ENTER SELL" in raw_state or (safe_allowed and direction=="SELL") or (trigger_confirmed and direction=="SELL"):
        decision = "ENTER SELL"
        decision_type = "SAFE_ENTRY"
    elif scalp_allowed and direction == "BUY":
        decision = "SCALP BUY"
        decision_type = "SCALP_ENTRY"
    elif scalp_allowed and direction == "SELL":
        decision = "SCALP SELL"
        decision_type = "SCALP_ENTRY"
    elif "WATCH BUY" in raw_state or direction == "BUY":
        decision = "WAIT"
        decision_type = "WATCH_BUY"
    elif "WATCH SELL" in raw_state or direction == "SELL":
        decision = "WAIT"
        decision_type = "WATCH_SELL"

    if decision in ["WAIT","DO NOT ENTER"]:
        reason = _main_block_reason(result)
    elif decision_type == "SAFE_ENTRY":
        reason = "Validated entry. All main checks passed."
    else:
        reason = "Scalp entry allowed with small risk only."

    entry = None
    if decision.endswith("BUY"):
        entry = lv.get("buy_above") or lv.get("safe") or price
    elif decision.endswith("SELL"):
        entry = lv.get("sell_below") or lv.get("safe") or price
    else:
        entry = lv.get("buy_above") if direction=="BUY" else lv.get("sell_below") if direction=="SELL" else None

    stop = lv.get("stop") or lv.get("cancel")
    target = _target(direction, price, lv)

    risk_moves = _moves(sym, entry, stop) if entry is not None and stop is not None else None
    reward_moves = _moves(sym, entry, target) if entry is not None and target is not None else None
    rr = reward_moves / risk_moves if reward_moves is not None and risk_moves and risk_moves > 0 else None

    report = {
        "decision": decision,
        "decision_type": decision_type,
        "direction": direction,
        "reason": reason,
        "current_price": price,
        "buy_above": lv.get("buy_above"),
        "sell_below": lv.get("sell_below"),
        "entry": entry,
        "stop_or_cancel": stop,
        "target": target,
        "risk_moves": round(risk_moves,1) if risk_moves is not None else None,
        "reward_moves": round(reward_moves,1) if reward_moves is not None else None,
        "rr": round(rr,2) if rr is not None else None,
        "distance_to_buy": _dist(sym, price, lv.get("buy_above")),
        "distance_to_sell": _dist(sym, price, lv.get("sell_below")),
        "simple_rule": "Only trade ENTER BUY, ENTER SELL, SCALP BUY, or SCALP SELL. Ignore WATCH.",
        "moves_note": "Moves = last digit movement. 10 moves = 1 pip on EUR/USD and GBP/USD.",
        "time": _now().isoformat()
    }

    result["pro_panel"] = report
    _PRO_PANEL_MEMORY[sym] = report

    # Make top-level final text match the professional decision.
    result["final_action"] = decision
    if decision in ["ENTER BUY","ENTER SELL"]:
        result["entry_permission"] = "PRO_VALIDATED_ENTRY"
    elif decision in ["SCALP BUY","SCALP SELL"]:
        result["entry_permission"] = "PRO_SCALP_ENTRY_SMALL_RISK"
    else:
        result["entry_permission"] = "NO_ENTRY"

    fd = result.get("final_decision") or {}
    if fd:
        fd["final_action"] = decision
        fd["command"] = decision if decision not in ["WAIT","DO NOT ENTER"] else "DO NOT ENTER" if decision=="DO NOT ENTER" else "WAIT"
        fd["entry_permission"] = result["entry_permission"]
        fd["summary"] = reason
        result["final_decision"] = fd

    return result

def pro_panel_report():
    return {"pro_panel": list(_PRO_PANEL_MEMORY.values())}
