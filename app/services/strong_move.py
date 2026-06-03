
import os
from datetime import datetime, timezone
from app.services.market import ASSETS, normalize

_STRONG_MEMORY = {}

def _now():
    return datetime.now(timezone.utc)

def _num(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default

def _pips(sym, a, b):
    return abs(float(a)-float(b)) / ASSETS[sym]["pip"]

def _direction(a, b):
    if b > a:
        return "BUY"
    if b < a:
        return "SELL"
    return "NEUTRAL"

def _thresholds(sym):
    pip = ASSETS[sym]["pip"]
    if pip == 0.0001:
        return (
            float(os.getenv("STRONG_MOVE_PIPS_FX", "7")),
            float(os.getenv("STRONG_CANDLE_PIPS_FX", "5"))
        )
    if pip >= 0.1:
        return (
            float(os.getenv("STRONG_MOVE_POINTS_GOLD", "8")),
            float(os.getenv("STRONG_CANDLE_POINTS_GOLD", "5"))
        )
    return (7,5)

def _candle_metrics(sym, candle):
    o = _num(candle.get("open"))
    h = _num(candle.get("high"))
    l = _num(candle.get("low"))
    c = _num(candle.get("close"))
    return {
        "open": o, "high": h, "low": l, "close": c,
        "direction": _direction(o,c),
        "body_pips": round(_pips(sym,o,c),1),
        "range_pips": round(_pips(sym,l,h),1)
    }

def detect_strong_move(sym, candles, result):
    sym = normalize(sym)
    if not candles or len(candles) < 6:
        return {
            "detected": False,
            "message": "Not enough candles to check strong move.",
            "simple_message": "Not enough price candles yet.",
        }

    strong_move_pips, strong_candle_pips = _thresholds(sym)
    recent = candles[-6:]
    last = recent[-1]
    prev = recent[-2]
    last_m = _candle_metrics(sym, last)
    prev_m = _candle_metrics(sym, prev)

    # Multi-candle move from first open to last close
    first_open = _num(recent[0].get("open"))
    last_close = _num(last.get("close"))
    net_pips = round(_pips(sym, first_open, last_close),1)
    net_direction = _direction(first_open, last_close)

    # Biggest candle in recent window
    metrics = [_candle_metrics(sym,x) for x in recent]
    biggest_body = max(metrics, key=lambda x: x["body_pips"])
    biggest_range = max(metrics, key=lambda x: x["range_pips"])

    # Break of previous recent high/low, excluding current candle
    prev_window = candles[-12:-1] if len(candles) >= 12 else candles[:-1]
    prev_high = max(_num(x.get("high")) for x in prev_window) if prev_window else None
    prev_low = min(_num(x.get("low")) for x in prev_window) if prev_window else None

    break_low = prev_low is not None and last_close < prev_low
    break_high = prev_high is not None and last_close > prev_high

    events = []
    if last_m["body_pips"] >= strong_candle_pips and last_m["direction"] in ["BUY","SELL"]:
        events.append({
            "type": "STRONG_LAST_CANDLE",
            "direction": last_m["direction"],
            "pips": last_m["body_pips"],
            "message": f"Last candle moved strongly {last_m['direction']} by {last_m['body_pips']} pips."
        })

    if biggest_body["body_pips"] >= strong_candle_pips and biggest_body["direction"] in ["BUY","SELL"]:
        events.append({
            "type": "BIG_CANDLE_IN_RECENT",
            "direction": biggest_body["direction"],
            "pips": biggest_body["body_pips"],
            "message": f"A strong candle appeared recently: {biggest_body['direction']} {biggest_body['body_pips']} pips."
        })

    if net_pips >= strong_move_pips and net_direction in ["BUY","SELL"]:
        events.append({
            "type": "MULTI_CANDLE_IMPULSE",
            "direction": net_direction,
            "pips": net_pips,
            "message": f"Recent candles moved strongly {net_direction} by {net_pips} pips."
        })

    if break_low:
        events.append({
            "type": "BROKE_RECENT_LOW",
            "direction": "SELL",
            "pips": net_pips,
            "message": "Price crossed below the recent low."
        })

    if break_high:
        events.append({
            "type": "BROKE_RECENT_HIGH",
            "direction": "BUY",
            "pips": net_pips,
            "message": "Price crossed above the recent high."
        })

    if not events:
        return {
            "detected": False,
            "direction": "NEUTRAL",
            "message": "No strong move detected now.",
            "simple_message": "No big fast move right now.",
            "last_candle": last_m,
            "net_pips": net_pips,
            "net_direction": net_direction
        }

    # Choose dominant direction by most recent/large events
    sell_score = sum(e.get("pips",0) for e in events if e["direction"] == "SELL")
    buy_score = sum(e.get("pips",0) for e in events if e["direction"] == "BUY")
    direction = "SELL" if sell_score > buy_score else "BUY" if buy_score > sell_score else events[-1]["direction"]
    move_pips = max(e.get("pips",0) for e in events)

    if direction == "SELL":
        action_if_in_trade = "If you are already in SELL: take some profit, move stop to entry or above last small high, and let the rest continue."
        action_if_not_in_trade = "If you are not in SELL: do not sell late. Wait for price to come back up a little, then fail again."
        simple = "Strong move down detected. If you were already selling, protect profit. If not, do not enter late."
    else:
        action_if_in_trade = "If you are already in BUY: take some profit, move stop to entry or below last small low, and let the rest continue."
        action_if_not_in_trade = "If you are not in BUY: do not buy late. Wait for price to come back down a little, then rise again."
        simple = "Strong move up detected. If you were already buying, protect profit. If not, do not enter late."

    report = {
        "detected": True,
        "direction": direction,
        "move_pips": round(move_pips,1),
        "net_pips": net_pips,
        "net_direction": net_direction,
        "events": events[-5:],
        "message": f"STRONG {direction} MOVE DETECTED.",
        "simple_message": simple,
        "action_if_in_trade": action_if_in_trade,
        "action_if_not_in_trade": action_if_not_in_trade,
        "take_profit_rule": "Take partial profit after strong move. Move stop to safer place. Do not close all unless opposite strong move appears.",
        "new_entry_rule": "Do not enter late after strong move. Wait for price to come back to a better area first.",
        "last_candle": last_m,
        "time": _now().isoformat()
    }

    _STRONG_MEMORY[sym] = report
    return report

def apply_strong_move(result, candles=None):
    if result.get("status") != "live":
        return result
    sym = result.get("asset")
    if candles is None:
        candles = []
    sm = detect_strong_move(sym, candles, result)
    result["strong_move"] = sm

    # Add alert even when entry is not allowed.
    if sm.get("detected"):
        alerts = result.get("alerts") or []
        alerts.append({
            "asset": sym,
            "type": "STRONG_MOVE_TP",
            "title": sm.get("message"),
            "title_simple": sm.get("simple_message"),
            "direction": sm.get("direction"),
            "severity": "trade_management",
            "action": "TAKE PROFIT / PROTECT PROFIT" if sm.get("detected") else "WAIT",
            "action_simple": sm.get("action_if_in_trade"),
            "reason": sm.get("simple_message"),
            "price": result.get("price"),
            "time": sm.get("time")
        })
        result["alerts"] = alerts[-20:]

        # Do not force a new entry; this is management.
        result["management_alert"] = sm

    return result

def strong_move_report():
    return {"strong_moves": list(_STRONG_MEMORY.values())}
