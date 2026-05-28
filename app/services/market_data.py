import requests
from app.config import settings
from app.services.cache import get_cache,set_cache,age
SUPPORTED_ASSETS={
 'EURUSD':{'display':'EUR/USD','twelve':'EUR/USD','pip':0.0001},
 'GBPUSD':{'display':'GBP/USD','twelve':'GBP/USD','pip':0.0001},
 'XAUUSD':{'display':'Gold / XAUUSD','twelve':'XAU/USD','pip':0.10},
 'WTI':{'display':'WTI Oil','twelve':'WTI/USD','pip':0.01},
}
class LiveDataError(Exception): pass
def normalize_asset(a):
    c=a.upper().replace('/','').replace('-','').replace(' ','')
    if c in ['GOLD','XAU']: return 'XAUUSD'
    if c in ['OIL','USOIL','WTIUSD']: return 'WTI'
    return c if c in SUPPORTED_ASSETS else 'EURUSD'
def active_assets(): return [a for a in settings.ACTIVE_ASSETS if a in SUPPORTED_ASSETS]
def get_candles(asset,interval='5min',points=120):
    sym=normalize_asset(asset); key=f'td:{sym}:{interval}:{points}'
    cached=get_cache(key,settings.MARKET_CACHE_SECONDS)
    if cached: return {**cached,'source':'twelve-data-live-cached','cache_age':age(key)}
    if not settings.TWELVEDATA_API_KEY: raise LiveDataError('TWELVEDATA_API_KEY missing')
    info=SUPPORTED_ASSETS[sym]
    try:
        r=requests.get('https://api.twelvedata.com/time_series',params={'symbol':info['twelve'],'interval':interval,'outputsize':points,'apikey':settings.TWELVEDATA_API_KEY,'format':'JSON'},timeout=15)
        data=r.json()
    except Exception as e: raise LiveDataError(f'Twelve Data connection failed: {e}')
    if data.get('status')=='error': raise LiveDataError(data.get('message','Twelve Data API error'))
    vals=data.get('values') or []
    if len(vals)<40: raise LiveDataError('Not enough live candles returned')
    candles=[]
    for row in reversed(vals):
        candles.append({'datetime':row.get('datetime',''),'open':float(row['open']),'high':float(row['high']),'low':float(row['low']),'close':float(row['close'])})
    res={'asset':sym,'display_name':info['display'],'candles':candles,'source':'twelve-data-live','cache_age':0,'source_time':candles[-1].get('datetime','')}
    set_cache(key,res); return res
