def liquidity_sweep(c,ind):
    last=c[-1]
    bull=last['low']<ind['prev_low'] and last['close']>ind['prev_low']
    bear=last['high']>ind['prev_high'] and last['close']<ind['prev_high']
    if bull: return {'dir':'bullish','score':26,'reason':'Bullish liquidity sweep below previous low.'}
    if bear: return {'dir':'bearish','score':-26,'reason':'Bearish liquidity sweep above previous high.'}
    return {'dir':'none','score':0,'reason':'No liquidity sweep.'}
def fvg(c):
    if len(c)<5: return {'dir':'none','score':0,'zone':None,'reason':'Not enough candles for FVG.'}
    a,b,x=c[-3],c[-2],c[-1]
    if x['low']>a['high']: return {'dir':'bullish','score':18,'zone':{'low':a['high'],'high':x['low']},'reason':'Bullish FVG detected.'}
    if x['high']<a['low']: return {'dir':'bearish','score':-18,'zone':{'low':x['high'],'high':a['low']},'reason':'Bearish FVG detected.'}
    return {'dir':'none','score':0,'zone':None,'reason':'No FVG.'}
def structure(c,ind):
    last=c[-1]; r=c[-12:]; rh=max(x['high'] for x in r[:-1]); rl=min(x['low'] for x in r[:-1])
    if last['close']>rh: return {'dir':'bullish','score':22,'reason':'Bullish BOS/CHOCH confirmation.'}
    if last['close']<rl: return {'dir':'bearish','score':-22,'reason':'Bearish BOS/CHOCH confirmation.'}
    return {'dir':'none','score':0,'reason':'No BOS/CHOCH confirmation.'}
def order_block(c,direction):
    r=c[-14:]
    if direction=='buy': pool=[x for x in r if x['close']<x['open']]
    elif direction=='sell': pool=[x for x in r if x['close']>x['open']]
    else: pool=[]
    base=pool[-1] if pool else r[-2]
    return {'low':min(base['open'],base['close'],base['low']),'high':max(base['open'],base['close'],base['high'])}
def analyze(c,ind):
    l=liquidity_sweep(c,ind); g=fvg(c); st=structure(c,ind); total=l['score']+g['score']+st['score']
    return {'score':total,'liquidity_sweep':l,'fvg':g,'structure':st,'reasons':[l['reason'],g['reason'],st['reason']]}
