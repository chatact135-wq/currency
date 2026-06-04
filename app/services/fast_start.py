
import os
from datetime import datetime, timezone
from app.services.market import ASSETS, normalize

_FAST_START_MEMORY = {}

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

def _pip(sym):
    return ASSETS[sym]["pip"]

def _points(sym, a, b):
    # one move/point on 5-digit FX = 0.00001; for JPY-like would adapt to pip/10
    pip = _pip(sym)
    point = pip / 10
    try:
        return abs(float(a)-float(b)) / point
    except Exception:
        return None

def _pips(sym, a, b):
    try:
        return abs(float(a)-float(b)) / _pip(sym)
    except Exception:
        return None

def _direction(a,b):
    if b > a:
        return "BUY"
    if b < a:
        return "SELL"
    return "NEUTRAL"

def _last_data(sym, candles):
    if not candles or len(candles) < 4:
        return None
    c1 = candles[-1]
    c2 = candles[-2]
    c3 = candles[-3]
    o = _num(c1.get("open"))
    cl = _num(c1.get("close"))
    h = _num(c1.get("high"))
    l = _num(c1.get("low"))
    po = _num(c2.get("open"))
    pc = _num(c2.get("close"))
    c3o = _num(c3.get("open"))
    if None in [o,cl,h,l,po,pc,c3o]:
        return None
    return {
        "last_direction": _direction(o,cl),
        "last_body_moves": round(_points(sym,o,cl) or 0,1),
        "last_range_moves": round(_points(sym,l,h) or 0,1),
        "two_direction": _direction(po,cl),
        "two_moves": round(_points(sym,po,cl) or 0,1),
        "three_direction": _direction(c3o,cl),
        "three_moves": round(_points(sym,c3o,cl) or 0,1),
        "close": cl,
        "open": o,
        "high": h,
        "low": l
    }

def _prob_direction(result):
    probs = result.get("probabilities") or {}
    up = _num(probs.get("up"),0)
    down = _num(probs.get("down"),0)
    if up - down >= 8:
        return "BUY", up-down
    if down - up >= 8:
        return "SELL", down-up
    return "NEUTRAL", abs(up-down)

def _locked_direction(result):
    dl = result.get("direction_lock") or {}
    d = _upper(dl.get("locked_direction"))
    if d in ["BUY","SELL"]:
        return d
    return None

def _target_and_risk(result, direction):
    price = _num(result.get("price"))
    tr = result.get("trade_readiness") or {}
    mm = result.get("market_map") or {}
    tm = mm.get("trade_map") or {}
    tp1 = _num(tr.get("tp1") or tm.get("tp1_partial_close"))
    tp2 = _num(tr.get("tp2") or tm.get("tp2"))
    sl = _num(tr.get("stop_loss") or tm.get("stop_loss") or tr.get("cancel_level") or tm.get("cancel_level"))
    target = None
    if direction == "BUY":
        if tp1 and price and tp1 > price: target = tp1
        elif tp2 and price and tp2 > price: target = tp2
    elif direction == "SELL":
        if tp1 and price and tp1 < price: target = tp1
        elif tp2 and price and tp2 < price: target = tp2
    return price, target, sl

