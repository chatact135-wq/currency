def liquidity_sweep(candles, ind):
    last = candles[-1]
    if last["low"] < ind["prev_low"] and last["close"] > ind["prev_low"]:
        return {"direction":"buy", "score":18, "matched":"Bullish liquidity sweep below previous low."}
    if last["high"] > ind["prev_high"] and last["close"] < ind["prev_high"]:
        return {"direction":"sell", "score":-18, "matched":"Bearish liquidity sweep above previous high."}
    return {"direction":"none", "score":0, "missing":"No liquidity sweep."}

def fvg(candles):
    if len(candles) < 4:
        return {"direction":"none", "score":0, "missing":"Not enough candles for FVG."}
    a,b,c = candles[-3], candles[-2], candles[-1]
    if c["low"] > a["high"]:
        return {"direction":"buy", "score":12, "zone":{"low":a["high"], "high":c["low"]}, "matched":"Bullish FVG detected."}
    if c["high"] < a["low"]:
        return {"direction":"sell", "score":-12, "zone":{"low":c["high"], "high":a["low"]}, "matched":"Bearish FVG detected."}
    return {"direction":"none", "score":0, "missing":"No clean FVG."}

def bos_choch(candles, ind):
    last = candles[-1]
    recent = candles[-15:-1]
    hi = max(c["high"] for c in recent)
    lo = min(c["low"] for c in recent)
    if last["close"] > hi:
        return {"direction":"buy", "score":16, "matched":"Bullish BOS/CHOCH close above recent structure."}
    if last["close"] < lo:
        return {"direction":"sell", "score":-16, "matched":"Bearish BOS/CHOCH close below recent structure."}
    return {"direction":"none", "score":0, "missing":"No BOS/CHOCH confirmation."}

def order_block(candles, direction):
    recent = candles[-14:]
    if direction == "buy":
        choices = [c for c in recent if c["close"] < c["open"]]
    elif direction == "sell":
        choices = [c for c in recent if c["close"] > c["open"]]
    else:
        choices = []
    base = choices[-1] if choices else recent[-2]
    return {"low": min(base["low"], base["open"], base["close"]), "high": max(base["high"], base["open"], base["close"])}

def analyze(candles, ind):
    parts = [liquidity_sweep(candles, ind), fvg(candles), bos_choch(candles, ind)]
    score = sum(p.get("score",0) for p in parts)
    matched = [p["matched"] for p in parts if "matched" in p]
    missing = [p["missing"] for p in parts if "missing" in p]
    return {"score":score, "matched":matched, "missing":missing, "parts":parts}
