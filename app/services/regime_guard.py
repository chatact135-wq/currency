
from app.services.market import ASSETS, normalize

def rp(sym, v):
    pip = ASSETS[sym]["pip"]
    if pip >= 0.1:
        return round(float(v), 2)
    if pip >= 0.01:
        return round(float(v), 3)
    return round(float(v), 5)

def candle_features(candles, lookback=6):
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    if not recent:
        return {"avg_range":0,"last_range":0,"last_body":0,"wick_ratio":0,"direction":"SIDEWAYS"}
    last = recent[-1]
    ranges = [abs(x["high"]-x["low"]) for x in recent]
    avg = sum(ranges)/max(1,len(ranges))
    last_range = abs(last["high"]-last["low"])
    body = abs(last["close"]-last["open"])
    wick_ratio = max(0,last_range-body)/last_range if last_range else 0
    direction = "UP" if last["close"] > last["open"] else "DOWN" if last["close"] < last["open"] else "SIDEWAYS"
    return {"avg_range":avg,"last_range":last_range,"last_body":body,"wick_ratio":wick_ratio,"direction":direction}

def market_regime(sym, candles, signal_result):
    sym = normalize(sym)
    news = signal_result.get("news") or {}
    fresh = signal_result.get("data_fresh", True)
    live_age = signal_result.get("live_price_cache_age")
    f = candle_features(candles)
    pip = ASSETS[sym]["pip"]

    regimes = []
    risk = 0
    reasons = []

    if fresh is False:
        regimes.append("DATA_STALE")
        risk += 100
        reasons.append("Live data is stale. Trading blocked.")

    if news.get("mode") == "NEWS_WAIT":
        regimes.append("NEWS_WAIT")
        risk += 80
        reasons.append("News is close. New entries blocked.")
    elif news.get("mode") == "POST_NEWS_IMPULSE":
        regimes.append("POST_NEWS_IMPULSE")
        risk += 35
        reasons.append("Post-news impulse. Use only breakout/retest with small risk.")

    if f["avg_range"] and f["last_range"] > f["avg_range"] * 2.2:
        regimes.append("VOLATILITY_SPIKE")
        risk += 35
        reasons.append("Last candle is much larger than recent candles.")

    if f["wick_ratio"] > 0.55 and f["last_range"] > 4*pip:
        regimes.append("LIQUIDITY_SWEEP_RISK")
        risk += 25
        reasons.append("Large wick detected. Possible liquidity sweep / fake breakout.")

    if f["avg_range"] and f["avg_range"] < 2*pip:
        regimes.append("LOW_LIQUIDITY")
        risk += 20
        reasons.append("Recent candles are too small. Low-liquidity/noise risk.")

    if live_age is not None and live_age > 10:
        regimes.append("API_LAG_RISK")
        risk += 30
        reasons.append("Live quote age is elevated.")

    if not regimes:
        regimes.append("NORMAL")
        reasons.append("No major regime risk detected.")

    if risk >= 80:
        mode = "BLOCK_TRADE"
    elif risk >= 45:
        mode = "REDUCE_RISK"
    elif risk >= 20:
        mode = "CAUTION"
    else:
        mode = "NORMAL"

    return {"mode":mode,"regimes":regimes,"risk_score":risk,"reasons":reasons,"candle_features":f}

