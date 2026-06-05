
from datetime import datetime, timezone
import os
from app.services.market import ASSETS, normalize

_MEM = {}
_STATE = {}

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

def _step(sym):
    return ASSETS[sym]["pip"] / 10

def _moves(sym, a, b):
    try:
        return abs(float(a) - float(b)) / _step(sym)
    except Exception:
        return None

def _level_data(result):
    pc = result.get("permission_clarity") or {}
    pp = result.get("pro_panel") or {}
    sp = result.get("strategy_permission") or {}
    return {
        "decision": pc.get("decision") or sp.get("decision") or pp.get("decision") or result.get("final_action"),
        "direction": pc.get("direction") or sp.get("direction") or pp.get("direction"),
        "current": _num(pc.get("current_price") or sp.get("current_price") or pp.get("current_price") or result.get("price")),
        "buy_above": _num(pc.get("watch_buy_above") or sp.get("buy_above") or pp.get("buy_above")),
        "sell_below": _num(pc.get("watch_sell_below") or sp.get("sell_below") or pp.get("sell_below")),
        "entry": _num(sp.get("entry") or pp.get("entry")),
        "stop": _num(sp.get("stop") or pp.get("stop_or_cancel")),
        "target": _num(sp.get("target") or pp.get("target")),
        "risk_moves": _num(sp.get("risk_moves") or pp.get("risk_moves")),
        "reward_moves": _num(sp.get("reward_moves") or pp.get("reward_moves")),
        "rr": _num(sp.get("rr") or pp.get("rr")),
        "reason": pc.get("why_not_active") or sp.get("reason") or pp.get("reason")
    }

def _candle_close(result):
    return _num(result.get("candle_close") or result.get("close"))

