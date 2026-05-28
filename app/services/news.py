import requests
from app.config import settings
from app.services import cache
from app.services.session import info as session_info
QUERIES={'EURUSD':'EURUSD OR ECB OR Federal Reserve OR US dollar OR euro dollar','GBPUSD':'GBPUSD OR Bank of England OR UK inflation OR Federal Reserve','XAUUSD':'gold OR XAUUSD OR inflation OR treasury yields OR Federal Reserve','WTI':'WTI oil OR crude oil OR OPEC OR inventories'}
def get(asset):
    key=f'news:{asset}'; c=cache.get(key,settings.NEWS_CACHE_SECONDS)
    if c: return c
    countdown=session_info()['news_countdown']
    if not settings.NEWS_API_KEY: return {'connected':False,'score':0,'bias':'neutral','explanation':'NEWS_API_KEY missing.','headlines':[],'news_countdown':countdown}
    try:
        r=requests.get('https://newsapi.org/v2/everything',params={'q':QUERIES.get(asset,QUERIES['EURUSD']),'language':'en','sortBy':'publishedAt','pageSize':6,'apiKey':settings.NEWS_API_KEY},timeout=12); data=r.json()
    except Exception as e: return {'connected':False,'score':0,'bias':'neutral','explanation':str(e),'headlines':[],'news_countdown':countdown}
    if data.get('status')!='ok': return {'connected':False,'score':0,'bias':'neutral','explanation':data.get('message','News API error'),'headlines':[],'news_countdown':countdown}
    bull=['dovish','rate cut','weak dollar','safe haven','supply cut','inventories fall']; bear=['hawkish','rate hike','strong dollar','yields rise','inventories rise','demand weak']
    score=0; hits=[]; heads=[]
    for a in data.get('articles',[]):
        title=a.get('title') or ''; desc=a.get('description') or ''; txt=(title+' '+desc).lower(); local=0
        for w in bull:
            if w in txt: local+=4; hits.append(w)
        for w in bear:
            if w in txt: local-=4; hits.append(w)
        score+=local; heads.append({'title':title[:150],'source':(a.get('source') or {}).get('name',''),'score':local})
    score=max(-16,min(16,score)); bias='bullish' if score>4 else 'bearish' if score<-4 else 'neutral'
    res={'connected':True,'score':score,'bias':bias,'explanation':', '.join(hits[:5]) if hits else 'No strong headline bias.','headlines':heads,'news_countdown':countdown}
    cache.set(key,res); return res
