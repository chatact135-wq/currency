
from app.services.market import ASSETS, normalize

def rp(sym, v):
    pip = ASSETS[sym]["pip"]
    if pip >= 0.1:
        return round(float(v), 2)
    if pip >= 0.01:
        return round(float(v), 3)
    return round(float(v), 5)

def pips(sym, a, b):
    return round(abs(float(a)-float(b)) / ASSETS[sym]["pip"], 1)

def levels(c, n=24):
    d = c[-n:] if len(c) >= n else c
    highs = [x["high"] for x in d]
    lows = [x["low"] for x in d]
    return {
        "prev_high": max(highs[:-1]) if len(highs) > 1 else max(highs),
        "prev_low": min(lows[:-1]) if len(lows) > 1 else min(lows),
        "high": max(highs),
        "low": min(lows),
        "mid": (max(highs) + min(lows)) / 2
    }

def speed(c, n=6):
    d = c[-n:] if len(c) >= n else c
    if len(d) < 2:
        return {"direction": "SIDEWAYS", "strength": 0}
    net = d[-1]["close"] - d[0]["close"]
    avg = sum(abs(x["high"] - x["low"]) for x in d) / len(d)
    if avg <= 0:
        return {"direction": "SIDEWAYS", "strength": 0}
    if abs(net) < avg * 0.35:
        return {"direction": "SIDEWAYS", "strength": round(abs(net) / avg * 100, 1)}
    return {"direction": "UP" if net > 0 else "DOWN", "strength": round(abs(net) / avg * 100, 1)}

def dist(sym):
    pip = ASSETS[sym]["pip"]
    if pip == 0.0001:
        return {"ag": 2*pip, "safe": 5*pip, "sl": 6*pip, "tp1": 5*pip, "tp2": 9*pip, "full": 13*pip}
    if pip >= 0.1:
        return {"ag": 0.8, "safe": 2.0, "sl": 2.5, "tp1": 2.0, "tp2": 4.0, "full": 6.0}
    return {"ag": 0.03, "safe": 0.08, "sl": 0.10, "tp1": 0.08, "tp2": 0.14, "full": 0.20}

def infer_bias(res):
    text = (str(res.get("final_action","")) + " " + str((res.get("final_decision") or {}).get("final_action","")) + " " + str(res.get("master_bias",""))).upper()
    if "BUY" in text and "SELL" not in text:
        return "BUY"
    if "SELL" in text and "BUY" not in text:
        return "SELL"
    probs = res.get("probabilities") or {}
    up = float(probs.get("up") or 0)
    down = float(probs.get("down") or 0)
    if up - down >= 15:
        return "BUY"
    if down - up >= 15:
        return "SELL"
    return "NEUTRAL"

def simple_text(sym, bias, buy_switch, sell_switch, entry, safe, sl, tp1, tp2, full):
    if bias == "BUY":
        return {
            "headline": "BUY idea, but wait for confirmation.",
            "simple_steps": [
                "Do not buy now.",
                f"Watch BUY above {rp(sym, entry)}.",
                f"Safer BUY confirmation above {rp(sym, safe)}.",
                f"If price breaks above {rp(sym, entry)} and holds, BUY becomes possible.",
                f"If price breaks below {rp(sym, sell_switch)}, cancel BUY and watch SELL.",
                f"After entry: SL {rp(sym, sl)}, TP1 {rp(sym, tp1)}, TP2 {rp(sym, tp2)}, full close {rp(sym, full)}."
            ],
            "short_command": f"WAIT. BUY only above {rp(sym, entry)}."
        }
    if bias == "SELL":
        return {
            "headline": "SELL idea, but wait for confirmation.",
            "simple_steps": [
                "Do not sell now.",
                f"Watch SELL below {rp(sym, entry)}.",
                f"Safer SELL confirmation below {rp(sym, safe)}.",
                f"If price breaks below {rp(sym, entry)} and holds, SELL becomes possible.",
                f"If price breaks above {rp(sym, buy_switch)}, cancel SELL and watch BUY.",
                f"After entry: SL {rp(sym, sl)}, TP1 {rp(sym, tp1)}, TP2 {rp(sym, tp2)}, full close {rp(sym, full)}."
            ],
            "short_command": f"WAIT. SELL only below {rp(sym, entry)}."
        }
    return {
        "headline": "No clear trade now.",
        "simple_steps": [
            "Do not buy now.",
            "Do not sell now.",
            f"Watch BUY above {rp(sym, buy_switch)}.",
            f"Watch SELL below {rp(sym, sell_switch)}.",
            "Trade only after one side breaks and holds."
        ],
        "short_command": "WAIT. No clear side yet."
    }

