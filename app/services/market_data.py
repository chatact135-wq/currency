import math, random, requests
from datetime import datetime, timezone
from app.config import settings

SUPPORTED_ASSETS = {
    "EURUSD": {"display": "EUR/USD", "twelve": "EUR/USD", "base": 1.0850, "pip": 0.0001},
    "GBPUSD": {"display": "GBP/USD", "twelve": "GBP/USD", "base": 1.2700, "pip": 0.0001},
    "XAUUSD": {"display": "Gold / XAUUSD", "twelve": "XAU/USD", "base": 2350.0, "pip": 0.10},
    "WTI": {"display": "WTI Oil", "twelve": "WTI/USD", "base": 78.0, "pip": 0.01},
}

def normalize_asset(asset: str) -> str:
    asset = asset.upper().replace("/", "").replace("-", "").replace(" ", "")
    if asset in ["GOLD", "XAU"]:
        return "XAUUSD"
    if asset in ["OIL", "USOIL", "WTIUSD"]:
        return "WTI"
    return asset if asset in SUPPORTED_ASSETS else "EURUSD"

def get_supported_assets():
    return SUPPORTED_ASSETS

def _synthetic_candles(symbol: str, points: int = 160):
    info = SUPPORTED_ASSETS.get(symbol, SUPPORTED_ASSETS["EURUSD"])
    base = info["base"]
    now = datetime.now(timezone.utc).timestamp()
    candles, previous = [], base
    for i in range(points):
        wave_fast = math.sin((i + now / 900) / 8) * base * 0.0022
        wave_slow = math.sin((i + now / 3600) / 22) * base * 0.004
        noise = random.uniform(-base * 0.0007, base * 0.0007)
        close = max(0.0001, base + wave_fast + wave_slow + noise)
        high = max(previous, close) * (1 + random.uniform(0.0004, 0.0018))
        low = min(previous, close) * (1 - random.uniform(0.0004, 0.0018))
        candles.append({"open": round(previous, 5), "high": round(high, 5), "low": round(low, 5), "close": round(close, 5)})
        previous = close
    return candles, "demo-fallback"

def _twelve_data_candles(symbol: str, interval: str = "5min", points: int = 160):
    key = settings.TWELVEDATA_API_KEY
    if not key:
        return None
    info = SUPPORTED_ASSETS.get(symbol)
    if not info:
        return None
    try:
        r = requests.get("https://api.twelvedata.com/time_series", params={"symbol": info["twelve"], "interval": interval, "outputsize": points, "apikey": key, "format": "JSON"}, timeout=12)
        data = r.json()
        values = data.get("values", [])
        if len(values) < 50:
            return None
        candles = []
        for row in reversed(values):
            candles.append({"open": float(row["open"]), "high": float(row["high"]), "low": float(row["low"]), "close": float(row["close"])})
        return candles, "twelve-data-live"
    except Exception:
        return None

def get_market_candles(asset: str, points: int = 160):
    symbol = normalize_asset(asset)
    real = _twelve_data_candles(symbol, points=points)
    if real:
        return real
    return _synthetic_candles(symbol, points=points)