def trigger_state(sym, price, bias, entry, safe_entry, cancel_level):
    sym = normalize(sym)
    pip = ASSETS[sym]["pip"]
    hold_buffer = 1.5*pip
    chase_limit = 5*pip if pip == 0.0001 else 2.5 if pip >= 0.1 else 0.10

    if bias not in ["BUY","SELL"] or entry is None:
        return {"state":"NO_TRIGGER","message":"No clear trigger yet.","entry_permission":"NO_ENTRY"}

    price = float(price)
    entry = float(entry)
    safe_entry = float(safe_entry) if safe_entry is not None else entry
    cancel_level = float(cancel_level) if cancel_level is not None else None

    if bias == "BUY":
        if cancel_level is not None and price <= cancel_level:
            return {"state":"FAILED_CANCEL","message":"BUY failed. Price broke cancel level. Watch SELL instead.","entry_permission":"NO_ENTRY"}
        if price < entry:
            return {"state":"NOT_REACHED","message":f"BUY trigger not reached. Watch above {rp(sym, entry)}.","entry_permission":"NO_ENTRY"}
        if price >= entry + chase_limit:
            return {"state":"TOO_LATE_DO_NOT_CHASE","message":"BUY moved too far after trigger. Do not chase. Wait pullback/retest.","entry_permission":"NO_ENTRY"}
        if entry <= price < entry + hold_buffer:
            return {"state":"BROKEN_WAIT_HOLD","message":"BUY trigger just broke. Wait hold / M1 close / retest.","entry_permission":"WAIT_HOLD"}
        if price >= safe_entry:
            return {"state":"ACTIVE","message":"BUY trigger active. Entry allowed only if regime is safe.","entry_permission":"ENTRY_ALLOWED"}
        return {"state":"BROKEN_WAIT_HOLD","message":"BUY trigger broken but not fully confirmed. Wait hold/retest.","entry_permission":"WAIT_HOLD"}

    if bias == "SELL":
        if cancel_level is not None and price >= cancel_level:
            return {"state":"FAILED_CANCEL","message":"SELL failed. Price broke cancel level. Watch BUY instead.","entry_permission":"NO_ENTRY"}
        if price > entry:
            return {"state":"NOT_REACHED","message":f"SELL trigger not reached. Watch below {rp(sym, entry)}.","entry_permission":"NO_ENTRY"}
        if price <= entry - chase_limit:
            return {"state":"TOO_LATE_DO_NOT_CHASE","message":"SELL moved too far after trigger. Do not chase. Wait pullback/retest.","entry_permission":"NO_ENTRY"}
        if entry - hold_buffer < price <= entry:
            return {"state":"BROKEN_WAIT_HOLD","message":"SELL trigger just broke. Wait hold / M1 close / retest.","entry_permission":"WAIT_HOLD"}
        if price <= safe_entry:
            return {"state":"ACTIVE","message":"SELL trigger active. Entry allowed only if regime is safe.","entry_permission":"ENTRY_ALLOWED"}
        return {"state":"BROKEN_WAIT_HOLD","message":"SELL trigger broken but not fully confirmed. Wait hold/retest.","entry_permission":"WAIT_HOLD"}

    return {"state":"NO_TRIGGER","message":"No trigger.","entry_permission":"NO_ENTRY"}

def apply_regime_to_permission(result, regime, tstate):
    result["regime_guard"] = regime
    result["trigger_state"] = tstate

    if regime["mode"] == "BLOCK_TRADE":
        result["final_action"] = "NO TRADE - REGIME BLOCK"
        result["entry_permission"] = "NO_ENTRY"
        result["warning"] = "Trade blocked: " + " ".join(regime["reasons"])
        return result

    if tstate.get("state") == "TOO_LATE_DO_NOT_CHASE":
        result["final_action"] = "NO TRADE - DO NOT CHASE"
        result["entry_permission"] = "NO_ENTRY"
        result["warning"] = tstate.get("message")
        return result

    if tstate.get("state") == "FAILED_CANCEL":
        result["final_action"] = "CANCEL - TRIGGER FAILED"
        result["entry_permission"] = "NO_ENTRY"
        result["warning"] = tstate.get("message")
        return result

    if tstate.get("entry_permission") == "ENTRY_ALLOWED":
        if regime["mode"] == "NORMAL":
            result["entry_permission"] = "ENTRY_ALLOWED"
            result["warning"] = tstate.get("message")
        elif regime["mode"] == "CAUTION":
            result["entry_permission"] = "ENTRY_ALLOWED_SMALL_RISK"
            result["warning"] = tstate.get("message") + " Caution regime: use smaller risk."
        else:
            result["entry_permission"] = "NO_ENTRY"
            result["warning"] = "Regime risk too high for entry."
        return result

    if tstate.get("entry_permission") == "WAIT_HOLD":
        result["entry_permission"] = "WAIT_HOLD"
        result["warning"] = tstate.get("message")
        return result

    return result
