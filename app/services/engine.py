from app.config import settings
from app.services.market import candles,normalize,ASSETS,LiveDataError
from app.services.indicators import build
from app.services.stages import setup_engine,trigger_engine,confirmation_engine
from app.services.session import info as session_info
from app.services.news import get as news_get
def rp(symbol,value):
    pip=ASSETS[symbol]['pip']
    if pip>=0.1: return round(float(value),2)
    if pip>=0.01: return round(float(value),3)
    return round(float(value),5)
def pip_count(symbol,a,b): return round(abs(a-b)/ASSETS[symbol]['pip'],1)
def decide_stage(setup,trigger,confirm):
    if setup['bias']=='NEUTRAL' and trigger['bias']=='NEUTRAL': return 'NO SETUP','NEUTRAL','No setup zone and no trigger.'
    if setup['bias']!='NEUTRAL' and abs(setup['score'])>=settings.SETUP_SCORE:
        if trigger['bias']==setup['bias'] and abs(trigger['score'])>=settings.TRIGGER_SCORE: return f"ACTIVE SCALP {setup['bias']}",setup['bias'],'Setup zone + trigger confirmation agree.'
        if trigger['bias']!='NEUTRAL' and trigger['bias']!=setup['bias']: return f"{trigger['bias']} PULLBACK WATCH",trigger['bias'],f"Trigger is opposite to {setup['bias']} setup; treat as pullback only."
        return f"{setup['bias']} SETUP - WAIT TRIGGER",setup['bias'],'Setup exists but trigger confirmation is not complete.'
    if trigger['bias']!='NEUTRAL' and abs(trigger['score'])>=settings.TRIGGER_SCORE: return f"{trigger['bias']} TRIGGER WITHOUT SETUP",trigger['bias'],'Trigger active but no strong setup zone; wait or reduce risk.'
    return 'WAIT',setup['bias'] if setup['bias']!='NEUTRAL' else trigger['bias'],'Weak setup/trigger.'
def build_plan(symbol,stage,direction,ind):
    price=ind['price']; pip=ASSETS[symbol]['pip']; atr=ind['atr']
    if 'ACTIVE SCALP' not in stage:
        if direction=='BUY':
            low=ind['support_soft']; high=price; display=f"Setup zone only: {rp(symbol,min(low,high))} → {rp(symbol,max(low,high))}"; trigger=rp(symbol,max(price,ind['resistance_soft']))
        elif direction=='SELL':
            high=ind['resistance_soft']; low=price; display=f"Setup zone only: {rp(symbol,max(high,low))} → {rp(symbol,min(high,low))}"; trigger=rp(symbol,min(price,ind['support_soft']))
        else:
            display='No setup zone yet'; trigger=rp(symbol,price)
        return {'entry_state':'not_active','has_exact_entry':False,'setup_zone_display':display,'trigger_level':trigger,'exact_entry_display':'No exact entry until trigger confirms','stop_loss':None,'tp1_partial_close':None,'tp2':None,'full_close':None,'invalidation':None,'after_tp1':'No trade management until ACTIVE SCALP signal.'}
    if pip==0.0001: width=max(settings.MIN_ENTRY_PIPS*pip,min(settings.MAX_ENTRY_PIPS*pip,atr*0.12))
    elif pip==0.10: width=max(0.8,min(3.5,atr*0.16))
    else: width=max(0.04,min(0.18,atr*0.16))
    if direction=='BUY':
        low=price-width*0.25; high=price+width*0.75; low,high=min(low,high),max(low,high); sl=low-max(width*1.4,atr*0.28); tp1=high+max(width*1.1,atr*0.32); tp2=high+max(width*2.0,atr*0.58); full=high+max(width*2.8,atr*0.78)
        return {'entry_state':'active','has_exact_entry':True,'direction':'ascending','exact_entry_display':f"{rp(symbol,low)} → {rp(symbol,high)}",'entry_pips':pip_count(symbol,low,high),'stop_loss':rp(symbol,sl),'invalidation':rp(symbol,sl),'tp1_partial_close':rp(symbol,tp1),'tp2':rp(symbol,tp2),'full_close':rp(symbol,full),'after_tp1':'Close 50% and move SL to breakeven.'}
    if direction=='SELL':
        high=price+width*0.25; low=price-width*0.75; high,low=max(high,low),min(high,low); sl=high+max(width*1.4,atr*0.28); tp1=low-max(width*1.1,atr*0.32); tp2=low-max(width*2.0,atr*0.58); full=low-max(width*2.8,atr*0.78)
        return {'entry_state':'active','has_exact_entry':True,'direction':'descending','exact_entry_display':f"{rp(symbol,high)} → {rp(symbol,low)}",'entry_pips':pip_count(symbol,high,low),'stop_loss':rp(symbol,sl),'invalidation':rp(symbol,sl),'tp1_partial_close':rp(symbol,tp1),'tp2':rp(symbol,tp2),'full_close':rp(symbol,full),'after_tp1':'Close 50% and move SL to breakeven.'}
    return build_plan(symbol,'WAIT','NEUTRAL',ind)
def signal(asset):
    symbol=normalize(asset)
    try: live=candles(symbol)
    except LiveDataError as exc: return {'status':'error','asset':symbol,'display':ASSETS[symbol]['display'],'message':'LIVE DATA ERROR — no live price shown.','error':str(exc)}
    cs=live['candles']; ind=build(cs); ses=session_info(); nw=news_get(symbol); setup=setup_engine(cs,ind); trigger=trigger_engine(cs,ind,setup['bias']); confirm=confirmation_engine(ind,nw,ses); stage,direction,note=decide_stage(setup,trigger,confirm); plan=build_plan(symbol,stage,direction,ind)
    timer=10*60 if 'ACTIVE SCALP' in stage else 15*60 if 'SETUP' in stage or 'WATCH' in stage else 5*60
    if 'ACTIVE SCALP' in stage: warning=f'{stage}: exact entry active only because trigger confirmed.'
    elif 'SETUP' in stage: warning=f'{stage}: do not enter yet; wait for trigger confirmation.'
    elif 'WATCH' in stage: warning=f'{stage}: pullback/watch only; no exact entry.'
    else: warning='No trade. Wait for setup zone and trigger confirmation.'
    return {'status':'live','asset':symbol,'display':ASSETS[symbol]['display'],'price':rp(symbol,ind['price']),'source':live['source'],'source_time':live['source_time'],'cache_age':live['cache_age'],'stage':stage,'direction':direction,'stage_note':note,'warning':warning,'setup_engine':setup,'trigger_engine':trigger,'confirmation_engine':confirm,'plan':plan,'timer_seconds':timer,'indicators':{'trend':ind['trend'],'rsi':ind['rsi'],'momentum':round(ind['momentum'],6),'pressure':round(ind['pressure'],3),'atr':rp(symbol,ind['atr']),'rejection':ind['rejection'],'displacement':ind['displacement']},'profile':{'poc':rp(symbol,ind['profile']['poc']),'val':rp(symbol,ind['profile']['val']),'vah':rp(symbol,ind['profile']['vah'])},'news':nw,'session':ses,'all_alerts':setup['alerts']+trigger['alerts']+confirm['alerts'],'logic_note':'V9 uses 3 stages: SETUP ZONE first, TRIGGER CONFIRMATION second, EXACT ENTRY only when active.'}
