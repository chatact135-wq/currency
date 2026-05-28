from app.config import settings
from app.services.market import candles,normalize,ASSETS,LiveDataError
from app.services.indicators import build
from app.services.weights import w
from app.services.session import info as session_info
from app.services.news import get as news_get

def alert(layer,model,direction,score,message,interpretation=''):
    return {'layer':layer,'model':model,'direction':direction,'score':round(score,1),'message':message,'interpretation':interpretation}
def rp(symbol,value):
    pip=ASSETS[symbol]['pip']
    if pip>=0.1: return round(float(value),2)
    if pip>=0.01: return round(float(value),3)
    return round(float(value),5)
def pip_count(symbol,a,b): return round(abs(a-b)/ASSETS[symbol]['pip'],1)
def master_bias_engine(symbol,cs,ind):
    wt=w(symbol); alerts=[]; buy=sell=0; last=cs[-1]
    if last['low']<ind['prev_low'] and last['close']>ind['prev_low']:
        sc=28*wt['sb']; buy+=sc; alerts.append(alert('Master Bias','SB Liquidity','BUY',sc,'Bullish sweep below previous low.','Primary direction'))
    elif last['high']>ind['prev_high'] and last['close']<ind['prev_high']:
        sc=28*wt['sb']; sell+=sc; alerts.append(alert('Master Bias','SB Liquidity','SELL',-sc,'Bearish sweep above previous high.','Primary direction'))
    recent=cs[-15:-1]; hi=max(x['high'] for x in recent); lo=min(x['low'] for x in recent)
    if last['close']>hi:
        sc=26*wt['smc']; buy+=sc; alerts.append(alert('Master Bias','SMC Structure','BUY',sc,'Bullish BOS/CHOCH above recent structure.','Primary direction'))
    elif last['close']<lo:
        sc=26*wt['smc']; sell+=sc; alerts.append(alert('Master Bias','SMC Structure','SELL',-sc,'Bearish BOS/CHOCH below recent structure.','Primary direction'))
    a,b,c=cs[-3],cs[-2],cs[-1]
    if c['low']>a['high']:
        sc=14*wt['smc']; buy+=sc; alerts.append(alert('Master Bias','SMC FVG','BUY',sc,'Bullish FVG setup zone.','Direction support'))
    elif c['high']<a['low']:
        sc=14*wt['smc']; sell+=sc; alerts.append(alert('Master Bias','SMC FVG','SELL',-sc,'Bearish FVG setup zone.','Direction support'))
    prof=ind['profile']; price=ind['price']
    if price>prof['vah']:
        sc=16*wt['profile']; buy+=sc; alerts.append(alert('Master Bias','Frequency Profile','BUY',sc,'Price accepted above VAH.','Auction direction'))
    elif price<prof['val']:
        sc=16*wt['profile']; sell+=sc; alerts.append(alert('Master Bias','Frequency Profile','SELL',-sc,'Price accepted below VAL.','Auction direction'))
    elif abs(price-prof['poc'])<=ind['atr']*0.25:
        alerts.append(alert('Master Bias','Frequency Profile','NEUTRAL',0,'Price near POC balance area.','Avoid forcing direction'))
    if ind['trend']=='bullish':
        sc=7*wt['trend']; buy+=sc; alerts.append(alert('Master Bias','Trend Bias','BUY',sc,'EMA trend bullish.','Direction confirmation only'))
    elif ind['trend']=='bearish':
        sc=7*wt['trend']; sell+=sc; alerts.append(alert('Master Bias','Trend Bias','SELL',-sc,'EMA trend bearish.','Direction confirmation only'))
    net=buy-sell; bias='NEUTRAL' if abs(net)<10 else ('BUY' if net>0 else 'SELL')
    return {'bias':bias,'buy_score':round(buy,1),'sell_score':round(sell,1),'net':round(net,1),'alerts':alerts}