def build_market_map(sym, c, ind, res):
    sym = normalize(sym)
    price = float(ind["price"])
    lv = levels(c)
    sp = speed(c)
    d = dist(sym)
    bias = infer_bias(res)

    buy_switch = max(price + d["ag"], lv["prev_high"] + d["ag"] * 0.25)
    sell_switch = min(price - d["ag"], lv["prev_low"] - d["ag"] * 0.25)

    if bias == "BUY":
        entry = buy_switch
        safe = max(price + d["safe"], lv["prev_high"] + d["ag"])
        # V24 FIX: calculate from entry, not current price
        sl = entry - d["sl"]
        tp1 = entry + d["tp1"]
        tp2 = entry + d["tp2"]
        full = entry + d["full"]
        cancel = sell_switch
        command = f"WAIT. BUY only above {rp(sym, entry)}."
        flip = f"Cancel BUY and watch SELL if price breaks below {rp(sym, sell_switch)}."
        rule = "Buy only after breakout and hold, or pullback bullish reaction."
    elif bias == "SELL":
        entry = sell_switch
        safe = min(price - d["safe"], lv["prev_low"] - d["ag"])
        # V24 FIX: calculate from entry, not current price
        sl = entry + d["sl"]
        tp1 = entry - d["tp1"]
        tp2 = entry - d["tp2"]
        full = entry - d["full"]
        cancel = buy_switch
        command = f"WAIT. SELL only below {rp(sym, entry)}."
        flip = f"Cancel SELL and watch BUY if price breaks above {rp(sym, buy_switch)}."
        rule = "Sell only after breakdown and hold, or pullback bearish rejection."
    else:
        entry = safe = sl = tp1 = tp2 = full = cancel = None
        command = "WAIT. No clear side yet."
        flip = "Wait until buy or sell switch breaks."
        rule = "No prediction trade. Wait for switch."

    simple = simple_text(sym, bias, buy_switch, sell_switch, entry, safe, sl, tp1, tp2, full) if bias != "NEUTRAL" else simple_text(sym, bias, buy_switch, sell_switch, 0, 0, 0, 0, 0, 0)

    return {
        "current_state": {"price": rp(sym, price), "bias": bias, "speed_direction": sp["direction"], "speed_strength": sp["strength"]},
        "switch_levels": {"buy_switch": rp(sym, buy_switch), "sell_switch": rp(sym, sell_switch), "buy_distance_pips": pips(sym, price, buy_switch), "sell_distance_pips": pips(sym, price, sell_switch), "flip_rule": flip},
        "trade_map": {"command": command, "open_rule": rule, "aggressive_entry": rp(sym, entry) if entry is not None else None, "safe_entry": rp(sym, safe) if safe is not None else None, "stop_loss": rp(sym, sl) if sl is not None else None, "tp1_partial_close": rp(sym, tp1) if tp1 is not None else None, "tp2": rp(sym, tp2) if tp2 is not None else None, "full_close": rp(sym, full) if full is not None else None, "cancel_level": rp(sym, cancel) if cancel is not None else None, "risk_note": "Aggressive is faster/riskier. Safe waits for more confirmation."},
        "simple_trade_plan": simple,
        "pip_plan": {"stop_pips": pips(sym, entry, sl) if entry is not None else None, "tp1_pips": pips(sym, entry, tp1) if entry is not None else None, "tp2_pips": pips(sym, entry, tp2) if entry is not None else None, "full_close_pips": pips(sym, entry, full) if entry is not None else None},
        "fix_note": "V24 fix: TP/SL are calculated from entry price, not current price."
    }
