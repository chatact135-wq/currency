import time, requests
from app.config import settings
from app.services import cache
ASSETS={
'EURUSD':{'display':'EUR/USD','symbol':'OANDA:EUR_USD','pip':0.0001,'class':'forex'},
'GBPUSD':{'display':'GBP/USD','symbol':'OANDA:GBP_USD','pip':0.0001,'class':'forex'},
'XAUUSD':{'display':'Gold / XAUUSD','symbol':'OANDA:XAU_USD','pip':0.10,'class':'gold'},
'WTI':{'display':'WTI Oil','symbol':'OANDA:WTICO_USD','pip':0.01,'class':'oil'}}
class LiveDataError(Exception): pass
def normalize(a):
    x=a.upper().replace('/','').replace('-','').replace(' ','')
    if x in ['GOLD','XAU']: return 'XAUUSD'
    if x in ['OIL','USOIL','WTIUSD']: return 'WTI'
    return x if x in ASSETS else 'EURUSD'
def active_assets(): return [a for a in settings.ACTIVE_ASSETS if a in ASSETS]
def _get(path,params):
    if not settings.FINNHUB_API_KEY: raise LiveDataError('FINNHUB_API_KEY missing. Add it in Railway Variables.')
    params=dict(params); params['token']=settings.FINNHUB_API_KEY
    try: data=requests.get('https://finnhub.io/api/v1/'+path,params=params,timeout=15).json()
    except Exception as e: raise LiveDataError(f'Finnhub connection failed: {e}')
    if isinstance(data,dict) and data.get('error'): raise LiveDataError(str(data['error']))
    return data
def quote(asset):
    s=normalize(asset); key=f'q:{s}'; c=cache.get(key,5)
    if c: return {**c,'source':'finnhub-quote-cached','cache_age':cache.age(key)}
    data=_get('quote',{'symbol':ASSETS[s]['symbol']}); price=data.get('c') or data.get('pc')
    if not price: raise LiveDataError(f'Finnhub quote returned no price for {s}: {data}')
    res={'asset':s,'display':ASSETS[s]['display'],'price':float(price),'source':'finnhub-quote-live','cache_age':0,'source_time':int(data.get('t') or time.time())}
    cache.set(key,res); return res
def candles(asset,resolution='5',count=160):
    s=normalize(asset); key=f'c:{s}:{resolution}:{count}'; c=cache.get(key,settings.MARKET_CACHE_SECONDS)
    if c: return {**c,'source':'finnhub-candle-cached','cache_age':cache.age(key)}
    now=int(time.time()); seconds=int(resolution)*60 if str(resolution).isdigit() else 300; frm=now-seconds*(count+50)
    data=_get('forex/candle',{'symbol':ASSETS[s]['symbol'],'resolution':resolution,'from':frm,'to':now})
    if data.get('s')!='ok': raise LiveDataError(f'Finnhub candles not available for {s}: {data}')
    o,h,l,cl,t=data.get('o',[]),data.get('h',[]),data.get('l',[]),data.get('c',[]),data.get('t',[])
    if len(cl)<50: raise LiveDataError(f'Not enough Finnhub candles for {s}.')
    cs=[{'datetime':int(t[i]),'open':float(o[i]),'high':float(h[i]),'low':float(l[i]),'close':float(cl[i])} for i in range(len(cl))]
    q=quote(s); cs[-1]['close']=q['price']
    res={'asset':s,'display':ASSETS[s]['display'],'candles':cs[-count:],'quote_price':q['price'],'source':'finnhub-candle-live','cache_age':0,'source_time':cs[-1]['datetime']}
    cache.set(key,res); return res
