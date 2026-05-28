import pandas as pd
import numpy as np

def series(candles, key):
    return pd.Series([float(c[key]) for c in candles], dtype="float64")

def ema(candles, span):
    return float(round(series(candles, "close").ewm(span=span, adjust=False).mean().iloc[-1], 5))

def rsi(candles, period=14):
    closes = series(candles, "close")
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 0.000001)
    value = 100 - (100 / (1 + rs))
    last = value.iloc[-1]
    return float(50 if pd.isna(last) else round(last, 2))

def atr(candles, period=14):
    highs, lows, closes = series(candles, "high"), series(candles, "low"), series(candles, "close")
    prev_close = closes.shift(1)
    tr = pd.concat([highs - lows, (highs - prev_close).abs(), (lows - prev_close).abs()], axis=1).max(axis=1)
    val = tr.rolling(period).mean().iloc[-1]
    if pd.isna(val):
        val = tr.mean()
    return float(round(val, 5))

def sr(candles, lookback=96):
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]
    closes = [c["close"] for c in recent]
    base = recent[:-3] if len(recent) > 6 else recent
    return {
        "range_high": round(max(highs), 5),
        "range_low": round(min(lows), 5),
        "resistance_soft": round(float(np.quantile(highs, 0.82)), 5),
        "support_soft": round(float(np.quantile(lows, 0.18)), 5),
        "midpoint": round(float(np.median(closes)), 5),
        "prev_high": round(max([c["high"] for c in base]), 5),
        "prev_low": round(min([c["low"] for c in base]), 5),
    }

def build(candles):
    close = float(candles[-1]["close"])
    ema9, ema20, ema50 = ema(candles, 9), ema(candles, 20), ema(candles, 50)
    if ema9 > ema20 > ema50:
        trend = "bullish"
    elif ema9 < ema20 < ema50:
        trend = "bearish"
    else:
        trend = "mixed"
    return {
        "price": round(close, 5), "ema9": ema9, "ema20": ema20, "ema50": ema50,
        "rsi": rsi(candles), "atr": atr(candles), "trend": trend, **sr(candles)
    }
