import requests
from sqlalchemy.orm import Session
from app.config import settings
from app.models import MarketCandle
from app.services import cache

ASSETS = {
    "EURUSD": {"display": "EUR/USD", "twelve": "EUR/USD", "pip": 0.0001},
    "GBPUSD": {"display": "GBP/USD", "twelve": "GBP/USD", "pip": 0.0001},
    "XAUUSD": {"display": "Gold / XAUUSD", "twelve": "XAU/USD", "pip": 0.10},
    "WTI": {"display": "WTI Oil", "twelve": "WTI/USD", "pip": 0.01},
}

class LiveDataError(Exception):
    pass

def normalize(asset):
    a = asset.upper().replace("/", "").replace("-", "").replace(" ", "")
    if a in ["GOLD", "XAU"]:
        return "XAUUSD"
    if a in ["OIL", "USOIL", "WTIUSD"]:
        return "WTI"
    return a if a in ASSETS else "EURUSD"

def active_assets():
    return [a for a in settings.ACTIVE_ASSETS if a in ASSETS]

def parse_candles(data):
    values = data.get("values") or []
    if len(values) < 50:
        msg = data.get("message") or data.get("status") or "Not enough candle values."
        raise LiveDataError(str(msg))
    out = []
    for row in reversed(values):
        out.append({
            "datetime": str(row.get("datetime", "")),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        })
    return out

def fetch_twelve_candles(asset, interval="5min", outputsize=120):
    symbol = normalize(asset)
    key = f"td:{symbol}:{interval}:{outputsize}"
    cached = cache.get(key, settings.MARKET_CACHE_SECONDS)
    if cached:
        return {**cached, "source": "twelvedata-cached", "cache_age": cache.age(key)}

    if not settings.TWELVEDATA_API_KEY:
        raise LiveDataError("TWELVEDATA_API_KEY missing. Add it in Railway Variables.")

    try:
        r = requests.get("https://api.twelvedata.com/time_series", params={
            "symbol": ASSETS[symbol]["twelve"],
            "interval": interval,
            "outputsize": outputsize,
            "apikey": settings.TWELVEDATA_API_KEY,
            "format": "JSON"
        }, timeout=15)
        data = r.json()
    except Exception as exc:
        raise LiveDataError(f"Twelve Data connection failed: {exc}")

    if data.get("status") == "error":
        raise LiveDataError(data.get("message", "Twelve Data API error"))

    candles = parse_candles(data)
    result = {
        "asset": symbol,
        "display": ASSETS[symbol]["display"],
        "candles": candles,
        "price": candles[-1]["close"],
        "source": "twelvedata-live",
        "cache_age": 0,
        "source_time": candles[-1]["datetime"],
    }
    cache.set(key, result)
    return result

def store_candles(db: Session, asset: str, candles, timeframe="5min"):
    symbol = normalize(asset)
    inserted = 0
    for c in candles:
        exists = (db.query(MarketCandle)
                    .filter(MarketCandle.asset == symbol)
                    .filter(MarketCandle.timeframe == timeframe)
                    .filter(MarketCandle.candle_time == str(c["datetime"]))
                    .first())
        if exists:
            exists.open = c["open"]
            exists.high = c["high"]
            exists.low = c["low"]
            exists.close = c["close"]
        else:
            db.add(MarketCandle(asset=symbol, timeframe=timeframe, candle_time=str(c["datetime"]), open=c["open"], high=c["high"], low=c["low"], close=c["close"]))
            inserted += 1
    db.commit()
    return inserted

def get_stored_candles(db: Session, asset: str, limit=500, timeframe="5min"):
    symbol = normalize(asset)
    rows = (db.query(MarketCandle)
              .filter(MarketCandle.asset == symbol)
              .filter(MarketCandle.timeframe == timeframe)
              .order_by(MarketCandle.id.desc())
              .limit(limit)
              .all())
    rows = list(reversed(rows))
    return [{"datetime": r.candle_time, "open": r.open, "high": r.high, "low": r.low, "close": r.close} for r in rows]

def snapshot(db: Session, asset: str):
    live = fetch_twelve_candles(asset, outputsize=120)
    store_candles(db, live["asset"], live["candles"])
    stored = get_stored_candles(db, live["asset"], limit=settings.HISTORY_CANDLE_LIMIT)
    candles = stored if len(stored) >= 50 else live["candles"]
    return {
        "asset": live["asset"],
        "display": live["display"],
        "price": candles[-1]["close"],
        "candles": candles,
        "source": live["source"] + "+neon-history",
        "cache_age": live["cache_age"],
        "source_time": candles[-1]["datetime"],
        "stored_candles": len(stored),
    }

def download_history(db: Session, asset: str, outputsize=500):
    live = fetch_twelve_candles(asset, outputsize=outputsize)
    inserted = store_candles(db, live["asset"], live["candles"])
    return {"asset": live["asset"], "downloaded": len(live["candles"]), "inserted_or_new": inserted, "source_time": live["source_time"]}
