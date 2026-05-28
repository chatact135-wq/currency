import requests
from app.config import settings
from app.services.cache import get_cache,set_cache,cache_age_seconds
ASSET_NEWS_CONFIG={
 'EURUSD':{'query':'(EURUSD OR EUR/USD OR euro dollar OR ECB OR Federal Reserve OR US dollar)','positive_keywords':['euro strengthens','ecb hawkish','dollar weakens','fed dovish','eurozone growth'],'negative_keywords':['dollar strengthens','ecb dovish','fed hawkish','euro weakens','recession']},
 'GBPUSD':{'query':'(GBPUSD OR GBP/USD OR pound dollar OR Bank of England OR UK inflation OR Federal Reserve)','positive_keywords':['pound strengthens','boe hawkish','dollar weakens','uk growth'],'negative_keywords':['pound weakens','boe dovish','dollar strengthens','uk recession']},
 'XAUUSD':{'query':'(gold OR XAUUSD OR XAU/USD OR Federal Reserve OR inflation OR treasury yields OR geopolitical)','positive_keywords':['gold rises','safe haven','inflation rises','geopolitical tension','yields fall'],'negative_keywords':['gold falls','yields rise','dollar strengthens','fed hawkish']},
 'WTI':{'query':'(WTI oil OR crude oil OR oil inventory OR OPEC OR EIA crude)','positive_keywords':['oil rises','supply cut','inventories fall','opec cuts','demand rises'],'negative_keywords':['oil falls','inventories rise','demand weakens','supply increases']}}
def _score_text(text, config):
    lower=text.lower(); score=0.0; hits=[]
    for kw in config['positive_keywords']:
        if kw in lower: score+=0.18; hits.append(f'positive: {kw}')
    for kw in config['negative_keywords']:
        if kw in lower: score-=0.18; hits.append(f'negative: {kw}')
    if 'rate cut' in lower or 'dovish' in lower: score+=0.05; hits.append('macro: dovish/rate-cut language')
    if 'rate hike' in lower or 'hawkish' in lower: score-=0.05; hits.append('macro: hawkish/rate-hike language')
    return score,hits
def get_news_sentiment(asset):
    symbol=asset.upper(); config=ASSET_NEWS_CONFIG.get(symbol,ASSET_NEWS_CONFIG['EURUSD']); cache_key=f'news:{symbol}'
    cached=get_cache(cache_key,settings.NEWS_CACHE_SECONDS)
    if cached:
        cached=cached.copy(); cached['cache_age_seconds']=cache_age_seconds(cache_key); cached['source']=cached['source']+'-cached'; return cached
    if not settings.NEWS_API_KEY:
        return {'connected':False,'source':'news-api-not-connected','bias':'neutral','score':0.0,'headlines':[],'explanation':'NEWS_API_KEY is missing. Add it in Railway Variables for real news sentiment.','cache_age_seconds':None}
    try:
        r=requests.get('https://newsapi.org/v2/everything',params={'q':config['query'],'language':'en','sortBy':'publishedAt','pageSize':8,'apiKey':settings.NEWS_API_KEY},timeout=12); data=r.json()
    except Exception as exc:
        return {'connected':False,'source':'news-api-error','bias':'neutral','score':0.0,'headlines':[],'explanation':f'Could not reach NewsAPI: {exc}','cache_age_seconds':None}
    if data.get('status')!='ok':
        return {'connected':False,'source':'news-api-error','bias':'neutral','score':0.0,'headlines':[],'explanation':data.get('message','NewsAPI returned an error.'),'cache_age_seconds':None}
    headlines=[]; total=0.0; all_hits=[]
    for a in data.get('articles',[]):
        title=a.get('title') or ''; desc=a.get('description') or ''; source=(a.get('source') or {}).get('name','')
        score,hits=_score_text(f'{title}. {desc}',config); total+=score; all_hits.extend(hits); headlines.append({'title':title[:180],'source':source,'publishedAt':a.get('publishedAt',''),'score':round(score,3)})
    normalized=max(-0.45,min(0.45,total)); bias='bullish' if normalized>0.12 else 'bearish' if normalized<-0.12 else 'neutral'
    result={'connected':True,'source':'newsapi-live','bias':bias,'score':round(normalized,3),'headlines':headlines,'explanation':'Real news scanned from NewsAPI. '+(', '.join(all_hits[:4]) if all_hits else 'No strong keyword bias detected.'),'cache_age_seconds':0}
    set_cache(cache_key,result.copy()); return result
