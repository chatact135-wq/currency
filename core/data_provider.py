import pandas as pd
import httpx
import os
from typing import Optional
from datetime import datetime, timedelta

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")

async def fetch_twelvedata_candles(symbol: str, interval: str = "15min", outputsize: int = 200) -> pd.DataFrame:
    if not TWELVEDATA_API_KEY:
        raise Exception("TWELVEDATA_API_KEY not set")
    
    symbol_map = {
        "EUR/USD": "EUR/USD",
        "GBP/USD": "GBP/USD"
    }
    
    sym = symbol_map.get(symbol, symbol)
    
    url = (
        f"https://api.twelvedata.com/time_series"
        f"?symbol={sym}&interval={interval}&outputsize={outputsize}"
        f"&apikey={TWELVEDATA_API_KEY}&format=JSON"
    )
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        data = response.json()
        
        if "values" not in data:
            raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
        
        df = pd.DataFrame(data["values"])
        df = df.rename(columns={
            "datetime": "time",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close"
        })
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").reset_index(drop=True)
        
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        
        return df

def fallback_demo_data(symbol: str) -> pd.DataFrame:
    """Demo data when API fails"""
    dates = pd.date_range(end=pd.Timestamp.now(), periods=200, freq="15min")
    base = 1.08 if "EUR" in symbol else 1.27
    prices = base + (pd.Series(range(200)).cumsum() % 30) * 0.0003
    
    return pd.DataFrame({
        "time": dates,
        "open": prices,
        "high": prices + 0.0008,
        "low": prices - 0.0008,
        "close": prices + (pd.Series(range(200)).apply(lambda x: 0.0003 if x % 3 == 0 else -0.0002))
    })
