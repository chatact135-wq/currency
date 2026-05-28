from app.services.market_data import get_live_candles, normalize_asset, SUPPORTED_ASSETS, LiveMarketDataError
from app.services.indicators import build_indicators
from app.services.news_engine import get_news_sentiment
from app.services.session_engine import get_market_session
def _round_price(symbol,value):
    pip=SUPPORTED_ASSETS.get(symbol,SUPPORTED_ASSETS['EURUSD'])['pip']
    if pip>=0.1: return round(float(value),2)
    if pip>=0.01: return round(float(value),3)
    return round(float(value),5)
def _zone_width(symbol,atr_value):
    pip=SUPPORTED_ASSETS.get(symbol,SUPPORTED_ASSETS['EURUSD'])['pip']; return max(float(atr_value)*0.35,pip*12)
def _action_from_score(score):
    if score>=0.72: return 'STRONG BUY'
    if score>=0.42: return 'BUY'
    if score>=0.18: return 'SCALP BUY'
    if score<=-0.72: return 'STRONG SELL'
    if score<=-0.42: return 'SELL'
    if score<=-0.18: return 'SCALP SELL'
    return 'WAIT'
def generate_live_signal(asset):
    symbol=normalize_asset(asset)
    try: live=get_live_candles(symbol)
    except LiveMarketDataError as exc:
        return {'asset':symbol,'display_name':SUPPORTED_ASSETS.get(symbol,{}).get('display',symbol),'status':'error','error':str(exc),'message':'LIVE DATA ERROR — no fake/demo price shown.'}
    candles=live['candles']; ind=build_indicators(candles); news=get_news_sentiment(symbol); session=get_market_session()
    price=ind['current_price']; atr=max(ind['atr'],SUPPORTED_ASSETS[symbol]['pip']*20); width=_zone_width(symbol,atr)
    support,support_soft,resistance,resistance_soft=ind['support'],ind['support_soft'],ind['resistance'],ind['resistance_soft']
    buy_low,buy_high=min(support,support_soft+width),max(support,support_soft+width)
    sell_low,sell_high=min(resistance_soft-width,resistance),max(resistance_soft-width,resistance)
    score=0.0; reasons=[]
    near_support=price<=buy_high; near_resistance=price>=sell_low
    breakout_up=price>resistance_soft and ind['trend'] in ['bullish','strong bullish']
    breakout_down=price<support_soft and ind['trend'] in ['bearish','strong bearish']
    if near_support: score+=0.30; reasons.append('Price is inside/near smart buy zone.')
    if near_resistance: score-=0.30; reasons.append('Price is inside/near smart sell zone.')
    if breakout_up: score+=0.24; reasons.append('Bullish breakout pressure above soft resistance.')
    if breakout_down: score-=0.24; reasons.append('Bearish breakout pressure below soft support.')
    if ind['rsi']<=32: score+=0.18; reasons.append('RSI is oversold; bounce probability improves.')
    elif ind['rsi']>=68: score-=0.18; reasons.append('RSI is overbought; pullback probability improves.')
    else: reasons.append('RSI is neutral; price zone and trend are more important.')
    if ind['trend']=='strong bullish': score+=0.22; reasons.append('EMA structure is strongly bullish.')
    elif ind['trend']=='bullish': score+=0.12; reasons.append('EMA structure is bullish.')
    elif ind['trend']=='strong bearish': score-=0.22; reasons.append('EMA structure is strongly bearish.')
    elif ind['trend']=='bearish': score-=0.12; reasons.append('EMA structure is bearish.')
    else: reasons.append('EMA structure is mixed.')
    score+=news['score']; reasons.append((f"Live news bias is {news['bias']}: " if news['connected'] else '')+news['explanation'])
    score+=session['score']; reasons.append(session['message'])
    if ind['volatility_pct']>0.35: score*=0.82; risk='High'; reasons.append('Volatility is high; confidence reduced.')
    elif ind['volatility_pct']>0.18: risk='Medium'
    else: risk='Low'
    action=_action_from_score(score); confidence=min(94,max(52,52+abs(score)*55))
    if 'BUY' in action:
        entry_low,entry_high=buy_low,max(buy_high,price); sl=buy_low-atr*0.85; tp1=ind['midpoint']; tp2=sell_low; warning='Avoid SELL here unless price breaks below support. Buy setup is stronger.'; expected='Possible bounce/continuation within 30–90 minutes if support/trend holds.'
    elif 'SELL' in action:
        entry_low,entry_high=min(sell_low,price),sell_high; sl=sell_high+atr*0.85; tp1=ind['midpoint']; tp2=buy_high; warning='Avoid BUY here unless price breaks above resistance. Sell setup is stronger.'; expected='Possible pullback/drop within 30–90 minutes if resistance/trend holds.'
    else:
        entry_low,entry_high=buy_high,sell_low; sl=price-atr; tp1=price+atr; tp2=price+atr*1.8; warning='No clean trade. Wait for buy zone, sell zone, or confirmed breakout.'; expected='Wait for confirmation. Best decision may be no trade now.'
    return {'asset':symbol,'display_name':SUPPORTED_ASSETS[symbol]['display'],'status':'live','current_price':_round_price(symbol,price),'source':live['source'],'source_time':live['source_time'],'cache_age_seconds':live['cache_age_seconds'],'action':action,'confidence':round(confidence,1),'score':round(score,3),'risk_level':risk,'trend':ind['trend'],'rsi':ind['rsi'],'ema9':_round_price(symbol,ind['ema9']),'ema20':_round_price(symbol,ind['ema20']),'ema50':_round_price(symbol,ind['ema50']),'atr':_round_price(symbol,atr),'range_high':_round_price(symbol,ind['range_high']),'range_low':_round_price(symbol,ind['range_low']),'support':_round_price(symbol,support),'resistance':_round_price(symbol,resistance),'buy_zone':{'low':_round_price(symbol,buy_low),'high':_round_price(symbol,buy_high)},'sell_zone':{'low':_round_price(symbol,sell_low),'high':_round_price(symbol,sell_high)},'do_not_buy_above':_round_price(symbol,sell_low),'do_not_sell_below':_round_price(symbol,buy_high),'entry_zone':{'low':_round_price(symbol,entry_low),'high':_round_price(symbol,entry_high)},'stop_loss':_round_price(symbol,sl),'take_profit_1':_round_price(symbol,tp1),'take_profit_2':_round_price(symbol,tp2),'expected_move_time':expected,'warning':warning,'reasons':reasons[:9],'news':news,'market_session':session}
