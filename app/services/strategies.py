def alert(name, direction, score, message, active=True):
    return {"name": name, "direction": direction, "score": score, "message": message, "active": active}

def sb_model(candles, ind):
    last = candles[-1]
    alerts = []
    score = 0

    if last["low"] < ind["prev_low"] and last["close"] > ind["prev_low"]:
        alerts.append(alert("SB Model", "BUY", 18, "Bullish liquidity sweep below previous low."))
        score += 18
    elif last["high"] > ind["prev_high"] and last["close"] < ind["prev_high"]:
        alerts.append(alert("SB Model", "SELL", -18, "Bearish liquidity sweep above previous high."))
        score -= 18

    body = abs(last["close"] - last["open"])
    candle_range = max(0.0000001, last["high"] - last["low"])
    if body / candle_range > 0.62:
        if last["close"] > last["open"]:
            alerts.append(alert("SB Model", "BUY", 10, "Bullish displacement candle."))
            score += 10
        else:
            alerts.append(alert("SB Model", "SELL", -10, "Bearish displacement candle."))
            score -= 10

    return {"score": score, "alerts": alerts}

def smc_model(candles, ind):
    alerts = []
    score = 0
    last = candles[-1]
    recent = candles[-15:-1]
    hi = max(c["high"] for c in recent)
    lo = min(c["low"] for c in recent)

    if last["close"] > hi:
        alerts.append(alert("SMC Model", "BUY", 16, "Bullish BOS/CHOCH close above recent structure."))
        score += 16
    elif last["close"] < lo:
        alerts.append(alert("SMC Model", "SELL", -16, "Bearish BOS/CHOCH close below recent structure."))
        score -= 16

    a, b, c = candles[-3], candles[-2], candles[-1]
    if c["low"] > a["high"]:
        alerts.append(alert("SMC Model", "BUY", 12, "Bullish FVG detected."))
        score += 12
    elif c["high"] < a["low"]:
        alerts.append(alert("SMC Model", "SELL", -12, "Bearish FVG detected."))
        score -= 12

    return {"score": score, "alerts": alerts}

def raven_model(candles, ind):
    alerts = []
    score = 0

    if ind["pressure"] > 0.25:
        alerts.append(alert("RAVEN Composite", "BUY", 10, "RAVEN bullish candle pressure."))
        score += 10
    elif ind["pressure"] < -0.25:
        alerts.append(alert("RAVEN Composite", "SELL", -10, "RAVEN bearish candle pressure."))
        score -= 10

    if ind["momentum"] > 0.00025:
        alerts.append(alert("RAVEN Composite", "BUY", 12, "RAVEN bullish acceleration."))
        score += 12
    elif ind["momentum"] < -0.00025:
        alerts.append(alert("RAVEN Composite", "SELL", -12, "RAVEN bearish acceleration."))
        score -= 12

    if ind["trend"] == "bullish":
        alerts.append(alert("RAVEN Composite", "BUY", 8, "RAVEN bullish EMA alignment."))
        score += 8
    elif ind["trend"] == "bearish":
        alerts.append(alert("RAVEN Composite", "SELL", -8, "RAVEN bearish EMA alignment."))
        score -= 8

    return {"score": score, "alerts": alerts}

def profile_model(ind):
    price = ind["price"]
    profile = ind["profile"]
    alerts = []
    score = 0

    if price > profile["vah"]:
        alerts.append(alert("Frequency Profile", "BUY", 8, "Price above value area high; bullish auction pressure."))
        score += 8
    elif price < profile["val"]:
        alerts.append(alert("Frequency Profile", "SELL", -8, "Price below value area low; bearish auction pressure."))
        score -= 8
    elif abs(price - profile["poc"]) <= ind["atr"] * 0.25:
        alerts.append(alert("Frequency Profile", "NEUTRAL", 0, "Price near POC; balance area, avoid forcing."))
    return {"score": score, "alerts": alerts, "profile": profile}

def all_strategy_alerts(candles, ind):
    models = [sb_model(candles, ind), smc_model(candles, ind), raven_model(candles, ind), profile_model(ind)]
    score = sum(m["score"] for m in models)
    alerts = []
    for m in models:
        alerts.extend(m["alerts"])
    return {"score": score, "alerts": alerts, "models": models}
