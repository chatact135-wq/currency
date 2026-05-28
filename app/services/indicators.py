import pandas as pd, numpy as np
def s(c,k): return pd.Series([float(x[k]) for x in c],dtype='float64')
def ema(c,span): return float(s(c,'close').ewm(span=span,adjust=False).mean().iloc[-1])
def rsi(c,period=14):
    close=s(c,'close'); d=close.diff(); gain=d.clip(lower=0).rolling(period).mean(); loss=(-d.clip(upper=0)).rolling(period).mean(); rs=gain/loss.replace(0,0.000001); val=100-(100/(1+rs)); last=val.iloc[-1]
    return float(50 if pd.isna(last) else round(last,2))
def atr(c,period=14):
    h,l,cl=s(c,'high'),s(c,'low'),s(c,'close'); pc=cl.shift(1); tr=pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1); val=tr.rolling(period).mean().iloc[-1]
    if pd.isna(val): val=tr.mean()
    return float(val)
def momentum(c,lookback=6): return 0.0 if len(c)<=lookback else (c[-1]['close']-c[-lookback]['close'])/c[-lookback]['close']
def pressure(c,n=5):
    r=c[-n:]; bull=sum(max(0,x['close']-x['open']) for x in r); bear=sum(max(0,x['open']-x['close']) for x in r); total=bull+bear
    return 0.0 if total==0 else (bull-bear)/total
def wick(c):
    last=c[-1]; rng=max(0.0000001,last['high']-last['low']); up=last['high']-max(last['open'],last['close']); lo=min(last['open'],last['close'])-last['low']
    if up/rng>0.42 and last['close']<last['open']: return {'direction':'SELL','strength':round(up/rng,3)}
    if lo/rng>0.42 and last['close']>last['open']: return {'direction':'BUY','strength':round(lo/rng,3)}
    return {'direction':'NEUTRAL','strength':round(max(up,lo)/rng,3)}
def displacement(c):
    last=c[-1]; rng=max(0.0000001,last['high']-last['low']); body=abs(last['close']-last['open']); st=body/rng
    if st<0.58: return {'direction':'NEUTRAL','strength':round(st,3)}
    return {'direction':'BUY' if last['close']>last['open'] else 'SELL','strength':round(st,3)}
def profile(c,bins=18):
    closes=np.array([x['close'] for x in c[-120:]],dtype=float); hist,edges=np.histogram(closes,bins=bins); poc_i=int(hist.argmax()); poc=(edges[poc_i]+edges[poc_i+1])/2; total=hist.sum(); selected=[]; acc=0
    for i in sorted(range(len(hist)),key=lambda j:hist[j],reverse=True):
        selected.append(i); acc+=hist[i]
        if total and acc/total>=0.70: break
    return {'poc':float(poc),'val':float(min(edges[i] for i in selected)),'vah':float(max(edges[i+1] for i in selected))}
def structure(c):
    r=c[-120:]; highs=[x['high'] for x in r]; lows=[x['low'] for x in r]; closes=[x['close'] for x in r]
    return {'range_high':max(highs),'range_low':min(lows),'resistance_soft':float(np.quantile(highs,0.82)),'support_soft':float(np.quantile(lows,0.18)),'midpoint':float(np.median(closes)),'prev_high':max(x['high'] for x in r[:-3]),'prev_low':min(x['low'] for x in r[:-3]),'profile':profile(c)}
def build(c):
    price=c[-1]['close']; e9,e20,e50=ema(c,9),ema(c,20),ema(c,50); trend='bullish' if e9>e20>e50 else 'bearish' if e9<e20<e50 else 'mixed'
    return {'price':price,'ema9':e9,'ema20':e20,'ema50':e50,'trend':trend,'rsi':rsi(c),'atr':atr(c),'momentum':momentum(c),'pressure':pressure(c),'rejection':wick(c),'displacement':displacement(c),**structure(c)}
