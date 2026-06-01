import requests
from app.config import settings
from app.models import MarketCandle
from app.services import cache
ASSETS={"EURUSD":{"display":"EUR/USD","twelve":"EUR/USD","pip":0.0001},"GBPUSD":{"display":"GBP/USD","twelve":"GBP/USD","pip":0.0001},"XAUUSD":{"display":"Gold / XAUUSD","twelve":"XAU/USD","pip":0.10},"WTI":{"display":"WTI Oil","twelve":"WTI/USD","pip":0.01}}
class LiveDataError(Exception): pass
def normalize(a):
    a=a.upper().replace("/","").replace("-","").replace(" ","")
    if a in ["GOLD","XAU"]: return "XAUUSD"
    if a in ["OIL","USOIL","WTIUSD"]: return "WTI"
    return a if a in ASSETS else "EURUSD"
def active_assets(): return [a for a in settings.ACTIVE_ASSETS if a in ASSETS]
def fetch_twelve(asset, outputsize=120, interval="5min"):
    sym=normalize(asset); key=f"td13:{sym}:{interval}:{outputsize}"
    c=cache.get(key,settings.MARKET_CACHE_SECONDS)
    if c: return {**c,"source":"twelvedata-cached","cache_age":cache.age(key)}
    if not settings.TWELVEDATA_API_KEY: raise LiveDataError("TWELVEDATA_API_KEY missing.")
    try:
        r=requests.get("https://api.twelvedata.com/time_series",params={"symbol":ASSETS[sym]["twelve"],"interval":interval,"outputsize":outputsize,"apikey":settings.TWELVEDATA_API_KEY,"format":"JSON"},timeout=15)
        data=r.json()
    except Exception as e: raise LiveDataError(f"Twelve Data failed: {e}")
    if data.get("status")=="error": raise LiveDataError(data.get("message","Twelve Data API error"))
    vals=data.get("values") or []
    if len(vals)<50: raise LiveDataError(data.get("message") or "Not enough candles.")
    out=[{"datetime":str(x.get("datetime","")),"open":float(x["open"]),"high":float(x["high"]),"low":float(x["low"]),"close":float(x["close"])} for x in reversed(vals)]
    res={"asset":sym,"display":ASSETS[sym]["display"],"candles":out,"price":out[-1]["close"],"source":"twelvedata-live","cache_age":0,"source_time":out[-1]["datetime"]}
    cache.set(key,res); return res
def store_candles(db,asset,candles,timeframe="5min"):
    sym=normalize(asset); n=0
    for c in candles:
        row=db.query(MarketCandle).filter(MarketCandle.asset==sym,MarketCandle.timeframe==timeframe,MarketCandle.candle_time==str(c["datetime"])).first()
        if row: row.open,row.high,row.low,row.close=c["open"],c["high"],c["low"],c["close"]
        else:
            db.add(MarketCandle(asset=sym,timeframe=timeframe,candle_time=str(c["datetime"]),open=c["open"],high=c["high"],low=c["low"],close=c["close"])); n+=1
    db.commit(); return n
def stored_candles(db,asset,limit=500):
    sym=normalize(asset); rows=db.query(MarketCandle).filter(MarketCandle.asset==sym).order_by(MarketCandle.id.desc()).limit(limit).all()
    return [{"datetime":r.candle_time,"open":r.open,"high":r.high,"low":r.low,"close":r.close} for r in reversed(rows)]
def snapshot(db,asset):
    live=fetch_twelve(asset,120); store_candles(db,live["asset"],live["candles"])
    hist=stored_candles(db,live["asset"],settings.HISTORY_CANDLE_LIMIT); candles=hist if len(hist)>=50 else live["candles"]
    return {"asset":live["asset"],"display":live["display"],"price":candles[-1]["close"],"candles":candles,"source":live["source"]+"+adaptive-history","cache_age":live["cache_age"],"source_time":candles[-1]["datetime"],"stored_candles":len(hist)}
def download_history(db,asset):
    live=fetch_twelve(asset,settings.HISTORY_CANDLE_LIMIT); ins=store_candles(db,live["asset"],live["candles"])
    return {"asset":live["asset"],"downloaded":len(live["candles"]),"inserted_or_new":ins,"source_time":live["source_time"]}