def apply_fast_start(result, candles=None):
    if os.getenv("FAST_START_ENABLED","true").lower() not in ["1","true","yes","on"]:
        return result
    if result.get("status") != "live":
        return result

    candles = candles or []
    sym = normalize(result.get("asset"))
    data = _last_data(sym, candles)
    if not data:
        result["fast_start"] = {"detected":False,"state":"NO FAST START","simple_message":"Not enough candle data."}
        return result

    min_moves = float(os.getenv("FAST_START_MIN_MOVES","8"))
    confirm_moves = float(os.getenv("FAST_START_CONFIRM_MOVES","12"))
    max_late_moves = float(os.getenv("FAST_START_MAX_LATE_MOVES","18"))

    prob_dir, prob_edge = _prob_direction(result)
    locked = _locked_direction(result)
    direction = "NEUTRAL"
    score = 0
    reasons = []

    # First push: last candle body
    if data["last_direction"] in ["BUY","SELL"] and data["last_body_moves"] >= min_moves:
        direction = data["last_direction"]
        score += 25
        reasons.append(f"Last candle started {direction} by {data['last_body_moves']} moves.")

    # Two-candle pressure
    if data["two_direction"] in ["BUY","SELL"] and data["two_moves"] >= confirm_moves:
        if direction == "NEUTRAL":
            direction = data["two_direction"]
        if direction == data["two_direction"]:
            score += 25
            reasons.append(f"Recent candles push {direction} by {data['two_moves']} moves.")

    # Three-candle early trend
    if data["three_direction"] in ["BUY","SELL"] and data["three_moves"] >= confirm_moves:
        if direction == "NEUTRAL":
            direction = data["three_direction"]
        if direction == data["three_direction"]:
            score += 12
            reasons.append(f"Short move is building {direction}.")

    if prob_dir == direction and direction != "NEUTRAL":
        score += 15
        reasons.append(f"Probability supports {direction}.")
    elif prob_dir != "NEUTRAL" and direction != "NEUTRAL":
        score -= 10
        reasons.append("Probability does not fully agree.")

    if locked == direction:
        score += 12
        reasons.append("Direction lock agrees.")
    elif locked and locked != direction:
        score -= 18
        reasons.append("Direction lock does not agree yet.")

    # news/regime
    news = result.get("news") or {}
    regime = result.get("regime_guard") or {}
    if news.get("mode") == "NEWS_WAIT":
        score -= 30
        reasons.append("News is too close.")
    if regime.get("mode") == "BLOCK_TRADE":
        score -= 40
        reasons.append("Market condition blocks trade.")

    price, target, sl = _target_and_risk(result, direction)
    reward_moves = _points(sym, price, target) if price is not None and target is not None else None
    risk_moves = _points(sym, price, sl) if price is not None and sl is not None else None
    rr = (reward_moves / risk_moves) if reward_moves is not None and risk_moves and risk_moves > 0 else None

    # classify late: if recent move already too large
    move_now = max(data["last_body_moves"], data["two_moves"])
    already_late = move_now > max_late_moves

    allowed = False
    if direction in ["BUY","SELL"] and score >= 45 and not already_late:
        # risk filter in moves: reward should not be tiny, risk should not be huge
        if reward_moves is not None and risk_moves is not None and rr is not None:
            if reward_moves >= 15 and risk_moves <= 25 and rr >= 0.9:
                allowed = True
                reasons.append("Fast start risk is acceptable.")
            else:
                reasons.append("Fast start risk is not acceptable yet.")
        else:
            # still report warning but not allowed
            reasons.append("Target/stop not clear enough for fast start.")

    if direction == "NEUTRAL":
        state = "NO FAST START"
        simple = "No fast buy or sell is starting now."
    elif already_late:
        state = f"FAST {direction} ALREADY HAPPENED"
        simple = f"Fast {direction.lower()} move already moved too much. Do not enter late."
    elif allowed:
        state = f"FAST START {direction} ALLOWED"
        simple = f"Fast {direction.lower()} is starting early. Use small risk only."
    elif score >= 35:
        state = f"FAST {direction} STARTING - WAIT RISK"
        simple = f"Fast {direction.lower()} may be starting, but risk is not good enough yet."
    else:
        state = "NO FAST START"
        simple = "No reliable fast start yet."

    report = {
        "detected": direction in ["BUY","SELL"] and score >= 35,
        "allowed": allowed,
        "state": state,
        "direction": direction,
        "score": int(score),
        "price": price,
        "target": target,
        "stop": sl,
        "reward_moves": round(reward_moves,1) if reward_moves is not None else None,
        "risk_moves": round(risk_moves,1) if risk_moves is not None else None,
        "rr": round(rr,2) if rr is not None else None,
        "last_body_moves": data["last_body_moves"],
        "two_candle_moves": data["two_moves"],
        "already_late": already_late,
        "simple_message": simple,
        "reasons": reasons[-8:],
        "time": _now().isoformat(),
        "note": "Moves = last digit movement. 10 moves = 1 pip on EUR/USD and GBP/USD."
    }

    result["fast_start"] = report
    _FAST_START_MEMORY[sym] = report

    alerts = result.get("alerts") or []
    if report["detected"]:
        alerts.append({
            "asset": sym,
            "type": "FAST_START",
            "title": state,
            "title_simple": simple,
            "direction": direction,
            "severity": "fast_start_allowed" if allowed else "fast_start_watch",
            "action": "ENTER EARLY SMALL RISK" if allowed else "WATCH / WAIT RISK",
            "action_simple": simple,
            "reason": " | ".join(report["reasons"]),
            "price": price,
            "time": report["time"]
        })
        result["alerts"] = alerts[-20:]

    if allowed:
        result["final_action"] = state
        result["entry_permission"] = "FAST_START_ALLOWED_SMALL_RISK"
        fd = result.get("final_decision") or {}
        if fd:
            fd["final_action"] = state
            fd["command"] = state
            fd["entry_permission"] = "FAST_START_ALLOWED_SMALL_RISK"
            fd["summary"] = simple
            result["final_decision"] = fd

    return result

def fast_start_report():
    return {"fast_start": list(_FAST_START_MEMORY.values())}
