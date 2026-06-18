import requests
import os
from datetime import datetime
import pandas as pd

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

def fetch_finnhub_candles(symbol: str, interval: str = "15", outputsize: int = 100):
    if not FINNHUB_API_KEY:
        print("Finnhub API key missing")
        return None

    resolution = {"1min": "1", "5min": "5", "15min": "15", "1h": "60", "4h": "240"}.get(interval, "15")

    to_time = int(datetime.now().timestamp())
    from_time = to_time - (outputsize * 15 * 60)

    url = "https://finnhub.io/api/v1/forex/candle"
    params = {
        "symbol": f"OANDA:{symbol.replace('/', '_')}",
        "resolution": resolution,
        "from": from_time,
        "to": to_time,
        "token": FINNHUB_API_KEY
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("s") != "ok":
            return None

        df = pd.DataFrame({
            "datetime": pd.to_datetime(data["t"], unit="s"),
            "open": data["o"],
            "high": data["h"],
            "low": data["l"],
            "close": data["c"],
        })
        df.set_index("datetime", inplace=True)
        return df
    except:
        return None

def fetch_twelvedata_candles(symbol: str, interval: str = "15min", outputsize: int = 100):
    return fetch_finnhub_candles(symbol, interval, outputsize)

def fallback_demo_data(symbol: str, interval: str = "15min"):
    print(f"Using fallback demo data for {symbol}")
    import pandas as pd
    from datetime import datetime, timedelta
    now = datetime.now()
    dates = [now - timedelta(minutes=i*15) for i in range(100)]
    prices = [1.15 + (i * 0.0001) for i in range(100)]
    df = pd.DataFrame({
        "datetime": dates,
        "open": prices,
        "high": [p + 0.0005 for p in prices],
        "low": [p - 0.0005 for p in prices],
        "close": prices,
    })
    df.set_index("datetime", inplace=True)
    return df
