from __future__ import annotations
import pandas as pd
import numpy as np
from .utils import moves, signed_moves

def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()

def atr_moves(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        (df["high"] - df["low"]).abs(),
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(n).mean() / 0.00001

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema20"] = ema(out["close"], 20)
    out["ema50"] = ema(out["close"], 50)
    out["atr14_moves"] = atr_moves(out, 14)
    out["body_moves"] = (out["close"] - out["open"]).abs() / 0.00001
    out["direction"] = np.where(out["close"] > out["open"], "BUY", np.where(out["close"] < out["open"], "SELL", "NEUTRAL"))
    out["range_moves"] = (out["high"] - out["low"]).abs() / 0.00001
    out["rolling_high_20"] = out["high"].shift(1).rolling(20).max()
    out["rolling_low_20"] = out["low"].shift(1).rolling(20).min()
    out["rolling_high_60"] = out["high"].shift(1).rolling(60).max()
    out["rolling_low_60"] = out["low"].shift(1).rolling(60).min()
    return out
