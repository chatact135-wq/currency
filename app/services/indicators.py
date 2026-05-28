import pandas as pd, numpy as np
def arr(c,k): return pd.Series([float(x[k]) for x in c],dtype='float64')
def ema(c,n): return float(arr(c,'close').ewm(span=n,adjust=False).mean().iloc[-1])
def rsi(c,n=14):
    close=arr(c,'close'); d=close.diff(); gain=d.clip(lower=0).rolling(n).mean(); loss=(-d.clip(upper=0)).rolling(n).mean(); rs=gain/loss.replace(0,0.000001); v=100-(100/(1+rs)); last=v.iloc[-1]; return float(50 if pd.isna(last) else round(last,2))
def atr(c,n=14):
    h,l,cl=arr(c,'high'),arr(c,'low'),arr(c,'close'); pc=cl.shift(1); tr=pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1); v=tr.rolling(n).mean().iloc[-1]; return float(tr.mean() if pd.isna(v) else v)
def momentum(c,n=6): return (c[-1]['close']-c[-n]['close'])/c[-n]['close'] if len(c)>n else 0.0
def pressure(c,n=5):
    r=c[-n:]; bull=sum(max(0,x['close']-x['open']) for x in r); bear=sum(max(0,x['open']-x['close']) for x in r); tot=bull+bear; return 0.0 if tot==0 else (bull-bear)/tot
def base(c):
    e9,e20,e50=ema(c,9),ema(c,20),ema(c,50); trend='bullish' if e9>e20>e50 else 'bearish' if e9<e20<e50 else 'mixed'
    recent=c[-96:]; highs=[x['high'] for x in recent]; lows=[x['low'] for x in recent]; closes=[x['close'] for x in recent]
    return {'price':c[-1]['close'],'ema9':e9,'ema20':e20,'ema50':e50,'rsi':rsi(c),'atr':atr(c),'momentum':momentum(c),'pressure':pressure(c),'trend':trend,'range_high':max(highs),'range_low':min(lows),'resistance_soft':float(np.quantile(highs,.82)),'support_soft':float(np.quantile(lows,.18)),'midpoint':float(np.median(closes)),'prev_high':max(x['high'] for x in recent[:-3]),'prev_low':min(x['low'] for x in recent[:-3])}