def execution_engine(symbol,ind,master_bias):
    wt=w(symbol); alerts=[]; buy=sell=0
    if ind['pressure']>0.25:
        sc=14*wt['raven']; buy+=sc; alerts.append(alert('Execution','RAVEN Pressure','BUY',sc,'RAVEN bullish candle pressure.','Timing if master BUY; pullback/risk if master SELL.'))
    elif ind['pressure']<-0.25:
        sc=14*wt['raven']; sell+=sc; alerts.append(alert('Execution','RAVEN Pressure','SELL',-sc,'RAVEN bearish candle pressure.','Timing if master SELL; pullback/risk if master BUY.'))
    if ind['momentum']>0.00025:
        sc=16*wt['raven']; buy+=sc; alerts.append(alert('Execution','RAVEN Momentum','BUY',sc,'RAVEN bullish acceleration.','Execution timing'))
    elif ind['momentum']<-0.00025:
        sc=16*wt['raven']; sell+=sc; alerts.append(alert('Execution','RAVEN Momentum','SELL',-sc,'RAVEN bearish acceleration.','Execution timing'))
    if ind['rejection']['direction']=='BUY': buy+=10; alerts.append(alert('Execution','Reaction Wick','BUY',10,'Bullish rejection wick.','Entry trigger'))
    elif ind['rejection']['direction']=='SELL': sell+=10; alerts.append(alert('Execution','Reaction Wick','SELL',-10,'Bearish rejection wick.','Entry trigger'))
    if ind['displacement']['direction']=='BUY': buy+=12; alerts.append(alert('Execution','Displacement','BUY',12,'Bullish displacement candle.','Entry trigger'))
    elif ind['displacement']['direction']=='SELL': sell+=12; alerts.append(alert('Execution','Displacement','SELL',-12,'Bearish displacement candle.','Entry trigger'))
    net=buy-sell; bias='BUY' if net>8 else 'SELL' if net<-8 else 'NEUTRAL'
    return {'bias':bias,'buy_score':round(buy,1),'sell_score':round(sell,1),'net':round(net,1),'alerts':alerts}
def confirmation_engine(symbol,ind,news,session):
    wt=w(symbol); alerts=[]; mod=0; risk=0
    if ind['rsi']<=32: mod+=5; alerts.append(alert('Confirmation','RSI','BUY',5,'RSI oversold.','Confidence modifier'))
    elif ind['rsi']>=68: mod-=5; alerts.append(alert('Confirmation','RSI','SELL',-5,'RSI overbought.','Confidence modifier'))
    if news.get('score',0)>0:
        sc=min(12,abs(news['score'])*wt['news']); mod+=sc; alerts.append(alert('Confirmation','News','BUY',sc,'News bias bullish: '+news.get('explanation',''),'Macro confidence'))
    elif news.get('score',0)<0:
        sc=min(12,abs(news['score'])*wt['news']); mod-=sc; alerts.append(alert('Confirmation','News','SELL',-sc,'News bias bearish: '+news.get('explanation',''),'Macro confidence'))
    if session['score']>0: mod+=session['score']; alerts.append(alert('Confirmation','Session','NEUTRAL',session['score'],'Good liquidity: '+session['name'],'Confidence boost'))
    elif session['score']<0: risk+=abs(session['score']); alerts.append(alert('Confirmation','Session','NEUTRAL',session['score'],'Low liquidity: '+session['name'],'Risk penalty'))
    return {'modifier':round(mod,1),'risk_penalty':round(risk,1),'alerts':alerts}
def interpret(master,execution):
    if master['bias']=='NEUTRAL' and execution['bias']=='NEUTRAL': return 'No clear bias or trigger.'
    if master['bias']!='NEUTRAL' and execution['bias']!='NEUTRAL' and master['bias']!=execution['bias']: return f"{execution['bias']} pullback/risk inside {master['bias']} master bias. Do not reverse unless structure changes."
    if master['bias']!='NEUTRAL' and execution['bias']=='NEUTRAL': return f"{master['bias']} setup exists; waiting for execution trigger."
    if master['bias']=='NEUTRAL' and execution['bias']!='NEUTRAL': return f"{execution['bias']} execution active, but master bias is not strong enough."
    return 'Master bias and execution are aligned.'
