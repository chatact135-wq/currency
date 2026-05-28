import requests
from app.config import settings
from app.services.cache import get_cache,set_cache,cache_age_seconds
SUPPORTED_ASSETS={
 'EURUSD':{'display':'EUR/USD','twelve':'EUR/USD','pip':0.0001},
 'GBPUSD':{'display':'GBP/USD','twelve':'GBP/USD','pip':0.0001},
 'XAUUSD':{'display':'Gold / XAUUSD','twelve':'XAU/USD','pip':0.10},
 'WTI':{'display':'WTI Oil','twelve':'WTI/USD','pip':0.01},
}
def normalize_asset(asset):
    cleaned=asset.upper().replace('/','').replace('-','').replace(' ','')
    if cleaned in ['GOLD','XAU']: return 'XAUUSD'
    if cleaned in ['OIL','USOIL','WTIUSD','WTI']: return 'WTI'
    return cleaned if cleaned in SUPPORTED_ASSETS else 'EURUSD'
def get_supported_assets(): return SUPPORTED_ASSETS
class LiveMarketDataError(Exception): pass
def _parse_twelve_values(data):
    values=data.get('values')
    if not values:
        msg=data.get('message') or data.get('status') or str(data)[:180]
        raise LiveMarketDataError(f'Twelve Data returned no candle values: {msg}')
    candles=[]
    for row in reversed(values):
        candles.append({'open':float(row['open']),'high':float(row['high']),'low':float(row['low']),'close':float(row['close']),'datetime':row.get('datetime','')})
    if len(candles)<50: raise LiveMarketDataError('Not enough live candles received to calculate reliable zones.')
    return candles
def get_live_candles(asset, interval='5min', points=120):
    symbol=normalize_asset(asset); info=SUPPORTED_ASSETS[symbol]
    cache_key=f'candles:{symbol}:{interval}:{points}'
    cached=get_cache(cache_key, settings.MARKET_CACHE_SECONDS)
    if cached:
        candles,source_time=cached
        return {'asset':symbol,'display_name':info['display'],'candles':candles,'source':'twelve-data-live-cached','cache_age_seconds':cache_age_seconds(cache_key),'source_time':source_time}
    if not settings.TWELVEDATA_API_KEY: raise LiveMarketDataError('TWELVEDATA_API_KEY is missing. Add it in Railway Variables.')
    try:
        r=requests.get('https://api.twelvedata.com/time_series',params={'symbol':info['twelve'],'interval':interval,'outputsize':points,'apikey':settings.TWELVEDATA_API_KEY,'format':'JSON'},timeout=15)
        data=r.json()
    except Exception as exc: raise LiveMarketDataError(f'Cannot reach Twelve Data API: {exc}')
    if data.get('status')=='error': raise LiveMarketDataError(data.get('message','Unknown Twelve Data error'))
    candles=_parse_twelve_values(data); source_time=candles[-1].get('datetime','')
    set_cache(cache_key,(candles,source_time))
    return {'asset':symbol,'display_name':info['display'],'candles':candles,'source':'twelve-data-live','cache_age_seconds':0,'source_time':source_time}
