import math, random
from datetime import datetime, timezone
SUPPORTED_ASSETS = {
    'EURUSD': {'name':'EUR/USD','base':1.0850},
    'GBPUSD': {'name':'GBP/USD','base':1.2700},
    'XAUUSD': {'name':'Gold / XAUUSD','base':2350.0},
    'WTI': {'name':'WTI Oil','base':78.0},
}
def normalize_asset(asset: str) -> str:
    return asset.upper().replace('/','').replace('-','').replace(' ','')
def get_supported_assets():
    return SUPPORTED_ASSETS
def get_market_candles(asset: str, points: int = 120):
    symbol = normalize_asset(asset)
    info = SUPPORTED_ASSETS.get(symbol, SUPPORTED_ASSETS['EURUSD'])
    base = info['base']
    now = datetime.now(timezone.utc).timestamp()
    candles=[]; price=base
    for i in range(points):
        wave = math.sin((i + now/3600)/7) * base * 0.002
        noise = random.uniform(-base*0.0008, base*0.0008)
        close = max(0.0001, base + wave + noise)
        open_price = price
        high = max(open_price, close) * (1 + random.uniform(0.0001,0.001))
        low = min(open_price, close) * (1 - random.uniform(0.0001,0.001))
        candles.append({'open':round(open_price,5),'high':round(high,5),'low':round(low,5),'close':round(close,5)})
        price = close
    return candles
def get_latest_price(asset: str):
    return get_market_candles(asset, 2)[-1]['close']
