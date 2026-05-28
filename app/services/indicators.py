import pandas as pd
import numpy as np

def s(candles, key):
    return pd.Series([float(c[key]) for c in candles], dtype="float64")

def ema(candles, span):
    return float(s(candles, "close").ewm(span=span, adjust=False).mean().iloc[-1])

def rsi(candles, period=14):
    close = s(candles, "close")
    d = close.diff()
    gain = d.clip(lower=0).rolling(period).mean()
    loss = (-d.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 0.000001)
    val = 100 - (100 / (1 + rs))
    last = val.iloc[-1]
    return float(50 if pd.isna(last) else round(last, 2))

def atr(candles, period=14):
    h, l, c = s(candles, "high"), s(candles, "low"), s(candles, "close")
    pc = c.shift(1)
    tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    val = tr.rolling(period).mean().iloc[-1]
    if pd.isna(val):
        val = tr.mean()
    return float(val)

def momentum(candles, lookback=6):
    if len(candles) <= lookback:
        return 0.0
    now = candles[-1]["close"]
    old = candles[-lookback]["close"]
    return (now - old) / old

def pressure(candles, n=5):
    recent = candles[-n:]
    bull = sum(max(0, c["close"] - c["open"]) for c in recent)
    bear = sum(max(0, c["open"] - c["close"]) for c in recent)
    total = bull + bear
    return 0.0 if total == 0 else (bull - bear) / total

def volume_profile_proxy(candles, bins=16):
    # Twelve Data forex candles often do not include true volume.
    # This is a frequency profile using candle close distribution.
    closes = np.array([c["close"] for c in candles[-96:]], dtype=float)
    hist, edges = np.histogram(closes, bins=bins)
    poc_i = int(hist.argmax())
    poc = (edges[poc_i] + edges[poc_i+1]) / 2
    total = hist.sum()
    sorted_bins = sorted(range(len(hist)), key=lambda i: hist[i], reverse=True)
    selected = []
    acc = 0
    for i in sorted_bins:
        selected.append(i)
        acc += hist[i]
        if total and acc / total >= 0.70:
            break
    val = min(edges[i] for i in selected)
    vah = max(edges[i+1] for i in selected)
    return {"poc": float(poc), "val": float(val), "vah": float(vah), "note": "frequency profile proxy"}

def structure(candles):
    recent = candles[-96:]
    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]
    closes = [c["close"] for c in recent]
    return {
        "range_high": max(highs),
        "range_low": min(lows),
        "resistance_soft": float(np.quantile(highs, 0.82)),
        "support_soft": float(np.quantile(lows, 0.18)),
        "midpoint": float(np.median(closes)),
        "prev_high": max(c["high"] for c in recent[:-3]),
        "prev_low": min(c["low"] for c in recent[:-3]),
        "profile": volume_profile_proxy(candles),
    }

def build(candles):
    price = candles[-1]["close"]
    e9, e20, e50 = ema(candles, 9), ema(candles, 20), ema(candles, 50)
    trend = "bullish" if e9 > e20 > e50 else "bearish" if e9 < e20 < e50 else "mixed"
    return {
        "price": price,
        "ema9": e9,
        "ema20": e20,
        "ema50": e50,
        "rsi": rsi(candles),
        "atr": atr(candles),
        "momentum": momentum(candles),
        "pressure": pressure(candles),
        "trend": trend,
        **structure(candles),
    }
