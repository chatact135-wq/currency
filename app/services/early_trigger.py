
import os
from datetime import datetime, timezone
from app.services.market import ASSETS, normalize

_EARLY_MEMORY = {}

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

def _pips(sym, a, b):
    try:
        return abs(float(a) - float(b)) / ASSETS[sym]["pip"]
    except Exception:
        return None

def _dir_from_prob(result):
    probs = result.get("probabilities") or {}
    up = _num(probs.get("up"), 0)
    down = _num(probs.get("down"), 0)
    if up - down >= 12:
        return "BUY", up - down
    if down - up >= 12:
        return "SELL", down - up
    return "NEUTRAL", abs(up-down)

def _trade_direction(result):
    tr = result.get("trade_readiness") or {}
    d = _upper(tr.get("direction"))
    if d in ["BUY","SELL"]:
        return d
    mm = result.get("market_map") or {}
    bias = _upper((mm.get("current_state") or {}).get("bias"))
    if bias in ["BUY","SELL"]:
        return bias
    d, _ = _dir_from_prob(result)
    return d

def _levels(result):
    mm = result.get("market_map") or {}
    tm = mm.get("trade_map") or {}
    sw = mm.get("switch_levels") or {}
    tr = result.get("trade_readiness") or {}
    return {
        "entry": _num(tr.get("entry") or tm.get("aggressive_entry")),
        "safe": _num(tr.get("safe_entry") or tm.get("safe_entry")),
        "sl": _num(tr.get("stop_loss") or tm.get("stop_loss")),
        "tp1": _num(tr.get("tp1") or tm.get("tp1_partial_close")),
        "tp2": _num(tr.get("tp2") or tm.get("tp2")),
        "cancel": _num(tr.get("cancel_level") or tm.get("cancel_level")),
        "buy_switch": _num(sw.get("buy_switch")),
        "sell_switch": _num(sw.get("sell_switch")),
    }

def _last_candle_pressure(sym, candles):
    if not candles or len(candles) < 3:
        return {"direction":"NEUTRAL","body_pips":0,"range_pips":0,"two_candle_pips":0}
    last = candles[-1]
    prev = candles[-2]
    o = _num(last.get("open"),0)
    c = _num(last.get("close"),0)
    h = _num(last.get("high"),0)
    l = _num(last.get("low"),0)
    po = _num(prev.get("open"),0)
    pc = _num(prev.get("close"),0)
    direction = "BUY" if c > o else "SELL" if c < o else "NEUTRAL"
    two_dir = "BUY" if c > po else "SELL" if c < po else "NEUTRAL"
    return {
        "direction": direction,
        "body_pips": round(_pips(sym,o,c) or 0,1),
        "range_pips": round(_pips(sym,l,h) or 0,1),
        "two_direction": two_dir,
        "two_candle_pips": round(_pips(sym,po,c) or 0,1),
        "close": c,
        "open": o,
    }

