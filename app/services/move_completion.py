
import os
from datetime import datetime, timezone
from app.services.market import ASSETS, normalize

_MOVE_MEMORY = {}

def _now():
    return datetime.now(timezone.utc)

def _num(v, default=None):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default

def _upper(v):
    return str(v or "").upper()

def _point(sym):
    return ASSETS[sym]["pip"] / 10

def _moves(sym, a, b):
    try:
        return abs(float(a)-float(b)) / _point(sym)
    except Exception:
        return None

def _direction(a,b):
    if b > a:
        return "BUY"
    if b < a:
        return "SELL"
    return "NEUTRAL"

def _candle(sym, c):
    o = _num(c.get("open"))
    h = _num(c.get("high"))
    l = _num(c.get("low"))
    cl = _num(c.get("close"))
    if None in [o,h,l,cl]:
        return None
    return {
        "open": o, "high": h, "low": l, "close": cl,
        "direction": _direction(o, cl),
        "body_moves": round(_moves(sym, o, cl) or 0, 1),
        "range_moves": round(_moves(sym, l, h) or 0, 1),
        "upper_wick_moves": round(_moves(sym, max(o,cl), h) or 0, 1),
        "lower_wick_moves": round(_moves(sym, min(o,cl), l) or 0, 1),
    }

def _dominant_direction(result):
    # Prefer master/fast/early/price-position direction
    for obj in [
        result.get("master_decision") or {},
        result.get("fast_start") or {},
        result.get("early_risk") or {},
        result.get("early_trigger") or {},
        result.get("price_position") or {},
        result.get("trade_readiness") or {},
    ]:
        d = _upper(obj.get("direction"))
        if d in ["BUY","SELL"]:
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
    up = _num(probs.get("up"),0)
    down = _num(probs.get("down"),0)
    if up - down >= 10:
        return "BUY"
    if down - up >= 10:
        return "SELL"
    return "NEUTRAL"

def _move_from_recent(sym, candles, direction):
    if not candles or len(candles) < 6 or direction not in ["BUY","SELL"]:
        return None
    recent = candles[-12:] if len(candles) >= 12 else candles
    current = _num(recent[-1].get("close"))
    highs = [_num(x.get("high")) for x in recent if _num(x.get("high")) is not None]
    lows = [_num(x.get("low")) for x in recent if _num(x.get("low")) is not None]
    if current is None or not highs or not lows:
        return None
    if direction == "BUY":
        start = min(lows)
        extreme = max(highs)
        moved = _moves(sym, start, current)
        from_extreme = _moves(sym, current, extreme)
        return {"start": start, "extreme": extreme, "current": current, "moved_moves": round(moved or 0,1), "pullback_from_extreme_moves": round(from_extreme or 0,1)}
    else:
        start = max(highs)
        extreme = min(lows)
        moved = _moves(sym, start, current)
        from_extreme = _moves(sym, current, extreme)
        return {"start": start, "extreme": extreme, "current": current, "moved_moves": round(moved or 0,1), "pullback_from_extreme_moves": round(from_extreme or 0,1)}