def apply_break_activation(result):
    if result.get("status") != "live":
        return result

    sym = normalize(result.get("asset"))
    d = _level_data(result)
    price = d["current"]
    candle_close = _candle_close(result)
    now = _now()

    hold_seconds = int(os.getenv("BREAK_HOLD_SECONDS", "8"))
    max_late_moves = float(os.getenv("BREAK_MAX_LATE_MOVES", "35"))
    scalp_min_rr = float(os.getenv("BREAK_SCALP_MIN_RR", "0.9"))
    scalp_max_risk = float(os.getenv("BREAK_SCALP_MAX_RISK_MOVES", "22"))
    trade_min_rr = float(os.getenv("BREAK_TRADE_MIN_RR", "1.15"))

    buy_above = d["buy_above"]
    sell_below = d["sell_below"]

    broke_buy = price is not None and buy_above is not None and price >= buy_above
    broke_sell = price is not None and sell_below is not None and price <= sell_below

    direction = None
    break_level = None
    if broke_buy and not broke_sell:
        direction = "BUY"
        break_level = buy_above
    elif broke_sell and not broke_buy:
        direction = "SELL"
        break_level = sell_below
    elif broke_buy and broke_sell:
        # impossible normally unless levels inverted; treat as conflict
        direction = "CONFLICT"

    if direction is None:
        report = {
            "state": "NOT BROKEN",
            "decision": "PLAN ONLY — DO NOT ENTER",
            "current_price": price,
            "buy_above": buy_above,
            "sell_below": sell_below,
            "reason": "Price has not broken the watch level yet.",
            "time": now.isoformat()
        }
        result["break_activation"] = report
        _MEM[sym] = report
        return result

    if direction == "CONFLICT":
        report = {
            "state": "LEVEL CONFLICT",
            "decision": "NO TRADE",
            "current_price": price,
            "buy_above": buy_above,
            "sell_below": sell_below,
            "reason": "BUY above and SELL below levels are conflicting or inverted.",
            "time": now.isoformat()
        }
        result["break_activation"] = report
        _MEM[sym] = report
        result["final_action"] = "NO TRADE"
        return result

    moved_after_break = _moves(sym, break_level, price)
    key = f"{sym}:{direction}:{break_level}"
    st = _STATE.get(key)
    if not st:
        st = {"first_seen": now, "level": break_level, "direction": direction}
        _STATE[key] = st
    held = int((now - st["first_seen"]).total_seconds())

    risk = d["risk_moves"]
    reward = d["reward_moves"]
    rr = d["rr"]

    # Decide after break
    state = f"BREAK {direction} HAPPENED"
    decision = f"BREAK {direction} — WAIT HOLD"
    reason = f"Price broke {direction} level {break_level}. Waiting hold confirmation."

    if moved_after_break is not None and moved_after_break > max_late_moves:
        decision = f"{direction} MOVE MISSED — DO NOT CHASE"
        state = "MOVE MISSED AFTER BREAK"
        reason = f"Price already moved {round(moved_after_break,1)} moves after break. Do not enter late."
    elif held < hold_seconds:
        decision = f"BREAK {direction} — WAIT HOLD"
        state = "BREAK WAIT HOLD"
        reason = f"Break happened, but wait {hold_seconds-held}s more for hold confirmation."
    elif risk is None or reward is None or rr is None:
        decision = "PLAN ONLY — DO NOT ENTER"
        state = "BREAK HELD BUT RISK UNKNOWN"
        reason = "Break held, but risk/reward is not clear."
    elif rr >= trade_min_rr:
        decision = f"TRADE NOW {direction}"
        state = "ACTIVE TRADE ENTRY"
        reason = f"Break held and R/R is acceptable: {round(rr,2)}."
    elif rr >= scalp_min_rr and risk <= scalp_max_risk:
        decision = f"SCALP NOW {direction}"
        state = "ACTIVE SCALP ENTRY"
        reason = f"Break held and scalp risk is acceptable. Risk {round(risk,1)} moves, R/R {round(rr,2)}."
    else:
        decision = "PLAN ONLY — DO NOT ENTER"
        state = "BREAK HELD BUT NOT APPROVED"
        reason = f"Break held, but risk/reward is not approved. Risk {risk}, reward {reward}, R/R {rr}."

    report = {
        "state": state,
        "decision": decision,
        "direction": direction,
        "current_price": price,
        "break_level": break_level,
        "moved_after_break_moves": round(moved_after_break,1) if moved_after_break is not None else None,
        "held_seconds": held,
        "hold_required_seconds": hold_seconds,
        "risk_moves": risk,
        "reward_moves": reward,
        "rr": rr,
        "reason": reason,
        "rule": "After price breaks watch level, classify immediately: wait hold, active entry, or missed move.",
        "time": now.isoformat()
    }

    result["break_activation"] = report
    _MEM[sym] = report

    # Override top panel and permission if break activation produces a stronger/current state.
    pp = result.get("pro_panel") or {}
    pp["decision"] = decision
    pp["reason"] = reason
    pp["direction"] = direction
    pp["current_price"] = price
    pp["entry"] = break_level if decision.startswith(("TRADE NOW", "SCALP NOW")) else "NOT ACTIVE"
    result["pro_panel"] = pp

    pc = result.get("permission_clarity") or {}
    if pc:
        pc["decision"] = decision
        pc["status"] = "ACTIVE ENTRY" if decision.startswith(("TRADE NOW","SCALP NOW")) else "WATCH ONLY — DO NOT ENTER"
        pc["active_entry"] = break_level if pc["status"] == "ACTIVE ENTRY" else None
        pc["why_not_active"] = None if pc["status"] == "ACTIVE ENTRY" else reason
        result["permission_clarity"] = pc

    result["final_action"] = decision
    if decision.startswith("TRADE NOW"):
        result["entry_permission"] = "EDGEFLOW_BREAK_TRADE_NOW"
    elif decision.startswith("SCALP NOW"):
        result["entry_permission"] = "EDGEFLOW_BREAK_SCALP_NOW"
    else:
        result["entry_permission"] = "NO_ENTRY"

    fd = result.get("final_decision") or {}
    if fd:
        fd["final_action"] = decision
        fd["command"] = decision
        fd["entry_permission"] = result["entry_permission"]
        fd["summary"] = reason
        result["final_decision"] = fd

    return result

def break_activation_report():
    return {"break_activation": list(_MEM.values())}
