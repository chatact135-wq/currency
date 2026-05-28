import requests
from app.config import settings
from app.services.cache import get_cache, set_cache, age

SUPPORTED_ASSETS = {
    "EURUSD": {"display": "EUR/USD", "twelve": "EUR/USD", "pip": 0.0001},
    "GBPUSD": {"display": "GBP/USD", "twelve": "GBP/USD", "pip": 0.0001},
    "XAUUSD": {"display": "Gold / XAUUSD", "twelve": "XAU/USD", "pip": 0.10},
    "WTI": {"display": "WTI Oil", "twelve": "WTI/USD", "pip": 0.01},
}

class LiveDataError(Exception):
    pass

def normalize_asset(asset: str) -> str:
    cleaned = asset.upper().replace("/", "").replace("-", "").replace(" ", "")
    if cleaned in ["GOLD", "XAU"]:
        return "XAUUSD"
    if cleaned in ["OIL", "USOIL", "WTIUSD"]:
        return "WTI"
    return cleaned if cleaned in SUPPORTED_ASSETS else "EURUSD"

def active_assets():
    return [a for a in settings.ACTIVE_ASSETS if a in SUPPORTED_ASSETS]

def parse_values(data: dict):
    values = data.get("values") or []
    if len(values) < 40:
        msg = data.get("message") or data.get("status") or "Not enough live candles returned"
        raise LiveDataError(str(msg))
    candles = []
    for row in reversed(values):
        candles.append({
            "datetime": row.get("datetime", ""),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        })
    return candles

def get_candles(asset: str, interval: str = "5min", points: int = 120):
    symbol = normalize_asset(asset)
    key = f"td:{symbol}:{interval}:{points}"
    cached = get_cache(key, settings.MARKET_CACHE_SECONDS)
    if cached:
        return {**cached, "source": "twelve-data-live-cached", "cache_age": age(key)}
    if not settings.TWELVEDATA_API_KEY:
        raise LiveDataError("TWELVEDATA_API_KEY missing. Add it in Railway Variables.")
    info = SUPPORTED_ASSETS[symbol]
    try:
        r = requests.get("https://api.twelvedata.com/time_series", params={
            "symbol": info["twelve"], "interval": interval, "outputsize": points,
            "apikey": settings.TWELVEDATA_API_KEY, "format": "JSON"
        }, timeout=15)
        data = r.json()
    except Exception as exc:
        raise LiveDataError(f"Twelve Data connection failed: {exc}")
    if data.get("status") == "error":
        raise LiveDataError(data.get("message", "Twelve Data API error"))
    candles = parse_values(data)
    result = {
        "asset": symbol, "display_name": info["display"], "candles": candles,
        "source": "twelve-data-live", "cache_age": 0, "source_time": candles[-1].get("datetime", "")
    }
    set_cache(key, result)
    return result
