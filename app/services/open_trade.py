
from datetime import datetime, timezone
from app.services.market import ASSETS, normalize

_OPEN_TRADES = {}

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

def open_trade(asset, direction, entry_price=None, stop=None, target=None, note=None):
    sym = normalize(asset)
    direction = _upper(direction)
    if direction not in ["BUY","SELL"]:
        return {"ok": False, "error": "direction must be BUY or SELL"}

    _OPEN_TRADES[sym] = {
        "asset": sym,
        "direction": direction,
        "entry_price": _num(entry_price),
        "stop": _num(stop),
        "target": _num(target),
        "note": note or "",
        "opened_at": _now(),
        "status": "OPEN"
    }
    return {"ok": True, "trade": _serialize(sym)}

def close_trade(asset):
    sym = normalize(asset)
    tr = _OPEN_TRADES.get(sym)
    if not tr:
        return {"ok": False, "error": "No open trade for asset"}
    tr["status"] = "CLOSED"
    tr["closed_at"] = _now()
    old = _serialize(sym)
    _OPEN_TRADES.pop(sym, None)
    return {"ok": True, "closed_trade": old}

def trade_status(asset=None):
    if asset:
        sym = normalize(asset)
        return {"open_trades": [_serialize(sym)] if sym in _OPEN_TRADES else []}
    return {"open_trades": [_serialize(sym) for sym in _OPEN_TRADES]}

def _serialize(sym):
    tr = _OPEN_TRADES.get(sym)
    if not tr:
        return None
    out = dict(tr)
    for k in ["opened_at","closed_at"]:
        if out.get(k):
            out[k] = out[k].isoformat()
    return out

def _manage_message(sym, tr, result):
    price = _num(result.get("price"))
    direction = tr.get("direction")
    entry = _num(tr.get("entry_price")) or price
    stop = _num(tr.get("stop"))
    target = _num(tr.get("target"))

    pnl_moves = None
    if price is not None and entry is not None:
        raw = (price - entry) if direction == "BUY" else (entry - price)
        pnl_moves = raw / (ASSETS[sym]["pip"]/10)

    mc = result.get("move_completion") or {}
    pp = result.get("price_position") or {}
    fg = result.get("final_guard") or {}

    danger = False
    action = "HOLD / MANAGE"
    reason = "Open trade is active."

    if pnl_moves is not None and pnl_moves >= 15:
        action = "PROTECT PROFIT"
        reason = "Trade is in profit. Protect profit or close partial."
    if pnl_moves is not None and pnl_moves >= 25:
        action = "TAKE PARTIAL / TRAIL STOP"
        reason = "Trade moved well in your favor. Do not let profit turn into loss."

    if mc.get("block_entry") or "FINISHED" in _upper(mc.get("state")) or "WEAKENING" in _upper(mc.get("state")):
        action = "PROTECT PROFIT / DO NOT ADD"
        reason = "Move may be extended or weakening. Manage existing trade, do not add new trade."

    if fg.get("blocked"):
        action = "MANAGE RISK"
        reason = "Safety check warns about new entries. For open trade, manage stop/exit."

    # invalidation based on stored stop if hit
    if price is not None and stop is not None:
        if direction == "BUY" and price <= stop:
            danger = True
            action = "EXIT / STOP HIT"
            reason = "Price reached or passed your buy stop/cancel level."
        elif direction == "SELL" and price >= stop:
            danger = True
            action = "EXIT / STOP HIT"
            reason = "Price reached or passed your sell stop/cancel level."

    # target hit
    if price is not None and target is not None:
        if direction == "BUY" and price >= target:
            action = "TARGET HIT / TAKE PROFIT"
            reason = "Price reached your buy target."
        elif direction == "SELL" and price <= target:
            action = "TARGET HIT / TAKE PROFIT"
            reason = "Price reached your sell target."

    return {
        "decision": f"MANAGE OPEN {direction}",
        "action": action,
        "reason": reason,
        "danger": danger,
        "asset": sym,
        "direction": direction,
        "entry_price": entry,
        "current_price": price,
        "stop": stop,
        "target": target,
        "pnl_moves": round(pnl_moves,1) if pnl_moves is not None else None,
        "pnl_pips": round(pnl_moves/10,1) if pnl_moves is not None else None,
        "moves_note": "Moves = last digit movement. 10 moves = 1 pip on EUR/USD and GBP/USD."
    }

def apply_open_trade_manager(result):
    if result.get("status") != "live":
        return result
    sym = normalize(result.get("asset"))
    tr = _OPEN_TRADES.get(sym)
    if not tr:
        result["open_trade"] = {"has_open_trade": False}
        return result

    mgmt = _manage_message(sym, tr, result)
    result["open_trade"] = {"has_open_trade": True, "trade": _serialize(sym), "management": mgmt}

    # Override pro panel / final action to management mode.
    pp = result.get("pro_panel") or {}
    if pp:
        pp["decision"] = mgmt["decision"]
        pp["decision_type"] = "MANAGE_OPEN_TRADE"
        pp["reason"] = mgmt["reason"]
        pp["current_price"] = mgmt["current_price"]
        pp["entry"] = mgmt["entry_price"]
        pp["stop_or_cancel"] = mgmt["stop"]
        pp["target"] = mgmt["target"]
        pp["risk_moves"] = None
        pp["reward_moves"] = None
        pp["rr"] = None
        result["pro_panel"] = pp

    result["final_action"] = mgmt["decision"]
    result["entry_permission"] = "MANAGE_OPEN_TRADE"

    fd = result.get("final_decision") or {}
    if fd:
        fd["final_action"] = mgmt["decision"]
        fd["command"] = mgmt["action"]
        fd["entry_permission"] = "MANAGE_OPEN_TRADE"
        fd["summary"] = mgmt["reason"]
        result["final_decision"] = fd

    return result
