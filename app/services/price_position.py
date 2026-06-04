
from datetime import datetime, timezone
from app.services.market import ASSETS, normalize

_POSITION_MEMORY = {}

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

def _direction(result):
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
    probs = result.get("probabilities") or {}
    up = _num(probs.get("up")) or 0
    down = _num(probs.get("down")) or 0
    if up - down >= 10:
        return "BUY"
    if down - up >= 10:
        return "SELL"
    return "NEUTRAL"

def _levels(result):
    mm = result.get("market_map") or {}
    tm = mm.get("trade_map") or {}
    sw = mm.get("switch_levels") or {}
    tr = result.get("trade_readiness") or {}
    entry = _num(tr.get("entry") or tm.get("aggressive_entry"))
    safe = _num(tr.get("safe_entry") or tm.get("safe_entry"))
    zone_low = min(entry, safe) if entry is not None and safe is not None else entry
    zone_high = max(entry, safe) if entry is not None and safe is not None else safe
    return {
        "entry": entry, "safe": safe, "zone_low": zone_low, "zone_high": zone_high,
        "buy_switch": _num(sw.get("buy_switch")),
        "sell_switch": _num(sw.get("sell_switch")),
        "cancel": _num(tr.get("cancel_level") or tm.get("cancel_level")),
        "sl": _num(tr.get("stop_loss") or tm.get("stop_loss")),
        "tp1": _num(tr.get("tp1") or tm.get("tp1_partial_close")),
        "tp2": _num(tr.get("tp2") or tm.get("tp2")),
    }

def _dist(sym, price, level):
    return {
        "level": level,
        "moves": round(_moves(sym, price, level), 1) if price is not None and level is not None else None,
        "pips": round(_pips(sym, price, level), 1) if price is not None and level is not None else None
    }

def apply_price_position(result):
    if result.get("status") != "live":
        return result

    sym = normalize(result.get("asset"))
    price = _num(result.get("price"))
    direction = _direction(result)
    lv = _levels(result)

    if price is None or direction == "NEUTRAL":
        result["price_position"] = {
            "state": "NO CLEAR POSITION",
            "simple_message": "No clear buy or sell position now.",
            "direction": direction
        }
        return result

    zl, zh = lv.get("zone_low"), lv.get("zone_high")
    buy_sw, sell_sw = lv.get("buy_switch"), lv.get("sell_switch")
    state, action, simple = "UNKNOWN", "WAIT", "Wait. Price position is not clear."
    key = None

    if direction == "BUY":
        key = buy_sw or zh
        distances = {
            "to_buy_area_start": _dist(sym, price, zl),
            "to_buy_area_end": _dist(sym, price, zh),
            "to_buy_confirmation": _dist(sym, price, key),
            "to_cancel": _dist(sym, price, lv.get("cancel") or lv.get("sl")),
        }
        if zl is not None and price < zl:
            state = "BELOW BUY AREA - WAIT"
            action = "WAIT BUY AREA"
            simple = f"Price is below the first buy area. Wait until price reaches {zl}."
        elif zl is not None and zh is not None and zl <= price <= zh:
            state = "INSIDE BUY AREA"
            action = "PREPARE BUY"
            simple = "Price is inside the first buy area. Early buy may be possible only if risk is controlled."
        elif key is not None and zh is not None and price > zh and price < key:
            state = "PRICE IN MIDDLE - NO ENTRY"
            action = "WAIT CONFIRMATION OR RETURN"
            simple = f"Price passed the first buy area but has not reached buy confirmation {key}. Do not buy in the middle."
        elif key is not None and price >= key:
            dist_from_key = _moves(sym, price, key)
            if dist_from_key is not None and dist_from_key > 18:
                state = "BUY MOVE ALREADY HAPPENED"
                action = "DO NOT ENTER LATE"
                simple = "Buy confirmation happened and price moved too far. Do not buy late."
            else:
                state = "BUY CONFIRMED"
                action = "BUY CONFIRMED - CHECK RISK"
                simple = f"Price is above buy confirmation {key}. Buy is confirmed only if risk is still good."
        else:
            distances = {}
    elif direction == "SELL":
        key = sell_sw or zl
        distances = {
            "to_sell_area_start": _dist(sym, price, zl),
            "to_sell_area_end": _dist(sym, price, zh),
            "to_sell_confirmation": _dist(sym, price, key),
            "to_cancel": _dist(sym, price, lv.get("cancel") or lv.get("sl")),
        }
        if zl is not None and key is not None and price < zl and price > key:
            state = "PRICE IN MIDDLE - NO ENTRY"
            action = "WAIT SELL AREA OR BREAK BELOW"
            simple = f"Price is between upper sell area and fast sell level. Sell only if price goes up to {zl}-{zh} and fails, or breaks below {key}."
        elif zl is not None and zh is not None and zl <= price <= zh:
            state = "INSIDE SELL AREA"
            action = "PREPARE SELL"
            simple = "Price is inside the upper sell area. Early sell may be possible only if price starts falling and risk is controlled."
        elif zh is not None and price > zh:
            state = "ABOVE SELL AREA - WAIT FAILURE"
            action = "WAIT SELL FAILURE"
            simple = "Price is above the sell area. Wait until it fails and starts coming down."
        elif key is not None and price <= key:
            dist_from_key = _moves(sym, price, key)
            if dist_from_key is not None and dist_from_key > 18:
                state = "SELL MOVE ALREADY HAPPENED"
                action = "DO NOT ENTER LATE"
                simple = "Sell confirmation happened and price moved too far. Do not sell late."
            else:
                state = "SELL CONFIRMED"
                action = "SELL CONFIRMED - CHECK RISK"
                simple = f"Price is below sell confirmation {key}. Sell is confirmed only if risk is still good."
        else:
            distances = {}
    else:
        distances = {}

    report = {
        "state": state, "action": action, "direction": direction, "price": price,
        "zone_low": zl, "zone_high": zh, "confirmation_level": key,
        "cancel_level": lv.get("cancel") or lv.get("sl"),
        "distances": distances, "simple_message": simple,
        "moves_note": "Moves = last digit movement. 10 moves = 1 pip on EUR/USD and GBP/USD.",
        "time": _now().isoformat()
    }
    result["price_position"] = report
    _POSITION_MEMORY[sym] = report

    if state == "PRICE IN MIDDLE - NO ENTRY":
        result["entry_permission"] = "NO_ENTRY"
        result["final_action"] = "PRICE IN MIDDLE - NO ENTRY"
        fd = result.get("final_decision") or {}
        if fd:
            fd["final_action"] = "PRICE IN MIDDLE - NO ENTRY"
            fd["command"] = action
            fd["entry_permission"] = "NO_ENTRY"
            fd["summary"] = simple
            result["final_decision"] = fd
        tr = result.get("trade_readiness") or {}
        if tr:
            tr["state"] = "PRICE IN MIDDLE - NO ENTRY"
            tr["headline"] = simple
            tr["command"] = action
            result["trade_readiness"] = tr

    return result

def price_position_report():
    return {"price_position": list(_POSITION_MEMORY.values())}
