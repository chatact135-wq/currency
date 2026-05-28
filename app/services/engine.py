from app.config import settings
from app.services.market import candles, normalize, ASSETS, LiveDataError
from app.services.indicators import build
from app.services.strategies import all_strategy_alerts
from app.services.session import info as session_info
from app.services.news import get as news_get

def rp(symbol, value):
    pip = ASSETS[symbol]["pip"]
    if pip >= 0.1:
        return round(float(value), 2)
    if pip >= 0.01:
        return round(float(value), 3)
    return round(float(value), 5)

def choose_direction(total_score, alerts):
    # Strategy alerts are allowed to create WATCH state, never hidden by WAIT.
    if total_score > 0:
        return "BUY"
    if total_score < 0:
        return "SELL"

    buy_alerts = sum(1 for a in alerts if a["direction"] == "BUY")
    sell_alerts = sum(1 for a in alerts if a["direction"] == "SELL")
    if buy_alerts > sell_alerts:
        return "BUY"
    if sell_alerts > buy_alerts:
        return "SELL"
    return "NEUTRAL"

def action_from_score(score, direction):
    abs_score = abs(score)
    if direction == "NEUTRAL":
        return "WAIT"
    if abs_score >= settings.EXECUTE_SCORE + 20:
        return f"STRONG {direction}"
    if abs_score >= settings.EXECUTE_SCORE:
        return f"SCALP {direction}"
    if abs_score >= settings.WATCH_SCORE:
        return f"{direction} WATCH"
    return "WAIT"

def pips(symbol, a, b):
    return round(abs(a - b) / ASSETS[symbol]["pip"], 1)

def build_plan(symbol, action, direction, ind):
    price = ind["price"]
    pip = ASSETS[symbol]["pip"]
    atr = ind["atr"]

    if action == "WAIT":
        return {
            "has_entry": False,
            "entry_display": "No exact entry yet — waiting for trigger",
            "trigger_level": rp(symbol, ind["resistance_soft"] if direction == "BUY" else ind["support_soft"] if direction == "SELL" else price),
            "stop_loss": None,
            "invalidation": None,
            "tp1_partial_close": None,
            "tp2": None,
            "full_close": None,
            "pips": None,
            "after_tp1": "No trade management until entry is active.",
        }

    if "WATCH" in action:
        # Watch has trigger level but no executable entry.
        trigger = ind["resistance_soft"] if direction == "BUY" else ind["support_soft"]
        return {
            "has_entry": False,
            "entry_display": f"Watch only — trigger near {rp(symbol, trigger)}",
            "trigger_level": rp(symbol, trigger),
            "stop_loss": None,
            "invalidation": None,
            "tp1_partial_close": None,
            "tp2": None,
            "full_close": None,
            "pips": None,
            "after_tp1": "Wait for upgrade to SCALP/SELL/BUY before entering.",
        }

    # Executable interval: tight, clear, and directionally displayed.
    if pip == 0.0001:
        width = max(3*pip, min(8*pip, atr*0.16))
    elif pip == 0.10:
        width = max(1.0, min(4.0, atr*0.18))
    else:
        width = max(0.05, min(0.20, atr*0.18))

    if direction == "BUY":
        start = price - width * 0.35
        end = price + width * 0.65
        low, high = min(start, end), max(start, end)
        sl = low - max(width*1.6, atr*0.32)
        tp1 = high + max(width*1.3, atr*0.35)
        tp2 = high + max(width*2.3, atr*0.65)
        full = high + max(width*3.0, atr*0.85)
        entry_display = f"{rp(symbol, low)} → {rp(symbol, high)}"
        interval_direction = "ascending"
    elif direction == "SELL":
        start = price + width * 0.35
        end = price - width * 0.65
        high, low = max(start, end), min(start, end)
        sl = high + max(width*1.6, atr*0.32)
        tp1 = low - max(width*1.3, atr*0.35)
        tp2 = low - max(width*2.3, atr*0.65)
        full = low - max(width*3.0, atr*0.85)
        entry_display = f"{rp(symbol, high)} → {rp(symbol, low)}"
        interval_direction = "descending"
    else:
        return build_plan(symbol, "WAIT", direction, ind)

    return {
        "has_entry": True,
        "entry_display": entry_display,
        "interval_direction": interval_direction,
        "stop_loss": rp(symbol, sl),
        "invalidation": rp(symbol, sl),
        "tp1_partial_close": rp(symbol, tp1),
        "tp2": rp(symbol, tp2),
        "full_close": rp(symbol, full),
        "pips": pips(symbol, low, high),
        "after_tp1": "Close 50% and move SL to breakeven.",
    }

def signal(asset):
    symbol = normalize(asset)
    try:
        live = candles(symbol)
    except LiveDataError as exc:
        return {"status": "error", "asset": symbol, "display": ASSETS[symbol]["display"], "message": "LIVE DATA ERROR — no live price shown.", "error": str(exc)}

    cs = live["candles"]
    ind = build(cs)
    strategy = all_strategy_alerts(cs, ind)
    ses = session_info()
    nw = news_get(symbol)

    score = strategy["score"]
    alerts = strategy["alerts"]

    # Additional non-strategy bias, smaller weight.
    if ind["trend"] == "bullish":
        score += 8
        alerts.append({"name":"Trend Filter","direction":"BUY","score":8,"message":"EMA trend bullish.","active":True})
    elif ind["trend"] == "bearish":
        score -= 8
        alerts.append({"name":"Trend Filter","direction":"SELL","score":-8,"message":"EMA trend bearish.","active":True})

    score += ses["score"]
    score += nw["score"]

    direction = choose_direction(score, alerts)
    action = action_from_score(score, direction)
    plan = build_plan(symbol, action, direction, ind)

    if action == "WAIT":
        warning = "No clean execution; watch strategy alerts only."
    elif "WATCH" in action:
        warning = f"{action}: alert detected, but wait for executable trigger."
    elif direction == "SELL":
        warning = "Use the descending SELL interval only."
    else:
        warning = "Use the ascending BUY interval only."

    timer = 10*60 if "WATCH" in action else 30*60 if action != "WAIT" else 5*60

    return {
        "status": "live",
        "asset": symbol,
        "display": ASSETS[symbol]["display"],
        "price": rp(symbol, ind["price"]),
        "source": live["source"],
        "source_time": live["source_time"],
        "cache_age": live["cache_age"],
        "score": round(score, 1),
        "bias": direction.lower(),
        "action": action,
        "signal_state": "executable" if plan["has_entry"] else "watch" if "WATCH" in action else "wait",
        "warning": warning,
        "plan": plan,
        "timer_seconds": timer,
        "indicators": {
            "trend": ind["trend"],
            "rsi": ind["rsi"],
            "momentum": round(ind["momentum"], 6),
            "pressure": round(ind["pressure"], 3),
            "atr": rp(symbol, ind["atr"]),
        },
        "volume_profile": {
            "poc": rp(symbol, ind["profile"]["poc"]),
            "val": rp(symbol, ind["profile"]["val"]),
            "vah": rp(symbol, ind["profile"]["vah"]),
            "note": ind["profile"]["note"],
        },
        "strategy_alerts": alerts,
        "news": nw,
        "session": ses,
        "logic_note": "V7 separates strategy alerts from executable entry. WAIT/WATCH never shows fake exact entry.",
    }
