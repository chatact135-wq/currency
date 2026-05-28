import pandas as pd, numpy as np
def s(c,k): return pd.Series([float(x[k]) for x in c],dtype='float64')
def ema(c,n): return float(round(s(c,'close').ewm(span=n,adjust=False).mean().iloc[-1],5))
def rsi(c,p=14):
    close=s(c,'close'); d=close.diff(); g=d.clip(lower=0).rolling(p).mean(); l=(-d.clip(upper=0)).rolling(p).mean(); rs=g/l.replace(0,0.000001); v=100-(100/(1+rs)); last=v.iloc[-1]; return float(50 if pd.isna(last) else round(last,2))
def atr(c,p=14):
    h,l,cl=s(c,'high'),s(c,'low'),s(c,'close'); pc=cl.shift(1); tr=pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1); val=tr.rolling(p).mean().iloc[-1]; return float(round(tr.mean() if pd.isna(val) else val,5))
def build(c):
    price=float(c[-1]['close']); e9,e20,e50=ema(c,9),ema(c,20),ema(c,50)
    trend='bullish' if e9>e20>e50 else 'bearish' if e9<e20<e50 else 'mixed'
    recent=c[-96:] if len(c)>=96 else c; highs=[x['high'] for x in recent]; lows=[x['low'] for x in recent]; closes=[x['close'] for x in recent]
    return {'price':round(price,5),'ema9':e9,'ema20':e20,'ema50':e50,'rsi':rsi(c),'atr':atr(c),'trend':trend,'range_high':round(max(highs),5),'range_low':round(min(lows),5),'resistance_soft':round(float(np.quantile(highs,0.82)),5),'support_soft':round(float(np.quantile(lows,0.18)),5),'midpoint':round(float(np.median(closes)),5),'prev_high':round(max([x['high'] for x in recent[:-3]]),5),'prev_low':round(min([x['low'] for x in recent[:-3]]),5)}
