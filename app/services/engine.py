from app.config import settings
from app.services.market import candles, normalize, ASSETS, LiveDataError
from app.services.indicators import base
from app.services.profile import frequency_volume_profile
from app.services.smc_sb_raven import smc_model, sb_model, raven_model
from app.services.news import get as news_get
from app.services.session import info as session_info

def rp(sym,v):
    pip=ASSETS[sym]['pip']
    if pip>=0.1: return round(float(v),2)
    if pip>=0.01: return round(float(v),3)
    return round(float(v),5)
def pips(sym,lo,hi): return round(abs(hi-lo)/ASSETS[sym]['pip'],1)
def action_from(score):
    if score>=78: return 'STRONG BUY'
    if score>=settings.MIN_TRADE_SCORE: return 'BUY'
    if score>=38: return 'SCALP BUY'
    if score<=-78: return 'STRONG SELL'
    if score<=-settings.MIN_TRADE_SCORE: return 'SELL'
    if score<=-38: return 'SCALP SELL'
    return 'BUY WATCH' if score>18 else 'SELL WATCH' if score<-18 else 'WAIT'
def plan(sym,act,ind,profile):
    price=ind['price']; pip=ASSETS[sym]['pip']; atr=ind['atr']
    width = max(3*pip, min(8*pip, atr*0.14)) if pip==0.0001 else max(1.0,min(4.0,atr*.16)) if pip==0.10 else max(.04,min(.18,atr*.16))
    direction='buy' if 'BUY' in act else 'sell' if 'SELL' in act else 'none'
    if direction=='buy':
        lo=max(min(profile['val'], price), price-width); hi=min(max(profile['poc'],price), price+width)
        sl=lo-max(width*1.8,atr*.30); tp1=hi+max(width*1.4,atr*.30); tp2=hi+max(width*2.5,atr*.55); full=hi+max(width*3.3,atr*.75); interval_display=f'{rp(sym,lo)} → {rp(sym,hi)}'
    elif direction=='sell':
        hi=min(max(profile['vah'], price), price+width); lo=max(min(profile['poc'],price), price-width)
        sl=hi+max(width*1.8,atr*.30); tp1=lo-max(width*1.4,atr*.30); tp2=lo-max(width*2.5,atr*.55); full=lo-max(width*3.3,atr*.75); interval_display=f'{rp(sym,hi)} → {rp(sym,lo)}'
    else:
        lo=profile['val']; hi=profile['vah']; sl=price-atr; tp1=price+atr; tp2=price+atr*1.6; full=price+atr*2.1; interval_display=f'{rp(sym,lo)} → {rp(sym,hi)}'
    return {'direction':direction,'entry':{'low':rp(sym,lo),'high':rp(sym,hi),'display':interval_display,'pips':pips(sym,lo,hi)},'stop_loss':rp(sym,sl),'tp1_partial_close':rp(sym,tp1),'tp2':rp(sym,tp2),'full_close':rp(sym,full),'invalidation':rp(sym,sl),'after_tp1':'Close 50% and move SL to breakeven.'}
def signal(asset):
    sym=normalize(asset)
    try: live=candles(sym)
    except LiveDataError as e: return {'status':'error','asset':sym,'display':ASSETS[sym]['display'],'message':'LIVE DATA ERROR — no live price shown.','error':str(e)}
    cs=live['candles']; ind=base(cs); nw=news_get(sym); ses=session_info()
    prof=frequency_volume_profile(cs); smc=smc_model(cs,ind); sb=sb_model(cs,ind); raven=raven_model(cs,ind,nw['score'])
    models=[prof,smc,sb,raven]
    score=0; alerts=[]
    for m in models:
        score += m.get('score',0)
        if m.get('triggered'):
            alerts.append({'name':m['name'],'direction':m.get('direction','neutral'),'score':m.get('score',0),'message':m.get('message') or '; '.join(m.get('alerts',[]))})
    if ind['trend']=='bullish': score+=10
    elif ind['trend']=='bearish': score-=10
    if ind['momentum']>0.00025: score+=9
    elif ind['momentum']<-0.00025: score-=9
    if ind['pressure']>0.25: score+=7
    elif ind['pressure']<-0.25: score-=7
    score += ses['score'] + nw['score']
    act=action_from(score); trplan=plan(sym,act,ind,prof)
    return {'status':'live','asset':sym,'display':ASSETS[sym]['display'],'price':rp(sym,ind['price']),'action':act,'score':round(score,1),'bias':'buy' if score>0 else 'sell' if score<0 else 'neutral','source':live['source'],'source_time':live['source_time'],'cache_age':live['cache_age'],'strategy_alerts':alerts,'models':{'profile':prof,'smc':smc,'sb':sb,'raven':raven},'indicators':{'trend':ind['trend'],'rsi':ind['rsi'],'momentum':round(ind['momentum'],6),'pressure':round(ind['pressure'],3),'atr':rp(sym,ind['atr'])},'plan':trplan,'timer_seconds':10*60 if 'SCALP' in act or 'WATCH' in act else 30*60,'news':nw,'session':ses,'warning':('Use the descending sell interval only.' if 'SELL' in act else 'Use the ascending buy interval only.' if 'BUY' in act else 'No clean execution; watch alerts only.'),'note':'V7 focuses only on Frequency/Volume Profile, SB, SMC, and RAVEN alerts. Each alert appears separately when it happens.'}