def probabilities(master,execution,confirm):
    buy=master['buy_score']+execution['buy_score']; sell=master['sell_score']+execution['sell_score']; m=confirm['modifier']
    if m>0: buy+=m
    elif m<0: sell+=abs(m)
    total=buy+sell+25; up=max(5,min(90,buy/total*100)); down=max(5,min(90,sell/total*100)); side=max(5,100-up-down); t=up+down+side
    return {'up':round(up/t*100,1),'sideways':round(side/t*100,1),'down':round(down/t*100,1)}
def risk_level(ind,session,conflict):
    r=0
    if session['score']<0: r+=18
    if 'pullback/risk' in conflict: r+=20
    return 'HIGH' if r>=28 else 'MEDIUM' if r>=12 else 'LOW'
def grade(conf,risk,active):
    if not active: return 'B' if conf>=68 else 'C'
    if conf>=88 and risk=='LOW': return 'A+'
    if conf>=76 and risk in ['LOW','MEDIUM']: return 'A'
    if conf>=64: return 'B'
    if conf>=52: return 'C'
    return 'D'
def decide(master,execution,confirm,ind,session):
    conflict=interpret(master,execution); probs=probabilities(master,execution,confirm); bias=master['bias'] if master['bias']!='NEUTRAL' else execution['bias']; risk=risk_level(ind,session,conflict)
    aligned=master['bias']!='NEUTRAL' and master['bias']==execution['bias']; ms=abs(master['net']); es=abs(execution['net']); conf=min(95,max(35,ms*0.75+es*0.65+abs(confirm['modifier'])*0.7-confirm['risk_penalty']))
    if aligned and conf>=settings.ACTIVE_SCORE and risk!='HIGH': action=f'ACTIVE SCALP {bias}'; stage='EXECUTION ACTIVE'; active=True
    elif master['bias']!='NEUTRAL' and ms>=settings.SETUP_SCORE: action=f"{master['bias']} SETUP READY"; stage='SETUP READY'; active=False
    elif execution['bias']!='NEUTRAL' and es>=settings.WATCH_SCORE: action=f"{execution['bias']} TRIGGER WATCH"; stage='TRIGGER WATCH'; active=False
    else: action='WAIT'; stage='WAIT'; active=False
    return {'action':action,'stage':stage,'active':active,'bias':bias,'confidence':round(conf,1),'grade':grade(conf,risk,active),'risk_level':risk,'probabilities':probs,'conflict_interpretation':conflict}
def build_plan(symbol,decision,ind):
    direction=decision['bias']; price=ind['price']; pip=ASSETS[symbol]['pip']; atr=ind['atr']
    if not decision['active']:
        if direction=='BUY': setup=f"{rp(symbol,min(ind['support_soft'],price))} → {rp(symbol,max(ind['support_soft'],price))}"; trigger=ind['resistance_soft']
        elif direction=='SELL': setup=f"{rp(symbol,max(ind['resistance_soft'],price))} → {rp(symbol,min(ind['resistance_soft'],price))}"; trigger=ind['support_soft']
        else: setup='No valid setup zone'; trigger=price
        return {'has_exact_entry':False,'entry_state':'not_active','setup_zone':setup,'trigger_level':rp(symbol,trigger),'exact_entry':'No exact entry until ACTIVE SCALP confirms.','after_tp1':'No trade management until exact entry is active.'}
    if pip==0.0001: width=max(settings.MIN_ENTRY_PIPS*pip,min(settings.MAX_ENTRY_PIPS*pip,atr*0.12))
    elif pip==0.10: width=max(0.8,min(3.5,atr*0.16))
    else: width=max(0.04,min(0.18,atr*0.16))
    if direction=='BUY':
        low=price-width*0.25; high=price+width*0.75; low,high=min(low,high),max(low,high); sl=low-max(width*1.4,atr*0.28); tp1=high+max(width*1.1,atr*0.32); tp2=high+max(width*2,atr*0.58); full=high+max(width*2.8,atr*0.78)
        return {'has_exact_entry':True,'entry_state':'active','direction':'ascending','exact_entry':f'{rp(symbol,low)} → {rp(symbol,high)}','entry_pips':pip_count(symbol,low,high),'stop_loss':rp(symbol,sl),'invalidation':rp(symbol,sl),'tp1_partial_close':rp(symbol,tp1),'tp2':rp(symbol,tp2),'full_close':rp(symbol,full),'after_tp1':'Close 50% and move SL to breakeven.'}
    if direction=='SELL':
        high=price+width*0.25; low=price-width*0.75; high,low=max(high,low),min(high,low); sl=high+max(width*1.4,atr*0.28); tp1=low-max(width*1.1,atr*0.32); tp2=low-max(width*2,atr*0.58); full=low-max(width*2.8,atr*0.78)
        return {'has_exact_entry':True,'entry_state':'active','direction':'descending','exact_entry':f'{rp(symbol,high)} → {rp(symbol,low)}','entry_pips':pip_count(symbol,high,low),'stop_loss':rp(symbol,sl),'invalidation':rp(symbol,sl),'tp1_partial_close':rp(symbol,tp1),'tp2':rp(symbol,tp2),'full_close':rp(symbol,full),'after_tp1':'Close 50% and move SL to breakeven.'}
    return {'has_exact_entry':False,'exact_entry':'No valid entry.'}
