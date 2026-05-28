import requests
from app.config import settings
from app.services import cache
ASSETS={
 'EURUSD':{'display':'EUR/USD','symbol':'EUR/USD','pip':0.0001},
 'GBPUSD':{'display':'GBP/USD','symbol':'GBP/USD','pip':0.0001},
 'XAUUSD':{'display':'Gold / XAUUSD','symbol':'XAU/USD','pip':0.10},
 'WTI':{'display':'WTI Oil','symbol':'WTI/USD','pip':0.01},
}
class LiveDataError(Exception): pass
def normalize(a):
    x=a.upper().replace('/','').replace('-','').replace(' ','')
    if x in ['GOLD','XAU']: return 'XAUUSD'
    if x in ['OIL','USOIL','WTIUSD']: return 'WTI'
    return x if x in ASSETS else 'EURUSD'
def active_assets(): return [a for a in settings.ACTIVE_ASSETS if a in ASSETS]
def candles(asset,interval='5min',outputsize=160):
    sym=normalize(asset); key=f'td:{sym}:{interval}:{outputsize}'
    c=cache.get(key,settings.MARKET_CACHE_SECONDS)
    if c: return {**c,'source':'twelve-data-live-cached','cache_age':cache.age(key)}
    if not settings.TWELVEDATA_API_KEY: raise LiveDataError('TWELVEDATA_API_KEY missing. No live price shown.')
    p={'symbol':ASSETS[sym]['symbol'],'interval':interval,'outputsize':outputsize,'apikey':settings.TWELVEDATA_API_KEY,'format':'JSON'}
    try:
        r=requests.get('https://api.twelvedata.com/time_series',params=p,timeout=15); data=r.json()
    except Exception as e: raise LiveDataError(f'Twelve Data connection failed: {e}')
    if data.get('status')=='error': raise LiveDataError(data.get('message','Twelve Data API error'))
    vals=data.get('values') or []
    if len(vals)<60: raise LiveDataError('Not enough live candles returned.')
    cs=[]
    for row in reversed(vals):
        vol=row.get('volume') or row.get('tick_volume') or 1
        try: vol=float(vol)
        except Exception: vol=1.0
        cs.append({'datetime':row.get('datetime',''),'open':float(row['open']),'high':float(row['high']),'low':float(row['low']),'close':float(row['close']),'volume':vol})
    res={'asset':sym,'display':ASSETS[sym]['display'],'candles':cs,'source':'twelve-data-live','source_time':cs[-1]['datetime'],'cache_age':0}
    cache.set(key,res); return res
