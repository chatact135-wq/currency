import requests
from app.config import settings
from app.services.cache import get_cache,set_cache,age
from app.services.session_engine import session
QUERIES={'EURUSD':'EURUSD OR ECB OR Federal Reserve OR US dollar','GBPUSD':'GBPUSD OR Bank of England OR UK inflation OR Federal Reserve','XAUUSD':'gold OR Federal Reserve OR inflation OR treasury yields','WTI':'WTI oil OR crude oil OR OPEC OR EIA inventories'}
def news(asset):
    key=f'news:{asset}'; c=get_cache(key,settings.NEWS_CACHE_SECONDS)
    if c: return {**c,'cache_age':age(key)}
    if not settings.NEWS_API_KEY: return {'connected':False,'bias':'neutral','score':0,'source':'NEWS_API_KEY missing','headlines':[],'explanation':'Add NEWS_API_KEY for real news sentiment.','next_event':{'event':'US/London high-impact window','countdown_seconds':session()['news_window_countdown']},'cache_age':None}
    try:
        r=requests.get('https://newsapi.org/v2/everything',params={'q':QUERIES.get(asset,QUERIES['EURUSD']),'language':'en','sortBy':'publishedAt','pageSize':6,'apiKey':settings.NEWS_API_KEY},timeout=12); data=r.json()
    except Exception as e: return {'connected':False,'bias':'neutral','score':0,'source':'news error','headlines':[],'explanation':str(e),'next_event':{'event':'US/London high-impact window','countdown_seconds':session()['news_window_countdown']},'cache_age':None}
    if data.get('status')!='ok': return {'connected':False,'bias':'neutral','score':0,'source':'news error','headlines':[],'explanation':data.get('message','News API error'),'next_event':{'event':'US/London high-impact window','countdown_seconds':session()['news_window_countdown']},'cache_age':None}
    pos=['dovish','rate cut','weak dollar','safe haven','supply cut','inventories fall']; neg=['hawkish','rate hike','strong dollar','yields rise','inventories rise','demand weak']
    score=0; heads=[]; hits=[]
    for a in data.get('articles',[]):
        title=a.get('title') or ''; txt=(title+' '+(a.get('description') or '')).lower(); s=0
        for p in pos:
            if p in txt: s+=8; hits.append(p)
        for n in neg:
            if n in txt: s-=8; hits.append(n)
        score+=s; heads.append({'title':title[:160],'source':(a.get('source') or {}).get('name',''),'score':s})
    score=max(-25,min(25,score)); bias='bullish' if score>6 else 'bearish' if score<-6 else 'neutral'
    res={'connected':True,'bias':bias,'score':score,'source':'NewsAPI live','headlines':heads,'explanation':'News keywords: '+(', '.join(hits[:5]) if hits else 'no strong bias found'),'next_event':{'event':'US/London high-impact window','countdown_seconds':session()['news_window_countdown']},'cache_age':0}
    set_cache(key,res); return res