def signal(asset):
    symbol=normalize(asset)
    try: live=candles(symbol)
    except LiveDataError as exc: return {'status':'error','asset':symbol,'display':ASSETS[symbol]['display'],'message':'LIVE DATA ERROR — no live price shown.','error':str(exc)}
    cs=live['candles']; ind=build(cs); ses=session_info(); nw=news_get(symbol); master=master_bias_engine(symbol,cs,ind); execution=execution_engine(symbol,ind,master['bias']); confirm=confirmation_engine(symbol,ind,nw,ses); dec=decide(master,execution,confirm,ind,ses); plan=build_plan(symbol,dec,ind)
    timer=10*60 if dec['active'] else 15*60 if 'SETUP' in dec['stage'] else 5*60
    if dec['active']: warning=f"{dec['action']}: exact entry active. Use {plan.get('direction','')} interval only."
    elif 'SETUP' in dec['stage']: warning=f"{dec['action']}: setup is ready, but wait for execution trigger."
    elif 'TRIGGER' in dec['stage']: warning=f"{dec['action']}: trigger exists but master bias is weak."
    else: warning='WAIT: no clean high-quality setup.'
    alerts=master['alerts']+execution['alerts']+confirm['alerts']; features={'trend':ind['trend'],'rsi':ind['rsi'],'atr':ind['atr'],'momentum':ind['momentum'],'pressure':ind['pressure'],'master_bias':master['bias'],'execution_bias':execution['bias'],'news_score':nw.get('score',0),'session':ses['name']}
    return {'status':'live','asset':symbol,'display':ASSETS[symbol]['display'],'price':rp(symbol,ind['price']),'source':live['source'],'source_time':live['source_time'],'cache_age':live['cache_age'],'final_action':dec['action'],'stage':dec['stage'],'master_bias':dec['bias'],'confidence':dec['confidence'],'grade':dec['grade'],'risk_level':dec['risk_level'],'probabilities':dec['probabilities'],'conflict_interpretation':dec['conflict_interpretation'],'warning':warning,'master_engine':master,'execution_engine':execution,'confirmation_engine':confirm,'plan':plan,'timer_seconds':timer,'indicators':{'trend':ind['trend'],'rsi':ind['rsi'],'momentum':round(ind['momentum'],6),'pressure':round(ind['pressure'],3),'atr':rp(symbol,ind['atr']),'rejection':ind['rejection'],'displacement':ind['displacement']},'profile':{'poc':rp(symbol,ind['profile']['poc']),'val':rp(symbol,ind['profile']['val']),'vah':rp(symbol,ind['profile']['vah'])},'news':nw,'session':ses,'alerts':alerts,'features':features,'logic_note':'V10 uses Finnhub data + Master Bias + Execution Trigger + Confirmation/Risk + ML-ready logging.'}
