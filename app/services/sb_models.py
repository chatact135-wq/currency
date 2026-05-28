def detect_liquidity_sweep(candles, ind):
    last = candles[-1]
    prev_high, prev_low = ind["prev_high"], ind["prev_low"]
    bearish = last["high"] > prev_high and last["close"] < prev_high
    bullish = last["low"] < prev_low and last["close"] > prev_low
    if bullish:
        return {"type": "bullish_liquidity_sweep", "score": 0.32, "reason": "Liquidity swept below previous low and closed back above it."}
    if bearish:
        return {"type": "bearish_liquidity_sweep", "score": -0.32, "reason": "Liquidity swept above previous high and closed back below it."}
    return {"type": "none", "score": 0.0, "reason": "No clean liquidity sweep detected."}

def detect_fvg(candles):
    if len(candles) < 5:
        return {"type": "none", "score": 0.0, "zone": None, "reason": "Not enough candles for FVG."}
    a, _, c = candles[-3], candles[-2], candles[-1]
    if c["low"] > a["high"]:
        return {"type": "bullish_fvg", "score": 0.22, "zone": {"low": a["high"], "high": c["low"]}, "reason": "Bullish Fair Value Gap detected."}
    if c["high"] < a["low"]:
        return {"type": "bearish_fvg", "score": -0.22, "zone": {"low": c["high"], "high": a["low"]}, "reason": "Bearish Fair Value Gap detected."}
    return {"type": "none", "score": 0.0, "zone": None, "reason": "No clean FVG detected."}

def detect_bos_choch(candles, ind):
    last = candles[-1]
    recent = candles[-12:]
    prior = recent[:-1]
    recent_high = max(c["high"] for c in prior)
    recent_low = min(c["low"] for c in prior)
    if last["close"] > recent_high and ind["trend"] == "bullish":
        return {"type": "bullish_bos", "score": 0.24, "reason": "Bullish Break of Structure detected."}
    if last["close"] < recent_low and ind["trend"] == "bearish":
        return {"type": "bearish_bos", "score": -0.24, "reason": "Bearish Break of Structure detected."}
    if last["close"] > recent_high and ind["trend"] == "bearish":
        return {"type": "bullish_choch", "score": 0.18, "reason": "Bullish CHOCH after bearish structure."}
    if last["close"] < recent_low and ind["trend"] == "bullish":
        return {"type": "bearish_choch", "score": -0.18, "reason": "Bearish CHOCH after bullish structure."}
    return {"type": "none", "score": 0.0, "reason": "No BOS/CHOCH confirmation."}

def order_block_zone(candles, direction):
    lookback = candles[-12:]
    if "BUY" in direction:
        matches = [c for c in lookback if c["close"] < c["open"]]
    elif "SELL" in direction:
        matches = [c for c in lookback if c["close"] > c["open"]]
    else:
        matches = []
    base = matches[-1] if matches else lookback[-2]
    return {"low": min(base["open"], base["close"], base["low"]), "high": max(base["open"], base["close"], base["high"])}

def analyze_sb(candles, ind):
    sweep = detect_liquidity_sweep(candles, ind)
    fvg = detect_fvg(candles)
    structure = detect_bos_choch(candles, ind)
    score = sweep["score"] + fvg["score"] + structure["score"]
    return {"score": round(score, 3), "liquidity_sweep": sweep, "fvg": fvg, "structure": structure, "reasons": [sweep["reason"], fvg["reason"], structure["reason"]]}
