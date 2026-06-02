
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
        "mid": (max(highs)+min(lows))/2
    }

def speed(c, n=6):
    d = c[-n:] if len(c) >= n else c
    if len(d) < 2:
        return {"direction":"SIDEWAYS","strength":0}
    net = d[-1]["close"] - d[0]["close"]
    avg = sum(abs(x["high"]-x["low"]) for x in d) / len(d)
    if avg <= 0:
        return {"direction":"SIDEWAYS","strength":0}
    if abs(net) < avg * 0.35:
        return {"direction":"SIDEWAYS","strength":round(abs(net)/avg*100,1)}
    return {"direction":"UP" if net > 0 else "DOWN","strength":round(abs(net)/avg*100,1)}

def dist(sym):
    pip = ASSETS[sym]["pip"]
    if pip == 0.0001:
        return {"ag":2*pip, "safe":4*pip, "sl":6*pip, "tp1":5*pip, "tp2":9*pip, "full":13*pip, "max_structure":8*pip}
    if pip >= 0.1:
        return {"ag":0.8, "safe":1.8, "sl":2.5, "tp1":2.0, "tp2":4.0, "full":6.0, "max_structure":3.5}
    return {"ag":0.03, "safe":0.08, "sl":0.10, "tp1":0.08, "tp2":0.14, "full":0.20, "max_structure":0.12}

def infer_bias(res):
    txt = (str(res.get("final_action",""))+" "+str((res.get("final_decision") or {}).get("final_action",""))+" "+str(res.get("master_bias",""))).upper()
    if "BUY" in txt and "SELL" not in txt:
        return "BUY"
    if "SELL" in txt and "BUY" not in txt:
        return "SELL"
    pr = res.get("probabilities") or {}
    up = float(pr.get("up") or 0)
    down = float(pr.get("down") or 0)
    if up - down >= 15:
        return "BUY"
    if down - up >= 15:
        return "SELL"
    return "NEUTRAL"

def simple_plan(sym, bias, price, entry, safe, sl, tp1, tp2, full, opposite_switch, far_level_note):
    if bias == "BUY":
        return {
            "headline": "BUY idea, but wait for close trigger.",
            "simple_steps": [
                "Do not buy randomly now.",
                f"Fast BUY trigger above {rp(sym, entry)}.",
                f"Safer BUY trigger above {rp(sym, safe)}.",
                f"If price breaks above {rp(sym, entry)} and holds, BUY becomes possible.",
                f"If price falls below {rp(sym, opposite_switch)}, cancel BUY and watch SELL.",
                f"After entry: SL {rp(sym, sl)}, TP1 {rp(sym, tp1)}, TP2 {rp(sym, tp2)}, full close {rp(sym, full)}.",
                far_level_note
            ],
            "short_command": f"WAIT. BUY only above {rp(sym, entry)}."
        }
    if bias == "SELL":
        return {
            "headline": "SELL idea, but wait for close trigger.",
            "simple_steps": [
                "Do not sell randomly now.",
                f"Fast SELL trigger below {rp(sym, entry)}.",
                f"Safer SELL trigger below {rp(sym, safe)}.",
                f"If price breaks below {rp(sym, entry)} and holds, SELL becomes possible.",
                f"If price rises above {rp(sym, opposite_switch)}, cancel SELL and watch BUY.",
                f"After entry: SL {rp(sym, sl)}, TP1 {rp(sym, tp1)}, TP2 {rp(sym, tp2)}, full close {rp(sym, full)}.",
                far_level_note
            ],
            "short_command": f"WAIT. SELL only below {rp(sym, entry)}."
        }
    return {
        "headline": "No clear trade now.",
        "simple_steps": [
            "Do not buy now.",
            "Do not sell now.",
            f"Fast BUY trigger above {rp(sym, price + dist(sym)['ag'])}.",
            f"Fast SELL trigger below {rp(sym, price - dist(sym)['ag'])}.",
            "Trade only after one side breaks and holds."
        ],
        "short_command": "WAIT. No clear side yet."
    }

