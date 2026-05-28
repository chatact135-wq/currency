import requests
from app.config import settings
from app.services import cache

ASSETS = {
    "EURUSD": {"display":"EUR/USD", "symbol":"EUR/USD", "pip":0.0001},
    "GBPUSD": {"display":"GBP/USD", "symbol":"GBP/USD", "pip":0.0001},
    "XAUUSD": {"display":"Gold / XAUUSD", "symbol":"XAU/USD", "pip":0.10},
    "WTI": {"display":"WTI Oil", "symbol":"WTI/USD", "pip":0.01},
}

class LiveDataError(Exception): pass

def normalize(asset):
    a = asset.upper().replace("/", "").replace("-", "").replace(" ", "")
    if a in ["GOLD","XAU"]: return "XAUUSD"
    if a in ["OIL","USOIL","WTIUSD"]: return "WTI"
    return a if a in ASSETS else "EURUSD"

def active_assets():
    return [a for a in settings.ACTIVE_ASSETS if a in ASSETS]

def candles(asset, interval="5min", outputsize=120):
    symbol = normalize(asset)
    key = f"td:{symbol}:{interval}:{outputsize}"
    cached = cache.get(key, settings.MARKET_CACHE_SECONDS)
    if cached:
        return {**cached, "source":"twelve-data-live-cached", "cache_age":cache.age(key)}
    if not settings.TWELVEDATA_API_KEY:
        raise LiveDataError("TWELVEDATA_API_KEY missing. No live price shown.")
    params = {
        "symbol": ASSETS[symbol]["symbol"],
        "interval": interval,
        "outputsize": outputsize,
        "apikey": settings.TWELVEDATA_API_KEY,
        "format":"JSON",
    }
    try:
        r = requests.get("https://api.twelvedata.com/time_series", params=params, timeout=15)
        data = r.json()
    except Exception as e:
        raise LiveDataError(f"Twelve Data connection failed: {e}")
    if data.get("status") == "error":
        raise LiveDataError(data.get("message", "Twelve Data API error"))
    vals = data.get("values") or []
    if len(vals) < 50:
        raise LiveDataError("Not enough live candles received.")
    cs = []
    for row in reversed(vals):
        cs.append({
            "datetime": row.get("datetime",""),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        })
    result = {"asset":symbol, "display":ASSETS[symbol]["display"], "candles":cs, "source":"twelve-data-live", "cache_age":0, "source_time":cs[-1]["datetime"]}
    cache.set(key, result)
    return result
