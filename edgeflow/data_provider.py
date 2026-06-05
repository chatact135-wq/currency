from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any
import httpx
import pandas as pd

from .config import TWELVEDATA_API_KEY

TWELVEDATA_BASE = "https://api.twelvedata.com"


class DataError(Exception):
    pass


async def fetch_twelvedata_candles(symbol: str, interval: str = "1min", outputsize: int = 200) -> pd.DataFrame:
    if not TWELVEDATA_API_KEY:
        raise DataError("TWELVEDATA_API_KEY is missing. Add it in Railway environment variables.")

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": TWELVEDATA_API_KEY,
        "format": "JSON",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{TWELVEDATA_BASE}/time_series", params=params)
        data = r.json()

    if "status" in data and data.get("status") == "error":
        raise DataError(data.get("message", "TwelveData error"))

    values = data.get("values")
    if not values:
        raise DataError(f"No candle values returned for {symbol}")

    df = pd.DataFrame(values)
    df["time"] = pd.to_datetime(df["datetime"], errors="coerce")
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").reset_index(drop=True)
    return df[["time", "open", "high", "low", "close"]]


async def fetch_live_quote(symbol: str) -> Dict[str, Any]:
    if not TWELVEDATA_API_KEY:
        raise DataError("TWELVEDATA_API_KEY is missing. Add it in Railway environment variables.")

    params = {"symbol": symbol, "apikey": TWELVEDATA_API_KEY}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{TWELVEDATA_BASE}/quote", params=params)
        data = r.json()

    if "status" in data and data.get("status") == "error":
        raise DataError(data.get("message", "TwelveData quote error"))

    return data


def fallback_demo_data(symbol: str) -> pd.DataFrame:
    """Safe demo data if API key is missing. This is not for trading."""
    import numpy as np
    now = pd.Timestamp.utcnow().floor("min")
    times = pd.date_range(end=now, periods=200, freq="min")
    base = 1.1600 if symbol == "EUR/USD" else 1.3400
    steps = np.random.default_rng(42 if symbol == "EUR/USD" else 43).normal(0, 0.00004, len(times)).cumsum()
    close = base + steps
    open_ = pd.Series(close).shift(1).fillna(close[0]).to_numpy()
    high = np.maximum(open_, close) + 0.00003
    low = np.minimum(open_, close) - 0.00003
    return pd.DataFrame({"time": times, "open": open_, "high": high, "low": low, "close": close})
