import pandas as pd
import numpy as np

def _series(candles, key):
    return pd.Series([float(c[key]) for c in candles], dtype="float64")

def rsi(candles, period=14):
    closes = _series(candles, "close")
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 0.000001)
    value = 100 - (100 / (1 + rs))
    last = value.iloc[-1]
    return float(50 if pd.isna(last) else round(last, 2))

def ema(candles, span=20):
    closes = _series(candles, "close")
    return float(round(closes.ewm(span=span, adjust=False).mean().iloc[-1], 5))

def atr(candles, period=14):
    highs, lows, closes = _series(candles, "high"), _series(candles, "low"), _series(candles, "close")
    prev_close = closes.shift(1)
    tr = pd.concat([highs-lows, (highs-prev_close).abs(), (lows-prev_close).abs()], axis=1).max(axis=1)
    value = tr.rolling(period).mean().iloc[-1]
    if pd.isna(value):
        value = tr.mean()
    return float(round(value, 5))

def volatility_pct(candles):
    closes = _series(candles, "close")
    returns = closes.pct_change().dropna()
    return 0.0 if len(returns) == 0 else float(round(returns.std()*100, 4))

def support_resistance(candles, lookback=96):
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    highs = [float(c["high"]) for c in recent]
    lows = [float(c["low"]) for c in recent]
    closes = [float(c["close"]) for c in recent]
    resistance, support = max(highs), min(lows)
    return {
        "support": round(support, 5),
        "support_soft": round(float(np.quantile(lows, 0.18)), 5),
        "resistance": round(resistance, 5),
        "resistance_soft": round(float(np.quantile(highs, 0.82)), 5),
        "midpoint": round(float(np.median(closes)), 5),
        "day_high": round(resistance, 5),
        "day_low": round(support, 5),
    }

def build_indicators(candles):
    current = float(candles[-1]["close"])
    ema20, ema50, ema100 = ema(candles, 20), ema(candles, 50), ema(candles, 100)
    trend = "bullish" if ema20 > ema50 and current > ema20 else "bearish" if ema20 < ema50 and current < ema20 else "mixed"
    return {"current_price": round(current, 5), "rsi": rsi(candles), "ema20": ema20, "ema50": ema50, "ema200": ema100, "atr": atr(candles), "volatility_pct": volatility_pct(candles), "trend": trend, **support_resistance(candles)}
