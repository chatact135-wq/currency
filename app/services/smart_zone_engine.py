from app.services.market_data import get_market_candles, normalize_asset, SUPPORTED_ASSETS
from app.services.indicators import build_indicators
from app.services.news_sentiment import analyze_news_context

def _round_price(symbol, value):
    pip = SUPPORTED_ASSETS.get(symbol, SUPPORTED_ASSETS["EURUSD"])["pip"]
    if pip >= 0.1:
        return round(value, 2)
    if pip >= 0.01:
        return round(value, 3)
    return round(value, 5)

def _zone_width(symbol, atr_value):
    pip = SUPPORTED_ASSETS.get(symbol, SUPPORTED_ASSETS["EURUSD"])["pip"]
    return max(atr_value * 0.35, pip * 12)

def generate_smart_signal(asset: str):
    symbol = normalize_asset(asset)
    candles, data_source = get_market_candles(symbol)
    ind = build_indicators(candles)
    news = analyze_news_context(symbol)
    price = ind["current_price"]
    pip = SUPPORTED_ASSETS.get(symbol, SUPPORTED_ASSETS["EURUSD"])["pip"]
    atr = max(ind["atr"], pip * 20)
    width = _zone_width(symbol, atr)
    support, support_soft = ind["support"], ind["support_soft"]
    resistance, resistance_soft = ind["resistance"], ind["resistance_soft"]
    buy_low = min(support, support_soft + width)
    buy_high = max(support, support_soft + width)
    sell_low = min(resistance_soft - width, resistance)
    sell_high = max(resistance_soft - width, resistance)
    do_not_buy_above = sell_low
    do_not_sell_below = buy_high
    reasons, warnings, score = [], [], 0.0
    near_support = price <= buy_high
    near_resistance = price >= sell_low
    overbought = ind["rsi"] >= 68
    oversold = ind["rsi"] <= 32
    if near_resistance:
        score -= 0.34
        reasons.append("Price is near the smart resistance / sell zone.")
        warnings.append("Do NOT buy near this high area unless a confirmed breakout happens.")
    if near_support:
        score += 0.34
        reasons.append("Price is near the smart support / buy zone.")
        warnings.append("Do NOT sell near this low area because bounce risk is higher.")
    if overbought:
        score -= 0.22
        reasons.append("RSI is overbought; pullback probability is higher.")
    elif oversold:
        score += 0.22
        reasons.append("RSI is oversold; bounce probability is higher.")
    else:
        reasons.append("RSI is not extreme; wait for price-zone confirmation.")
    if ind["trend"] == "bullish":
        score += 0.16
        reasons.append("EMA trend is bullish.")
    elif ind["trend"] == "bearish":
        score -= 0.16
        reasons.append("EMA trend is bearish.")
    else:
        reasons.append("EMA trend is mixed.")
    if news["score"] > 0.15:
        score += 0.12
        reasons.append("News sentiment is supportive.")
    elif news["score"] < -0.15:
        score -= 0.12
        reasons.append("News sentiment is negative.")
    else:
        reasons.append("No strong live news bias detected.")
    if score <= -0.35:
        action = "SELL ZONE / AVOID BUY"
        entry_low, entry_high = sell_low, sell_high
        stop_loss = sell_high + atr * 0.75
        take_profit_1 = ind["midpoint"]
        take_profit_2 = buy_high
        warning = "Do NOT buy now. Price is high or near resistance; sell setup is stronger."
        expected = "Possible drop in 30–90 minutes if resistance rejection continues."
    elif score >= 0.35:
        action = "BUY ZONE / AVOID SELL"
        entry_low, entry_high = buy_low, buy_high
        stop_loss = buy_low - atr * 0.75
        take_profit_1 = ind["midpoint"]
        take_profit_2 = sell_low
        warning = "Do NOT sell now. Price is low or near support; buy setup is stronger."
        expected = "Possible bounce in 30–90 minutes if support holds."
    else:
        action = "WAIT / NO CLEAN ENTRY"
        entry_low, entry_high = buy_high, sell_low
        stop_loss = price - atr
        take_profit_1 = price + atr
        take_profit_2 = price + atr * 1.8
        warning = "Do not force a trade. Price is between smart zones; wait for buy zone or sell zone."
        expected = "Wait for clearer movement; confirmation may need 30–120 minutes."
    volatility = ind["volatility_pct"]
    if volatility > 0.35:
        risk_level = "High"
        score *= 0.80
        reasons.append("Volatility is elevated, so confidence is reduced.")
    elif volatility > 0.18:
        risk_level = "Medium"
    else:
        risk_level = "Low"
    confidence = min(93, max(55, 55 + abs(score) * 100))
    if warnings and "Do NOT" not in warning:
        warning += " " + " ".join(warnings)
    return {"asset": symbol, "display_name": SUPPORTED_ASSETS.get(symbol, {}).get("display", symbol), "current_price": _round_price(symbol, price), "action": action, "confidence": round(confidence, 1), "risk_level": risk_level, "trend": ind["trend"], "rsi": ind["rsi"], "ema20": _round_price(symbol, ind["ema20"]), "ema50": _round_price(symbol, ind["ema50"]), "atr": _round_price(symbol, atr), "day_high": _round_price(symbol, ind["day_high"]), "day_low": _round_price(symbol, ind["day_low"]), "support": _round_price(symbol, support), "resistance": _round_price(symbol, resistance), "buy_zone": {"low": _round_price(symbol, buy_low), "high": _round_price(symbol, buy_high)}, "sell_zone": {"low": _round_price(symbol, sell_low), "high": _round_price(symbol, sell_high)}, "do_not_buy_above": _round_price(symbol, do_not_buy_above), "do_not_sell_below": _round_price(symbol, do_not_sell_below), "entry_zone": {"low": _round_price(symbol, entry_low), "high": _round_price(symbol, entry_high)}, "stop_loss": _round_price(symbol, stop_loss), "take_profit_1": _round_price(symbol, take_profit_1), "take_profit_2": _round_price(symbol, take_profit_2), "expected_move_time": expected, "warning": warning, "reasons": reasons[:8], "news": news, "data_source": data_source}
