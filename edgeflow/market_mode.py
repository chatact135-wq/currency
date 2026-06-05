from __future__ import annotations
import pandas as pd
from .indicators import add_indicators
from .utils import signed_moves, moves

def detect_market_mode(df: pd.DataFrame) -> dict:
    if len(df) < 80:
        return {
            "mode": "NO DATA",
            "bias": "NEUTRAL",
            "score": 0,
            "reason": "Need at least 80 candles.",
        }

    x = add_indicators(df).dropna().reset_index(drop=True)
    if x.empty:
        return {"mode": "NO DATA", "bias": "NEUTRAL", "score": 0, "reason": "Indicators unavailable."}

    last = x.iloc[-1]
    close = float(last["close"])
    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])
    atr = float(last["atr14_moves"]) if pd.notna(last["atr14_moves"]) else 0

    day_open = float(x.iloc[0]["open"])
    day_high = float(x["high"].max())
    day_low = float(x["low"].min())
    day_range = moves(day_low, day_high)
    day_move = signed_moves(day_open, close)

    recent_15 = signed_moves(float(x.iloc[-15]["open"]), close) if len(x) >= 15 else 0
    recent_30 = signed_moves(float(x.iloc[-30]["open"]), close) if len(x) >= 30 else 0

    # Structure: higher lows / lower highs over recent candles
    recent = x.tail(20)
    lower_highs = int((recent["high"].diff() < 0).sum())
    higher_lows = int((recent["low"].diff() > 0).sum())

    score_buy = 0
    score_sell = 0

    if close > ema20 > ema50:
        score_buy += 2
    if close < ema20 < ema50:
        score_sell += 2

    if day_move > 80:
        score_buy += 2
    if day_move < -80:
        score_sell += 2

    if recent_15 > 35 or recent_30 > 60:
        score_buy += 1
    if recent_15 < -35 or recent_30 < -60:
        score_sell += 1

    if higher_lows >= 10:
        score_buy += 1
    if lower_highs >= 10:
        score_sell += 1

    if atr >= 22 or day_range >= 180:
        vol = "HIGH"
    elif atr <= 7 or day_range <= 45:
        vol = "LOW"
    else:
        vol = "NORMAL"

    if score_buy >= 4 and day_range >= 80:
        mode = "TREND BUY"
        bias = "BUY"
        score = score_buy
        reason = f"Price above EMA20/EMA50, day move {day_move:.1f} moves, range {day_range:.1f}."
    elif score_sell >= 4 and day_range >= 80:
        mode = "TREND SELL"
        bias = "SELL"
        score = score_sell
        reason = f"Price below EMA20/EMA50, day move {day_move:.1f} moves, range {day_range:.1f}."
    elif day_range <= 55 and atr <= 9:
        mode = "CHOPPY"
        bias = "NEUTRAL"
        score = 0
        reason = f"Small range {day_range:.1f} and low ATR {atr:.1f}. Avoid scalping noise."
    elif atr >= 35:
        mode = "DANGER"
        bias = "NEUTRAL"
        score = max(score_buy, score_sell)
        reason = f"Very high volatility ATR {atr:.1f}. Possible news/spike danger."
    else:
        mode = "NORMAL"
        bias = "BUY" if score_buy > score_sell else "SELL" if score_sell > score_buy else "NEUTRAL"
        score = max(score_buy, score_sell)
        reason = f"Normal conditions. Day range {day_range:.1f}, ATR {atr:.1f}."

    return {
        "mode": mode,
        "bias": bias,
        "score": score,
        "volatility": vol,
        "day_range_moves": round(day_range, 1),
        "day_move_moves": round(day_move, 1),
        "recent_15_moves": round(recent_15, 1),
        "recent_30_moves": round(recent_30, 1),
        "atr14_moves": round(atr, 1),
        "price": round(close, 5),
        "ema20": round(ema20, 5),
        "ema50": round(ema50, 5),
        "reason": reason,
    }
