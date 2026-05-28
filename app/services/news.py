import requests
from app.config import settings
from app.services import cache
from app.services.session import info as session_info
QUERIES={'EURUSD':['eur','usd','ecb','federal','dollar'],'GBPUSD':['gbp','pound','boe','uk','federal'],'XAUUSD':['gold','xau','inflation','yields','federal','dollar'],'WTI':['oil','crude','opec','inventory']}
def score_text(text,asset):
    t=text.lower(); score=0; hits=[]; bull=['dovish','rate cut','weak dollar','safe haven','supply cut','inventories fall','stimulus','yields fall']; bear=['hawkish','rate hike','strong dollar','yields rise','inventories rise','demand weak','recession']
    for word in bull:
        if word in t: score+=5; hits.append(word)
    for word in bear:
        if word in t: score-=5; hits.append(word)
    return score,hits
def get(asset):
    key=f'news:{asset}'; cached=cache.get(key,settings.NEWS_CACHE_SECONDS)
    if cached: return cached
    countdown=session_info()['news_countdown']
    if not settings.FINNHUB_API_KEY: return {'connected':False,'score':0,'bias':'neutral','headlines':[],'explanation':'FINNHUB_API_KEY missing.','news_countdown':countdown}
    try: data=requests.get('https://finnhub.io/api/v1/news',params={'category':'forex','token':settings.FINNHUB_API_KEY},timeout=12).json()
    except Exception as e: return {'connected':False,'score':0,'bias':'neutral','headlines':[],'explanation':str(e),'news_countdown':countdown}
    if not isinstance(data,list): return {'connected':False,'score':0,'bias':'neutral','headlines':[],'explanation':str(data)[:160],'news_countdown':countdown}
    keys=QUERIES.get(asset,[]); total=0; hits=[]; heads=[]
    for a in data[:30]:
        title=a.get('headline') or ''; summary=a.get('summary') or ''; text=(title+' '+summary).lower()
        if len(heads)<8 and any(k in text for k in keys):
            sc,h=score_text(text,asset); total+=sc; hits+=h; heads.append({'title':title[:150],'source':a.get('source',''),'score':sc})
    total=max(-20,min(20,total)); bias='bullish' if total>4 else 'bearish' if total<-4 else 'neutral'
    res={'connected':True,'score':total,'bias':bias,'headlines':heads,'explanation':', '.join(hits[:6]) if hits else 'No strong relevant headline bias.','news_countdown':countdown}
    cache.set(key,res); return res