def apply_move_completion(result, candles=None):
    if result.get("status") != "live":
        return result
    candles = candles or []
    sym = normalize(result.get("asset"))
    direction = _dominant_direction(result)

    if direction not in ["BUY","SELL"] or len(candles) < 6:
        result["move_completion"] = {
            "state": "NO CLEAR MOVE",
            "direction": direction,
            "simple_message": "No clear buy or sell move to judge.",
            "block_entry": False
        }
        return result

    starting = float(os.getenv("MOVE_STARTING_MOVES","12"))
    active = float(os.getenv("MOVE_ACTIVE_MOVES","25"))
    extended = float(os.getenv("MOVE_EXTENDED_MOVES","40"))
    finished = float(os.getenv("MOVE_FINISHED_MOVES","55"))
    weak_candle = float(os.getenv("MOVE_WEAK_CANDLE_MOVES","6"))

    move = _move_from_recent(sym, candles, direction)
    last = _candle(sym, candles[-1])
    prev = _candle(sym, candles[-2])
    if not move or not last or not prev:
        return result

    moved = move["moved_moves"]
    pullback_from_extreme = move["pullback_from_extreme_moves"]
    opposite_candle = last["direction"] not in [direction, "NEUTRAL"] and last["body_moves"] >= weak_candle
    weak_after_big = moved >= extended and last["body_moves"] <= weak_candle
    failure_near_extreme = pullback_from_extreme >= 10 and moved >= active

    block_entry = False
    management = False
    reasons = []

    if moved < starting:
        state = "MOVE NOT STARTED YET"
        simple = f"{direction} move has not started enough yet."
    elif moved < active:
        state = "MOVE STARTING"
        simple = f"{direction} move is starting early."
    elif moved < extended:
        state = "MOVE ACTIVE"
        simple = f"{direction} move is active."
    elif moved < finished:
        state = "MOVE EXTENDED"
        simple = f"{direction} move already moved a lot. New entry is risky."
        reasons.append("Move is extended.")
        block_entry = True
        management = True
    else:
        state = "MOVE LIKELY FINISHED"
        simple = f"{direction} move likely already happened. Do not enter late."
        reasons.append("Move is too far from its start.")
        block_entry = True
        management = True

    if opposite_candle:
        state = "MOVE WEAKENING"
        simple = f"{direction} move is weakening because opposite candle appeared."
        reasons.append("Opposite candle appeared after the move.")
        block_entry = True
        management = True

    if weak_after_big:
        state = "MOVE WEAKENING"
        simple = f"{direction} move slowed down after moving a lot."
        reasons.append("Small candle after extended move.")
        block_entry = True
        management = True

    if failure_near_extreme:
        state = "MOVE LIKELY FINISHED"
        simple = f"{direction} move may be finished because price moved away from the best point."
        reasons.append("Price moved away from the best high/low after the move.")
        block_entry = True
        management = True

    if management:
        if direction == "BUY":
            manage = "If already in BUY: take some profit or move stop to entry. If not in BUY: do not buy late."
        else:
            manage = "If already in SELL: take some profit or move stop to entry. If not in SELL: do not sell late."
    else:
        manage = "Move is not finished yet, but entry still needs risk check."

    report = {
        "state": state,
        "direction": direction,
        "moved_moves": moved,
        "pullback_from_extreme_moves": pullback_from_extreme,
        "last_candle_direction": last["direction"],
        "last_body_moves": last["body_moves"],
        "opposite_candle": opposite_candle,
        "block_entry": block_entry,
        "management_alert": management,
        "simple_message": simple,
        "management_message": manage,
        "reasons": reasons,
        "start_price": move["start"],
        "extreme_price": move["extreme"],
        "current_price": move["current"],
        "moves_note": "Moves = last digit movement. 10 moves = 1 pip on EUR/USD and GBP/USD.",
        "time": _now().isoformat()
    }

    result["move_completion"] = report
    _MOVE_MEMORY[sym] = report

    # If likely finished, block any new entry text.
    if block_entry:
        result["entry_permission"] = "NO_ENTRY"
        result["final_action"] = "MOVE LIKELY FINISHED - DO NOT ENTER LATE"
        result["warning"] = simple + " " + manage

        fd = result.get("final_decision") or {}
        if fd:
            fd["final_action"] = "MOVE LIKELY FINISHED - DO NOT ENTER LATE"
            fd["command"] = "DO NOT ENTER"
            fd["entry_permission"] = "NO_ENTRY"
            fd["summary"] = simple
            result["final_decision"] = fd

        md = result.get("master_decision") or {}
        if md:
            md["state"] = "DO NOT ENTER"
            md["command"] = "DO NOT ENTER"
            md["simple_message"] = simple
            md["reasons"] = (md.get("reasons") or []) + reasons + ["Move completion detector blocked late entry."]
            result["master_decision"] = md

    return result

def move_completion_report():
    return {"move_completion": list(_MOVE_MEMORY.values())}
