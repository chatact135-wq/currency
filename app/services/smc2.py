
def rp(sym, value, assets):
    pip = assets[sym]["pip"]
    if pip >= 0.1:
        return round(float(value), 2)
    if pip >= 0.01:
        return round(float(value), 3)
    return round(float(value), 5)

def recent_swings(candles, lookback=30):
    data = candles[-lookback:] if len(candles) >= lookback else candles
    highs = [x["high"] for x in data]
    lows = [x["low"] for x in data]
    return {
        "swing_high": max(highs),
        "swing_low": min(lows),
        "mid": (max(highs) + min(lows)) / 2,
        "recent": data
    }

def fvg_zone(candles):
    if len(candles) < 3:
        return {"direction": "NEUTRAL", "zone": None, "strength": 0, "message": "No FVG data."}
    a, b, c = candles[-3], candles[-2], candles[-1]
    # Bullish FVG: current low above candle-3 high
    if c["low"] > a["high"]:
        return {
            "direction": "BUY",
            "zone": [a["high"], c["low"]],
            "strength": abs(c["low"] - a["high"]),
            "message": "Bullish FVG zone detected."
        }
    # Bearish FVG: current high below candle-3 low
    if c["high"] < a["low"]:
        return {
            "direction": "SELL",
            "zone": [c["high"], a["low"]],
            "strength": abs(a["low"] - c["high"]),
            "message": "Bearish FVG zone detected."
        }
    return {"direction": "NEUTRAL", "zone": None, "strength": 0, "message": "No clean FVG now."}

def liquidity_sweep(candles, swings):
    last = candles[-1]
    prev_high = max(x["high"] for x in swings["recent"][:-1])
    prev_low = min(x["low"] for x in swings["recent"][:-1])
    if last["low"] < prev_low and last["close"] > prev_low:
        return {
            "direction": "BUY",
            "level": prev_low,
            "message": "Sell-side liquidity swept, bullish reaction possible."
        }
    if last["high"] > prev_high and last["close"] < prev_high:
        return {
            "direction": "SELL",
            "level": prev_high,
            "message": "Buy-side liquidity swept, bearish reaction possible."
        }
    return {"direction": "NEUTRAL", "level": None, "message": "No liquidity sweep confirmed."}

def structure_state(candles, swings):
    last = candles[-1]
    prev_high = max(x["high"] for x in swings["recent"][:-3])
    prev_low = min(x["low"] for x in swings["recent"][:-3])
    if last["close"] > prev_high:
        return {"direction": "BUY", "level": prev_high, "message": "Bullish BOS/CHOCH above recent structure."}
    if last["close"] < prev_low:
        return {"direction": "SELL", "level": prev_low, "message": "Bearish BOS/CHOCH below recent structure."}
    return {"direction": "NEUTRAL", "level": None, "message": "No confirmed BOS/CHOCH."}

def premium_discount(price, swings):
    if price <= swings["mid"]:
        return {"zone": "discount", "buy_ok": True, "sell_ok": False, "message": "Price is in discount half of recent range."}
    return {"zone": "premium", "buy_ok": False, "sell_ok": True, "message": "Price is in premium half of recent range."}

def order_block_zone(candles, direction, atr):
    # Approximate OB from last opposite candle before current push.
    search = candles[-12:-1]
    if direction == "BUY":
        candidates = [x for x in reversed(search) if x["close"] < x["open"]]
        if candidates:
            ob = candidates[0]
            return {"zone": [ob["low"], ob["high"]], "message": "Bullish order-block proxy found."}
    if direction == "SELL":
        candidates = [x for x in reversed(search) if x["close"] > x["open"]]
        if candidates:
            ob = candidates[0]
            return {"zone": [ob["low"], ob["high"]], "message": "Bearish order-block proxy found."}
    return {"zone": None, "message": "No nearby order-block proxy."}

def smc2_analysis(symbol, candles, indicators, assets):
    price = indicators["price"]
    atr = indicators["atr"]
    swings = recent_swings(candles)
    fvg = fvg_zone(candles)
    sweep = liquidity_sweep(candles, swings)
    structure = structure_state(candles, swings)
    pd = premium_discount(price, swings)

    buy = 0
    sell = 0
    reasons = []

    # Context: structure and sweep are direction makers
    for item, score in [(structure, 28), (sweep, 24), (fvg, 18)]:
        if item["direction"] == "BUY":
            buy += score
            reasons.append(item["message"])
        elif item["direction"] == "SELL":
            sell += score
            reasons.append(item["message"])

    # Premium/discount filter
    if pd["buy_ok"]:
        buy += 8
        reasons.append("Discount supports BUY context.")
    if pd["sell_ok"]:
        sell += 8
        reasons.append("Premium supports SELL context.")

    direction = "BUY" if buy - sell >= 15 else "SELL" if sell - buy >= 15 else "NEUTRAL"
    confidence = min(95, max(20, abs(buy - sell) + 35)) if direction != "NEUTRAL" else 35

    ob = order_block_zone(candles, direction, atr)

    # Zone priority: FVG first if aligned, otherwise OB, otherwise micro range
    zone = None
    zone_source = "none"
    if fvg["direction"] == direction and fvg["zone"]:
        zone = fvg["zone"]
        zone_source = "FVG"
    elif ob["zone"]:
        zone = ob["zone"]
        zone_source = "Order Block Proxy"
    elif direction == "BUY":
        zone = [price - atr * 0.35, price - atr * 0.10]
        zone_source = "Micro Discount Pullback"
    elif direction == "SELL":
        zone = [price + atr * 0.10, price + atr * 0.35]
        zone_source = "Micro Premium Pullback"

    if direction == "BUY":
        trigger = max(price + atr * 0.08, swings["mid"])
        invalidation = min(swings["swing_low"], zone[0] if zone else price - atr * 0.5)
        trigger_text = f"BUY only after bullish close above {rp(symbol, trigger, assets)} or reaction from zone."
    elif direction == "SELL":
        trigger = min(price - atr * 0.08, swings["mid"])
        invalidation = max(swings["swing_high"], zone[1] if zone else price + atr * 0.5)
        trigger_text = f"SELL only after bearish close below {rp(symbol, trigger, assets)} or rejection from zone."
    else:
        trigger = None
        invalidation = None
        trigger_text = "No SMC trigger."

    if direction == "BUY":
        decision = "SMC_BUY_CONTEXT"
    elif direction == "SELL":
        decision = "SMC_SELL_CONTEXT"
    else:
        decision = "SMC_NEUTRAL"

    return {
        "decision": decision,
        "direction": direction,
        "confidence": round(confidence, 1),
        "context": {
            "structure": structure,
            "liquidity_sweep": sweep,
            "premium_discount": pd,
            "reason_summary": reasons[:6]
        },
        "zone": {
            "source": zone_source,
            "low": rp(symbol, min(zone), assets) if zone else None,
            "high": rp(symbol, max(zone), assets) if zone else None,
            "raw": zone
        },
        "trigger": {
            "level": rp(symbol, trigger, assets) if trigger else None,
            "text": trigger_text
        },
        "invalidation": rp(symbol, invalidation, assets) if invalidation else None,
        "fvg": fvg,
        "order_block": ob
    }