def build_market_map(sym, c, ind, res):
    sym = normalize(sym)
    # IMPORTANT: ind['price'] is replaced by live price in V25 engine.
    price = float(ind["price"])
    lv = levels(c)
    sp = speed(c)
    d = dist(sym)
    bias = infer_bias(res)

    # Micro scalp levels always close to live price.
    micro_buy = price + d["ag"]
    micro_sell = price - d["ag"]
    safe_buy = price + d["safe"]
    safe_sell = price - d["safe"]

    # Structure levels are context only if too far.
    structure_buy = lv["prev_high"]
    structure_sell = lv["prev_low"]
    structure_buy_far = abs(structure_buy - price) > d["max_structure"]
    structure_sell_far = abs(price - structure_sell) > d["max_structure"]

    if bias == "BUY":
        entry = micro_buy
        safe = safe_buy
        sl = entry - d["sl"]
        tp1 = entry + d["tp1"]
        tp2 = entry + d["tp2"]
        full = entry + d["full"]
        opposite = micro_sell
        command = f"WAIT. BUY only above {rp(sym, entry)}."
        flip = f"Cancel BUY and watch SELL if price breaks below {rp(sym, opposite)}."
        far_note = f"Old structure high {rp(sym, structure_buy)} is far, so it is context only, not required for scalp." if structure_buy_far else f"Nearby structure high: {rp(sym, structure_buy)}."
        rule = "Micro scalp buy uses close live trigger; structure level is context only."
    elif bias == "SELL":
        entry = micro_sell
        safe = safe_sell
        sl = entry + d["sl"]
        tp1 = entry - d["tp1"]
        tp2 = entry - d["tp2"]
        full = entry - d["full"]
        opposite = micro_buy
        command = f"WAIT. SELL only below {rp(sym, entry)}."
        flip = f"Cancel SELL and watch BUY if price breaks above {rp(sym, opposite)}."
        far_note = f"Old structure low {rp(sym, structure_sell)} is far, so it is context only, not required for scalp." if structure_sell_far else f"Nearby structure low: {rp(sym, structure_sell)}."
        rule = "Micro scalp sell uses close live trigger; structure level is context only."
    else:
        entry = safe = sl = tp1 = tp2 = full = opposite = None
        command = "WAIT. No clear side yet."
        flip = "Wait until one micro switch breaks."
        far_note = "No clear bias."
        rule = "No prediction trade."

    simple = simple_plan(sym, bias, price, entry, safe, sl, tp1, tp2, full, opposite, far_note) if bias != "NEUTRAL" else simple_plan(sym, bias, price, 0,0,0,0,0,0,0,far_note)

    return {
        "current_state": {"price": rp(sym, price), "bias": bias, "speed_direction": sp["direction"], "speed_strength": sp["strength"]},
        "switch_levels": {
            "buy_switch": rp(sym, micro_buy),
            "sell_switch": rp(sym, micro_sell),
            "safe_buy": rp(sym, safe_buy),
            "safe_sell": rp(sym, safe_sell),
            "buy_distance_pips": pips(sym, price, micro_buy),
            "sell_distance_pips": pips(sym, price, micro_sell),
            "structure_buy": rp(sym, structure_buy),
            "structure_sell": rp(sym, structure_sell),
            "structure_buy_far": structure_buy_far,
            "structure_sell_far": structure_sell_far,
            "flip_rule": flip
        },
        "trade_map": {
            "command": command,
            "open_rule": rule,
            "aggressive_entry": rp(sym, entry) if entry is not None else None,
            "safe_entry": rp(sym, safe) if safe is not None else None,
            "stop_loss": rp(sym, sl) if sl is not None else None,
            "tp1_partial_close": rp(sym, tp1) if tp1 is not None else None,
            "tp2": rp(sym, tp2) if tp2 is not None else None,
            "full_close": rp(sym, full) if full is not None else None,
            "cancel_level": rp(sym, opposite) if opposite is not None else None,
            "risk_note": "Micro scalp entries are close. Use smaller lot if aggressive."
        },
        "simple_trade_plan": simple,
        "pip_plan": {
            "stop_pips": pips(sym, entry, sl) if entry is not None else None,
            "tp1_pips": pips(sym, entry, tp1) if entry is not None else None,
            "tp2_pips": pips(sym, entry, tp2) if entry is not None else None,
            "full_close_pips": pips(sym, entry, full) if entry is not None else None
        },
        "fix_note": "V25 fix: live-price micro scalp levels; far structure levels are context only."
    }
