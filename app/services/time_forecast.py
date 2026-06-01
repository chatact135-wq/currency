
def _fmt_minutes(minutes):
    if minutes is None:
        return "Unknown"
    if minutes < 1:
        return "less than 1 minute"
    if minutes < 60:
        return f"about {round(minutes)} minutes"
    return f"about {round(minutes/60, 1)} hours"

def recent_speed(candles, lookback=8):
    if len(candles) < 3:
        return {"per_candle": 0, "direction": "SIDEWAYS", "confidence": 0}
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    first = recent[0]["close"]
    last = recent[-1]["close"]
    net = last - first
    ranges = [abs(x["high"] - x["low"]) for x in recent]
    avg_range = sum(ranges) / max(1, len(ranges))
    per_candle = abs(net) / max(1, len(recent)-1)
    direction = "UP" if net > 0 else "DOWN" if net < 0 else "SIDEWAYS"
    confidence = min(100, round((per_candle / avg_range) * 100, 1)) if avg_range else 0
    return {"per_candle": per_candle, "avg_range": avg_range, "direction": direction, "confidence": confidence, "net": net}

def estimate_minutes(distance, speed_per_candle, candle_minutes=5):
    if distance is None or speed_per_candle is None or speed_per_candle <= 0:
        return None
    candles_needed = abs(distance) / speed_per_candle
    return candles_needed * candle_minutes

def parse_primary_level(plan):
    lvl = plan.get("primary_level")
    try:
        return float(lvl) if lvl is not None else None
    except Exception:
        return None

def forecast(symbol, candles, price, final_action, plan, indicators):
    spd = recent_speed(candles)
    speed = max(spd.get("per_candle", 0), indicators.get("atr", 0) * 0.08)

    direction = "UP" if "BUY" in (final_action or "") else "DOWN" if "SELL" in (final_action or "") else spd["direction"]
    trigger_level = parse_primary_level(plan)

    trigger_distance = None
    if trigger_level is not None:
        trigger_distance = trigger_level - price if direction == "UP" else price - trigger_level

    tp1 = plan.get("tp1_partial_close")
    stop = plan.get("stop_loss") or plan.get("invalidation")

    try:
        tp1 = float(tp1) if tp1 is not None else None
    except Exception:
        tp1 = None
    try:
        stop = float(stop) if stop is not None else None
    except Exception:
        stop = None

    tp_distance = None
    stop_distance = None
    if tp1 is not None:
        tp_distance = tp1 - price if direction == "UP" else price - tp1
    if stop is not None:
        stop_distance = price - stop if direction == "UP" else stop - price

    trigger_minutes = estimate_minutes(trigger_distance, speed)
    tp_minutes = estimate_minutes(tp_distance, speed)
    stop_minutes = estimate_minutes(stop_distance, speed)

    if "ENTER" in (final_action or "") or "ACTIVE" in (final_action or ""):
        summary = f"{direction} trade is active/allowed. Trigger timing: {_fmt_minutes(trigger_minutes)}."
    elif "WAIT" in (final_action or "") or "WATCH" in (final_action or "") or "SETUP" in (final_action or ""):
        summary = f"{direction} is possible, but entry is not allowed yet. Estimated trigger time: {_fmt_minutes(trigger_minutes)}."
    elif "CANCEL" in (final_action or "") or "NO TRADE" in (final_action or ""):
        summary = "No trade. Conditions are not stable enough."
    else:
        summary = f"Expected movement direction: {direction}. Estimated trigger time: {_fmt_minutes(trigger_minutes)}."

    return {
        "direction_forecast": direction,
        "recent_speed_direction": spd["direction"],
        "speed_confidence": spd["confidence"],
        "estimated_time_to_trigger_minutes": round(trigger_minutes, 1) if trigger_minutes is not None else None,
        "estimated_time_to_trigger_text": _fmt_minutes(trigger_minutes),
        "estimated_time_to_tp1_minutes": round(tp_minutes, 1) if tp_minutes is not None else None,
        "estimated_time_to_tp1_text": _fmt_minutes(tp_minutes),
        "estimated_time_to_invalidation_minutes": round(stop_minutes, 1) if stop_minutes is not None else None,
        "estimated_time_to_invalidation_text": _fmt_minutes(stop_minutes),
        "trigger_level": trigger_level,
        "summary": summary
    }
