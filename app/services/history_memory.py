
from app.services.market import ASSETS, normalize, stored_candles

def level_memory(db, asset, level, direction, lookback=500):
    symbol = normalize(asset)
    candles = stored_candles(db, symbol, lookback)
    if not candles or level is None:
        return {
            "status": "no_history",
            "level": level,
            "touches": 0,
            "breaks": 0,
            "continuations": 0,
            "success_rate": None,
            "message": "No stored history for this level yet."
        }

    pip = ASSETS[symbol]["pip"]
    tolerance = 4 * pip if pip < 0.01 else 1.5 if pip >= 0.1 else 0.08

    touches = 0
    breaks = 0
    continuations = 0

    for i in range(0, max(0, len(candles) - 4)):
        c = candles[i]
        near = c["low"] <= level + tolerance and c["high"] >= level - tolerance
        if near:
            touches += 1

        if direction == "BUY":
            broke = c["close"] > level
            if broke:
                breaks += 1
                future_high = max(x["high"] for x in candles[i+1:i+4]) if i+4 <= len(candles) else c["high"]
                if future_high - c["close"] >= 3 * pip:
                    continuations += 1
        elif direction == "SELL":
            broke = c["close"] < level
            if broke:
                breaks += 1
                future_low = min(x["low"] for x in candles[i+1:i+4]) if i+4 <= len(candles) else c["low"]
                if c["close"] - future_low >= 3 * pip:
                    continuations += 1

    success = round(continuations / breaks * 100, 1) if breaks else None
    if success is None:
        msg = "This level has not broken enough times in stored history."
    elif success >= 58:
        msg = "Historical memory supports this trigger level."
    elif success >= 45:
        msg = "Historical memory is mixed around this level."
    else:
        msg = "Historical memory is weak around this level."

    return {
        "status": "ok",
        "level": level,
        "touches": touches,
        "breaks": breaks,
        "continuations": continuations,
        "success_rate": success,
        "message": msg
    }
