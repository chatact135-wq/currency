import requests
from app.config import settings
from app.services import cache
from app.services.session import info as session_info
QUERIES={'EURUSD':'EURUSD OR ECB OR Federal Reserve OR US dollar OR euro dollar','GBPUSD':'GBPUSD OR Bank of England OR UK inflation OR Federal Reserve','XAUUSD':'gold OR XAUUSD OR inflation OR treasury yields OR Federal Reserve','WTI':'WTI oil OR crude oil OR OPEC OR oil inventories'}
def get(asset):
    key=f'news:{asset}'; cached=cache.get(key,settings.NEWS_CACHE_SECONDS)
    if cached: return cached
    countdown=session_info()['news_countdown']
    if not settings.NEWS_API_KEY: return {'connected':False,'score':0,'bias':'neutral','headlines':[],'explanation':'NEWS_API_KEY missing.','news_countdown':countdown}
    try:
        r=requests.get('https://newsapi.org/v2/everything',params={'q':QUERIES.get(asset,QUERIES['EURUSD']),'language':'en','sortBy':'publishedAt','pageSize':6,'apiKey':settings.NEWS_API_KEY},timeout=12); data=r.json()
    except Exception as e: return {'connected':False,'score':0,'bias':'neutral','headlines':[],'explanation':str(e),'news_countdown':countdown}
    if data.get('status')!='ok': return {'connected':False,'score':0,'bias':'neutral','headlines':[],'explanation':data.get('message','News API error'),'news_countdown':countdown}
    total=0; headlines=[]
    for a in data.get('articles',[]):
        title=a.get('title') or ''; lower=(title+' '+(a.get('description') or '')).lower(); sc=0
        for w in ['dovish','rate cut','weak dollar','safe haven','supply cut','inventories fall','stimulus']:
            if w in lower: sc+=5
        for w in ['hawkish','rate hike','strong dollar','yields rise','inventories rise','demand weak','recession']:
            if w in lower: sc-=5
        total+=sc; headlines.append({'title':title[:150],'source':(a.get('source') or {}).get('name',''),'score':sc})
    total=max(-18,min(18,total)); bias='bullish' if total>4 else 'bearish' if total<-4 else 'neutral'
    res={'connected':True,'score':total,'bias':bias,'headlines':headlines,'explanation':'News headline score','news_countdown':countdown}; cache.set(key,res); return res
