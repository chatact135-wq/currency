def alert(stage,model,direction,score,message): return {'stage':stage,'model':model,'direction':direction,'score':score,'message':message}
def bias(score): return 'BUY' if score>0 else 'SELL' if score<0 else 'NEUTRAL'
def setup_engine(c,ind):
    alerts=[]; buy=0; sell=0; last=c[-1]
    if last['low']<ind['prev_low'] and last['close']>ind['prev_low']: buy+=26; alerts.append(alert('SETUP','SB Liquidity','BUY',26,'Bullish sweep below previous low: buy setup zone.'))
    if last['high']>ind['prev_high'] and last['close']<ind['prev_high']: sell+=26; alerts.append(alert('SETUP','SB Liquidity','SELL',-26,'Bearish sweep above previous high: sell setup zone.'))
    recent=c[-15:-1]; hi=max(x['high'] for x in recent); lo=min(x['low'] for x in recent)
    if last['close']>hi: buy+=22; alerts.append(alert('SETUP','SMC Structure','BUY',22,'Bullish BOS/CHOCH setup.'))
    if last['close']<lo: sell+=22; alerts.append(alert('SETUP','SMC Structure','SELL',-22,'Bearish BOS/CHOCH setup.'))
    a,_,cc=c[-3],c[-2],c[-1]
    if cc['low']>a['high']: buy+=14; alerts.append(alert('SETUP','SMC FVG','BUY',14,'Bullish FVG setup zone.'))
    if cc['high']<a['low']: sell+=14; alerts.append(alert('SETUP','SMC FVG','SELL',-14,'Bearish FVG setup zone.'))
    prof=ind['profile']; price=ind['price']
    if price>prof['vah']: buy+=10; alerts.append(alert('SETUP','Frequency Profile','BUY',10,'Price accepted above VAH.'))
    elif price<prof['val']: sell+=10; alerts.append(alert('SETUP','Frequency Profile','SELL',-10,'Price accepted below VAL.'))
    elif abs(price-prof['poc'])<=ind['atr']*0.25: alerts.append(alert('SETUP','Frequency Profile','NEUTRAL',0,'Price near POC/balance zone.'))
    if ind['trend']=='bullish': buy+=6; alerts.append(alert('SETUP','Trend','BUY',6,'EMA trend supports buy bias.'))
    if ind['trend']=='bearish': sell+=6; alerts.append(alert('SETUP','Trend','SELL',-6,'EMA trend supports sell bias.'))
    net=buy-sell; return {'bias':bias(net),'score':net,'buy_score':buy,'sell_score':sell,'alerts':alerts}
def trigger_engine(c,ind,setup_bias):
    alerts=[]; buy=0; sell=0; rej=ind['rejection']; disp=ind['displacement']
    if rej['direction']=='buy': buy+=12; alerts.append(alert('TRIGGER','Reaction Wick','BUY',12,'Bullish rejection wick confirmed.'))
    elif rej['direction']=='sell': sell+=12; alerts.append(alert('TRIGGER','Reaction Wick','SELL',-12,'Bearish rejection wick confirmed.'))
    if disp['direction']=='buy': buy+=14; alerts.append(alert('TRIGGER','Displacement','BUY',14,'Bullish displacement candle.'))
    elif disp['direction']=='sell': sell+=14; alerts.append(alert('TRIGGER','Displacement','SELL',-14,'Bearish displacement candle.'))
    if ind['pressure']>0.25: buy+=10; alerts.append(alert('TRIGGER','RAVEN Pressure','BUY',10,'RAVEN bullish candle pressure.'))
    elif ind['pressure']<-0.25: sell+=10; alerts.append(alert('TRIGGER','RAVEN Pressure','SELL',-10,'RAVEN bearish candle pressure.'))
    if ind['momentum']>0.00025: buy+=12; alerts.append(alert('TRIGGER','RAVEN Momentum','BUY',12,'RAVEN bullish acceleration.'))
    elif ind['momentum']<-0.00025: sell+=12; alerts.append(alert('TRIGGER','RAVEN Momentum','SELL',-12,'RAVEN bearish acceleration.'))
    recent=c[-8:-1]; hi=max(x['high'] for x in recent); lo=min(x['low'] for x in recent); last=c[-1]
    if last['close']>hi: buy+=10; alerts.append(alert('TRIGGER','Micro BOS','BUY',10,'Micro BOS up.'))
    elif last['close']<lo: sell+=10; alerts.append(alert('TRIGGER','Micro BOS','SELL',-10,'Micro BOS down.'))
    net=buy-sell; return {'bias':bias(net),'score':net,'buy_score':buy,'sell_score':sell,'alerts':alerts}
def confirmation_engine(ind,news,session):
    alerts=[]; mod=0
    if ind['rsi']<=32: mod+=5; alerts.append(alert('CONFIRMATION','RSI','BUY',5,'RSI oversold supports buy reaction.'))
    elif ind['rsi']>=68: mod-=5; alerts.append(alert('CONFIRMATION','RSI','SELL',-5,'RSI overbought supports sell reaction.'))
    if news.get('score',0)>0: mod+=min(8,abs(news['score'])); alerts.append(alert('CONFIRMATION','News','BUY',min(8,abs(news['score'])),'News bullish.'))
    elif news.get('score',0)<0: mod-=min(8,abs(news['score'])); alerts.append(alert('CONFIRMATION','News','SELL',-min(8,abs(news['score'])),'News bearish.'))
    if session['score']!=0: mod+=session['score']; alerts.append(alert('CONFIRMATION','Session','NEUTRAL',session['score'],f"Session: {session['name']}"))
    return {'modifier':mod,'alerts':alerts}
