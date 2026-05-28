from app.services.market_data import get_candles, normalize_asset, SUPPORTED_ASSETS, LiveDataError
from app.services.indicators import build
from app.services.sb_models import analyze_sb, order_block_zone
from app.services.session_engine import session_info
from app.services.news_engine import news


def rp(symbol, value):
    pip = SUPPORTED_ASSETS[symbol]["pip"]
    if pip >= 0.1:
        return round(float(value), 2)
    if pip >= 0.01:
        return round(float(value), 3)
    return round(float(value), 5)


def choose_action(score):
    if score >= 0.78:
        return "STRONG BUY"
    if score >= 0.48:
        return "BUY"
    if score >= 0.22:
        return "SCALP BUY"
    if score <= -0.78:
        return "STRONG SELL"
    if score <= -0.48:
        return "SELL"
    if score <= -0.22:
        return "SCALP SELL"
    return "WAIT"


def expiry_seconds_for(action_name):
    if "SCALP" in action_name:
        return 30 * 60
    if action_name in ["BUY", "SELL"]:
        return 2 * 60 * 60
    if "STRONG" in action_name:
        return 4 * 60 * 60
    return 15 * 60


def build_plan(symbol, action_name, ind, candles):
    atr = max(ind["atr"], SUPPORTED_ASSETS[symbol]["pip"] * 20)
    ob = order_block_zone(candles, action_name)
    price = ind["price"]
    if "BUY" in action_name:
        entry_low = min(ob["low"], price)
        entry_high = max(ob["high"], price)
        sl = entry_low - atr * 0.85
        tp1 = price + atr * 1.2
        tp2 = price + atr * 2.1
        invalid = sl
        do_not = entry_high + atr * 0.55
    elif "SELL" in action_name:
        entry_low = min(ob["low"], price)
        entry_high = max(ob["high"], price)
        sl = entry_high + atr * 0.85
        tp1 = price - atr * 1.2
        tp2 = price - atr * 2.1
        invalid = sl
        do_not = entry_low - atr * 0.55
    else:
        entry_low = ind["support_soft"]
        entry_high = ind["resistance_soft"]
        sl = price - atr
        tp1 = price + atr
        tp2 = price + atr * 1.8
        invalid = sl
        do_not = None
    return {
        "entry": {"low": rp(symbol, entry_low), "high": rp(symbol, entry_high)},
        "stop_loss": rp(symbol, sl),
        "take_profit_1": rp(symbol, tp1),
        "take_profit_2": rp(symbol, tp2),
        "invalidation": rp(symbol, invalid),
        "do_not_trade_level": rp(symbol, do_not) if do_not is not None else None,
    }


def signal(asset):
    symbol = normalize_asset(asset)
    try:
        live = get_candles(symbol)
    except LiveDataError as exc:
        return {
            "asset": symbol,
            "display_name": SUPPORTED_ASSETS[symbol]["display"],
            "status": "error",
            "error": str(exc),
            "message": "LIVE DATA ERROR — no fake/demo price shown.",
        }
    candles = live["candles"]
    ind = build(candles)
    sb = analyze_sb(candles, ind)
    ses = session_info()
    nw = news(symbol)
    score = 0.0
    reasons = []
    score += sb["score"]
    reasons += sb["reasons"]
    if ind["trend"] == "bullish":
        score += 0.14
        reasons.append("EMA trend bullish.")
    elif ind["trend"] == "bearish":
        score -= 0.14
        reasons.append("EMA trend bearish.")
    else:
        reasons.append("EMA trend mixed.")
    if ind["rsi"] <= 32:
        score += 0.15
        reasons.append("RSI oversold: buy bounce probability higher.")
    elif ind["rsi"] >= 68:
        score -= 0.15
        reasons.append("RSI overbought: sell pullback probability higher.")
    else:
        reasons.append("RSI neutral.")
    score += nw["score"]
    reasons.append(f"News bias: {nw['bias']} — {nw['explanation']}")
    score += ses["score"]
    reasons.append(f"Session: {ses['name']}.")
    action_name = choose_action(score)
    plan = build_plan(symbol, action_name, ind, candles)
    expiry = expiry_seconds_for(action_name)
    if "BUY" in action_name:
        warning = "Avoid SELL while buy/scalp-buy plan is active unless price breaks invalidation."
        trade_type = "scalp" if "SCALP" in action_name else "intraday"
    elif "SELL" in action_name:
        warning = "Avoid BUY while sell/scalp-sell plan is active unless price breaks invalidation."
        trade_type = "scalp" if "SCALP" in action_name else "intraday"
    else:
        warning = "No clean entry. Wait for liquidity sweep, FVG reaction, or BOS/CHOCH confirmation."
        trade_type = "no_trade"
    confidence = min(95, max(50, 50 + abs(score) * 58))
    return {
        "asset": symbol,
        "display_name": SUPPORTED_ASSETS[symbol]["display"],
        "status": "live",
        "price": rp(symbol, ind["price"]),
        "action": action_name,
        "trade_type": trade_type,
        "confidence": round(confidence, 1),
        "score": round(score, 3),
        "risk_level": "High" if abs(score) < 0.25 else "Medium" if abs(score) < 0.55 else "Controlled",
        "source": live["source"],
        "source_time": live["source_time"],
        "cache_age": live["cache_age"],
        "indicators": {
            "trend": ind["trend"], "rsi": ind["rsi"], "atr": rp(symbol, ind["atr"]),
            "ema9": rp(symbol, ind["ema9"]), "ema20": rp(symbol, ind["ema20"]), "ema50": rp(symbol, ind["ema50"]),
            "range_high": rp(symbol, ind["range_high"]), "range_low": rp(symbol, ind["range_low"]),
            "support_soft": rp(symbol, ind["support_soft"]), "resistance_soft": rp(symbol, ind["resistance_soft"]),
        },
        "sb_model": sb,
        "plan": plan,
        "signal_timer_seconds": expiry,
        "signal_expiry_label": "30 min scalp" if trade_type == "scalp" else "2-4 hr intraday" if trade_type == "intraday" else "15 min wait-check",
        "news": nw,
        "session": ses,
        "warning": warning,
        "reasons": reasons[:10],
    }
