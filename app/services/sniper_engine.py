from app.config import settings
from app.services.market_data import get_candles, normalize_asset, SUPPORTED_ASSETS, LiveDataError
from app.services.indicators import build
from app.services.sb_models import analyze, order_block
from app.services.session_engine import session
from app.services.news_engine import news

def rp(sym,val):
    pip=SUPPORTED_ASSETS[sym]['pip']
    if pip>=0.1: return round(float(val),2)
    if pip>=0.01: return round(float(val),3)
    return round(float(val),5)
def pips(sym,d): return abs(float(d))/SUPPORTED_ASSETS[sym]['pip']
def compress_zone(sym,center,atr):
    pip=SUPPORTED_ASSETS[sym]['pip']; half=min(settings.MAX_SCALP_ENTRY_PIPS*pip/2, atr*0.18)
    return center-half, center+half
def decide(score):
    if score>=settings.MIN_SIGNAL_SCORE: return 'SNIPER BUY'
    if score<=-settings.MIN_SIGNAL_SCORE: return 'SNIPER SELL'
    if score>=60: return 'SCALP BUY WATCH'
    if score<=-60: return 'SCALP SELL WATCH'
    return 'NO TRADE'
def signal(asset):
    sym=normalize_asset(asset)
    try: live=get_candles(sym)
    except LiveDataError as e: return {'asset':sym,'display_name':SUPPORTED_ASSETS[sym]['display'],'status':'error','message':'LIVE DATA ERROR — no fake/demo price shown.','error':str(e)}
    c=live['candles']; ind=build(c); sb=analyze(c,ind); ses=session(); nw=news(sym)
    score=0; reasons=[]
    score += sb['score']; reasons += sb['reasons']
    if ind['trend']=='bullish': score+=14; reasons.append('EMA trend bullish.')
    elif ind['trend']=='bearish': score-=14; reasons.append('EMA trend bearish.')
    else: reasons.append('EMA trend mixed.')
    if ind['rsi']<=32: score+=12; reasons.append('RSI oversold supports buy scalp.')
    elif ind['rsi']>=68: score-=12; reasons.append('RSI overbought supports sell scalp.')
    else: reasons.append('RSI neutral.')
    score += ses['score']; reasons.append('Session filter: '+ses['name'])
    score += nw['score']; reasons.append('News bias: '+nw['bias']+' — '+nw['explanation'])
    action=decide(score); price=ind['price']; atr=max(ind['atr'],SUPPORTED_ASSETS[sym]['pip']*15)
    direction='buy' if 'BUY' in action else 'sell' if 'SELL' in action else 'none'
    ob=order_block(c,direction)
    if direction=='buy': center=max(price, min(max(ob['low'], price-atr*0.25), price+atr*0.15))
    elif direction=='sell': center=min(price, max(min(ob['high'], price+atr*0.25), price-atr*0.15))
    else: center=price
    lo,hi=compress_zone(sym,center,atr)
    if direction=='buy':
        sl=lo-atr*0.45; tp1=hi+atr*0.45; tp2=hi+atr*0.85; full=hi+atr*1.15; inval=sl; be='When TP1 hits, close 50% and move SL to breakeven.'; warn='Buy only inside entry interval. Cancel if candle closes below invalidation.'
    elif direction=='sell':
        sl=hi+atr*0.45; tp1=lo-atr*0.45; tp2=lo-atr*0.85; full=lo-atr*1.15; inval=sl; be='When TP1 hits, close 50% and move SL to breakeven.'; warn='Sell only inside entry interval. Cancel if candle closes above invalidation.'
    else:
        sl=price-atr; tp1=price+atr; tp2=price+atr*1.5; full=price+atr*2; inval=sl; be='No active trade management because setup is not confirmed.'; warn='NO TRADE: wait for liquidity sweep + FVG + BOS/CHOCH alignment.'
    risk_pips=pips(sym,hi-lo)
    quality=max(0,min(100,50+abs(score)*0.55-(risk_pips*1.2)))
    if action=='NO TRADE': quality=min(quality,50)
    return {'asset':sym,'display_name':SUPPORTED_ASSETS[sym]['display'],'status':'live','source':live['source'],'source_time':live['source_time'],'cache_age':live['cache_age'],'price':rp(sym,price),'action':action,'quality':round(quality,1),'raw_score':round(score,1),'trade_type':'sniper_scalp' if 'SNIPER' in action or 'SCALP' in action else 'no_trade','plan':{'entry':{'low':rp(sym,lo),'high':rp(sym,hi),'width_pips':round(risk_pips,1)},'stop_loss':rp(sym,sl),'take_profit_1':rp(sym,tp1),'take_profit_2':rp(sym,tp2),'full_close':rp(sym,full),'invalidation':rp(sym,inval),'move_sl_rule':be,'timer_seconds':900 if 'SNIPER' in action else 1800 if 'SCALP' in action else 600},'indicators':{'trend':ind['trend'],'rsi':ind['rsi'],'atr':rp(sym,atr),'range_high':rp(sym,ind['range_high']),'range_low':rp(sym,ind['range_low'])},'sb_model':sb,'session':ses,'news':nw,'warning':warn,'reasons':reasons[:10]}