def apply_early_trigger(result, candles=None):
    if os.getenv("EARLY_TRIGGER_ENABLED","true").lower() not in ["1","true","yes","on"]:
        return result
    if result.get("status") != "live":
        return result
    candles = candles or []
    sym = normalize(result.get("asset"))
    price = _num(result.get("price"))
    if price is None:
        return result

    min_score = float(os.getenv("EARLY_TRIGGER_MIN_SCORE","58"))
    min_body = float(os.getenv("EARLY_TRIGGER_BODY_PIPS_FX","2.5"))
    max_dist = float(os.getenv("EARLY_TRIGGER_MAX_DISTANCE_PIPS","4"))

    direction = _trade_direction(result)
    prob_dir, prob_edge = _dir_from_prob(result)
    lv = _levels(result)
    pressure = _last_candle_pressure(sym, candles)
    tr = result.get("trade_readiness") or {}
    readiness_score = _num(tr.get("score"),0)

    events = []
    score = 0

    if direction in ["BUY","SELL"]:
        score += 20
        events.append(f"Main idea is {direction}.")
    if prob_dir == direction and prob_edge >= 15:
        score += 18
        events.append(f"Probability supports {direction}.")
    if readiness_score >= 45:
        score += 12
        events.append("Readiness is building.")
    if pressure.get("direction") == direction and pressure.get("body_pips",0) >= min_body:
        score += 20
        events.append(f"Latest candle started pushing {direction}.")
    elif pressure.get("two_direction") == direction and pressure.get("two_candle_pips",0) >= min_body:
        score += 15
        events.append(f"Recent candles started pushing {direction}.")

    # Position relative to early area and confirmation
    position = "UNKNOWN"
    early_price = None
    confirm_price = None
    invalidation = lv.get("cancel") or lv.get("sl")

    if direction == "BUY":
        early_price = lv.get("entry")
        confirm_price = lv.get("buy_switch") or lv.get("safe")
        if early_price is not None and confirm_price is not None:
            if price < early_price:
                position = "BELOW_EARLY_AREA"
            elif price >= early_price and price < confirm_price:
                position = "EARLY_BUY_ZONE"
                score += 18
                events.append("Price is between early buy area and full buy confirmation.")
            elif price >= confirm_price:
                position = "CONFIRMED_OR_LATE_BUY"
    elif direction == "SELL":
        early_price = lv.get("entry")
        confirm_price = lv.get("sell_switch") or lv.get("safe")
        if early_price is not None and confirm_price is not None:
            if price > early_price:
                position = "ABOVE_EARLY_AREA"
            elif price <= early_price and price > confirm_price:
                position = "EARLY_SELL_ZONE"
                score += 18
                events.append("Price is between early sell area and full sell confirmation.")
            elif price <= confirm_price:
                position = "CONFIRMED_OR_LATE_SELL"

    dist_to_confirm = _pips(sym, price, confirm_price) if confirm_price is not None else None
    if dist_to_confirm is not None and dist_to_confirm <= max_dist:
        score += 10
        events.append("Price is close to full confirmation level.")

    # Risk/reward sanity
    tp = lv.get("tp1") or lv.get("tp2")
    sl = lv.get("sl") or lv.get("cancel")
    rr_ok = True
    rr = None
    if tp is not None and sl is not None:
        reward = _pips(sym, price, tp)
        risk = _pips(sym, price, sl)
        if reward is not None and risk is not None and risk > 0:
            rr = reward / risk
            if rr < 0.7:
                rr_ok = False
                events.append("Reward is too small compared with risk.")

    detected = direction in ["BUY","SELL"] and score >= min_score and rr_ok and position in ["EARLY_BUY_ZONE","EARLY_SELL_ZONE"]

    if detected:
        state = f"EARLY {direction} POSSIBLE"
        if direction == "BUY":
            simple = "Early buy is possible before full confirmation. Higher risk. Use small risk and close quickly if price falls back."
            action = f"Early BUY possible near current price. Safer BUY is above {confirm_price}."
            invalid_msg = f"Cancel early buy if price falls below {invalidation}."
        else:
            simple = "Early sell is possible before full confirmation. Higher risk. Use small risk and close quickly if price rises back."
            action = f"Early SELL possible near current price. Safer SELL is below {confirm_price}."
            invalid_msg = f"Cancel early sell if price rises above {invalidation}."
    else:
        state = "NO EARLY ENTRY"
        simple = "No early entry now."
        action = "Wait for better early signal or full confirmation."
        invalid_msg = ""

    report = {
        "detected": detected,
        "state": state,
        "direction": direction,
        "score": int(score),
        "required_score": min_score,
        "position": position,
        "price": price,
        "early_price": early_price,
        "confirm_price": confirm_price,
        "distance_to_confirm_pips": round(dist_to_confirm,1) if dist_to_confirm is not None else None,
        "invalidation": invalidation,
        "rr": round(rr,2) if rr is not None else None,
        "pressure": pressure,
        "simple_message": simple,
        "action": action,
        "invalidation_message": invalid_msg,
        "events": events[-8:],
        "warning": "EARLY entry is faster but riskier. Safe entry waits for full confirmation.",
        "time": _now().isoformat()
    }

    result["early_trigger"] = report
    _EARLY_MEMORY[sym] = report

    # Important: if early trigger detected, do NOT overwrite final safe decision as guaranteed BUY/SELL.
    # Show it as a separate actionable early warning.
    if detected:
        alerts = result.get("alerts") or []
        alerts.append({
            "asset": sym,
            "type": "EARLY_TRIGGER",
            "title": state,
            "title_simple": simple,
            "direction": direction,
            "severity": "early_high_risk",
            "action": action,
            "action_simple": action + " " + invalid_msg,
            "reason": "Early trigger detected before full confirmation.",
            "price": price,
            "time": report["time"]
        })
        result["alerts"] = alerts[-20:]

        # If final action is only WAIT/NO TRADE, upgrade to EARLY warning but not safe entry.
        fa = _upper(result.get("final_action"))
        if "BUY NOW" not in fa and "SELL NOW" not in fa:
            result["final_action"] = state + " - HIGHER RISK"
            fd = result.get("final_decision") or {}
            if fd:
                fd["final_action"] = state + " - HIGHER RISK"
                fd["command"] = state
                fd["summary"] = simple
                fd["entry_permission"] = "EARLY_WARNING_ONLY"
                result["final_decision"] = fd

    return result

def early_trigger_report():
    return {"early_triggers": list(_EARLY_MEMORY.values())}
