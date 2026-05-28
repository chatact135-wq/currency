def smc_model(c,ind):
    last=c[-1]; alerts=[]; score=0; direction='neutral'
    if last['low']<ind['prev_low'] and last['close']>ind['prev_low']:
        score+=18; direction='buy'; alerts.append('SMC bullish liquidity sweep below previous low.')
    if last['high']>ind['prev_high'] and last['close']<ind['prev_high']:
        score-=18; direction='sell'; alerts.append('SMC bearish liquidity sweep above previous high.')
    recent=c[-15:-1]; hi=max(x['high'] for x in recent); lo=min(x['low'] for x in recent)
    if last['close']>hi: score+=14; direction='buy'; alerts.append('SMC bullish BOS/CHOCH close above recent structure.')
    if last['close']<lo: score-=14; direction='sell'; alerts.append('SMC bearish BOS/CHOCH close below recent structure.')
    return {'name':'SMC Model','triggered':bool(alerts),'direction':direction,'score':score,'alerts':alerts or ['No SMC trigger now.']}

def sb_model(c,ind):
    # Silver Bullet style = session momentum + displacement + imbalance.
    a,b,d=c[-3],c[-2],c[-1]; alerts=[]; score=0; direction='neutral'
    bullish_fvg=d['low']>a['high']; bearish_fvg=d['high']<a['low']
    displacement=abs(d['close']-d['open']) > ind['atr']*0.35
    if bullish_fvg and displacement:
        score+=16; direction='buy'; alerts.append('SB bullish displacement + FVG detected.')
    elif bullish_fvg:
        score+=9; direction='buy'; alerts.append('SB bullish FVG detected, displacement weak.')
    if bearish_fvg and displacement:
        score-=16; direction='sell'; alerts.append('SB bearish displacement + FVG detected.')
    elif bearish_fvg:
        score-=9; direction='sell'; alerts.append('SB bearish FVG detected, displacement weak.')
    return {'name':'SB Model','triggered':bool(alerts),'direction':direction,'score':score,'alerts':alerts or ['No SB/FVG trigger now.']}

def raven_model(c,ind,news_score=0):
    # RAVEN composite used here as a practical engine: Rejection, Acceleration, Value/profile, EMA, News.
    score=0; alerts=[]; direction='neutral'
    if ind['pressure']>0.35: score+=10; alerts.append('RAVEN bullish candle pressure.')
    if ind['pressure']<-0.35: score-=10; alerts.append('RAVEN bearish candle pressure.')
    if ind['momentum']>0.00025: score+=10; alerts.append('RAVEN bullish acceleration.')
    if ind['momentum']<-0.00025: score-=10; alerts.append('RAVEN bearish acceleration.')
    if ind['trend']=='bullish': score+=8; alerts.append('RAVEN bullish EMA alignment.')
    if ind['trend']=='bearish': score-=8; alerts.append('RAVEN bearish EMA alignment.')
    if news_score>0: score+=min(8,news_score); alerts.append('RAVEN news supports upside.')
    if news_score<0: score-=min(8,abs(news_score)); alerts.append('RAVEN news supports downside.')
    direction='buy' if score>=12 else 'sell' if score<=-12 else 'neutral'
    return {'name':'RAVEN Composite','triggered':direction!='neutral','direction':direction,'score':score,'alerts':alerts or ['RAVEN neutral; no acceleration alignment.']}
