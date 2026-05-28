import requests
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.config import settings
from app.models import PriceTick
from app.services import cache

ASSETS = {
    "EURUSD": {"display":"EUR/USD", "finnhub_symbol":"OANDA:EUR_USD", "pip":0.0001},
    "GBPUSD": {"display":"GBP/USD", "finnhub_symbol":"OANDA:GBP_USD", "pip":0.0001},
    "XAUUSD": {"display":"Gold / XAUUSD", "finnhub_symbol":"OANDA:XAU_USD", "pip":0.10},
    "WTI": {"display":"WTI Oil", "finnhub_symbol":"OANDA:WTICO_USD", "pip":0.01},
}

class LiveDataError(Exception): pass
class CollectingTicks(Exception): pass

def normalize(asset):
    a = asset.upper().replace("/", "").replace("-", "").replace(" ", "")
    if a in ["GOLD", "XAU"]: return "XAUUSD"
    if a in ["OIL", "USOIL", "WTIUSD"]: return "WTI"
    return a if a in ASSETS else "EURUSD"

def active_assets():
    return [a for a in settings.ACTIVE_ASSETS if a in ASSETS]

def finnhub_quote(asset):
    symbol = normalize(asset)
    key = f"fh_quote:{symbol}"
    cached = cache.get(key, settings.TICK_CACHE_SECONDS)
    if cached:
        return {**cached, "source":"finnhub-quote-cached", "cache_age":cache.age(key)}
    if not settings.FINNHUB_API_KEY:
        raise LiveDataError("FINNHUB_API_KEY missing.")
    fsym = ASSETS[symbol]["finnhub_symbol"]
    try:
        r = requests.get("https://finnhub.io/api/v1/quote", params={"symbol":fsym, "token":settings.FINNHUB_API_KEY}, timeout=12)
        data = r.json()
    except Exception as exc:
        raise LiveDataError(f"Finnhub quote connection failed: {exc}")
    if isinstance(data, dict) and data.get("error"):
        raise LiveDataError(str(data.get("error")))
    price = data.get("c") or data.get("pc")
    if not price:
        raise LiveDataError(f"Finnhub quote returned no price for {symbol}: {data}")
    result = {"asset":symbol, "display":ASSETS[symbol]["display"], "price":float(price), "provider_symbol":fsym, "source":"finnhub-quote-live", "cache_age":0}
    cache.set(key, result)
    return result

def store_tick(db: Session, asset: str):
    q = finnhub_quote(asset)
    row = PriceTick(asset=q["asset"], price=q["price"], provider="finnhub", provider_symbol=q["provider_symbol"])
    db.add(row)
    db.commit()
    return q

def collect_all_ticks(db: Session):
    out = []
    for a in active_assets():
        try:
            out.append(store_tick(db, a))
        except Exception as exc:
            out.append({"asset":a, "error":str(exc)})
    return out

def get_recent_ticks(db: Session, asset: str, minutes: int = 240):
    symbol = normalize(asset)
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    rows = (db.query(PriceTick)
              .filter(PriceTick.asset == symbol)
              .filter(PriceTick.created_at >= since)
              .order_by(PriceTick.created_at.asc())
              .all())
    return rows

def build_candles_from_ticks(db: Session, asset: str, interval_seconds: int = 300, needed: int = 60):
    symbol = normalize(asset)
    rows = get_recent_ticks(db, symbol, minutes=480)
    if len(rows) < 20:
        raise CollectingTicks(f"Collecting live ticks for {symbol}. Need more stored prices before strategy can run. Current ticks: {len(rows)}")
    buckets = {}
    for r in rows:
        ts = int(r.created_at.replace(tzinfo=timezone.utc).timestamp())
        bucket = ts - (ts % interval_seconds)
        buckets.setdefault(bucket, []).append(float(r.price))
    candles = []
    for bucket in sorted(buckets.keys()):
        prices = buckets[bucket]
        candles.append({
            "datetime": bucket,
            "open": prices[0],
            "high": max(prices),
            "low": min(prices),
            "close": prices[-1],
        })
    # If fewer 5-min candles, build compact time-buckets from stored live ticks using rolling chunks.
    # This uses only stored live prices.
    if len(candles) < 30 and len(rows) >= 20:
        prices = [float(r.price) for r in rows]
        chunk = max(2, len(prices)//40)
        candles = []
        for i in range(0, len(prices), chunk):
            part = prices[i:i+chunk]
            if len(part) < 2: continue
            candles.append({"datetime": i, "open":part[0], "high":max(part), "low":min(part), "close":part[-1]})
    if len(candles) < 20:
        raise CollectingTicks(f"Still collecting enough candle structure for {symbol}. Current candles: {len(candles)}")
    return candles[-needed:]

def market_snapshot(db: Session, asset: str):
    symbol = normalize(asset)
    q = store_tick(db, symbol)
    candles = build_candles_from_ticks(db, symbol)
    if candles:
        candles[-1]["close"] = q["price"]
        candles[-1]["high"] = max(candles[-1]["high"], q["price"])
        candles[-1]["low"] = min(candles[-1]["low"], q["price"])
    return {
        "asset": symbol,
        "display": ASSETS[symbol]["display"],
        "price": q["price"],
        "candles": candles,
        "source": q["source"] + "+neon-tick-candles",
        "cache_age": q["cache_age"],
        "source_time": candles[-1]["datetime"],
        "tick_count": len(get_recent_ticks(db, symbol, minutes=480)),
    }
