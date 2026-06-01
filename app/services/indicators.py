import pandas as pd, numpy as np
def s(c,k): return pd.Series([float(x[k]) for x in c],dtype="float64")
def ema(c,n): return float(s(c,"close").ewm(span=n,adjust=False).mean().iloc[-1])
def rsi(c,n=14):
    close=s(c,"close"); d=close.diff(); gain=d.clip(lower=0).rolling(n).mean(); loss=(-d.clip(upper=0)).rolling(n).mean()
    rs=gain/loss.replace(0,0.000001); v=100-(100/(1+rs)); last=v.iloc[-1]
    return float(50 if pd.isna(last) else round(last,2))
def atr(c,n=14):
    h,l,cl=s(c,"high"),s(c,"low"),s(c,"close"); pc=cl.shift(1)
    tr=pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1); v=tr.rolling(n).mean().iloc[-1]
    if pd.isna(v): v=tr.mean()
    return float(max(v,0.0000001))
def momentum(c,lb=6): return 0.0 if len(c)<=lb else (c[-1]["close"]-c[-lb]["close"])/c[-lb]["close"]
def pressure(c,n=5):
    r=c[-n:]; bull=sum(max(0,x["close"]-x["open"]) for x in r); bear=sum(max(0,x["open"]-x["close"]) for x in r); t=bull+bear
    return 0.0 if t==0 else (bull-bear)/t
def wick(c):
    x=c[-1]; rng=max(0.0000001,x["high"]-x["low"]); upper=x["high"]-max(x["open"],x["close"]); lower=min(x["open"],x["close"])-x["low"]
    if upper/rng>0.42 and x["close"]<x["open"]: return {"direction":"SELL","strength":round(upper/rng,3)}
    if lower/rng>0.42 and x["close"]>x["open"]: return {"direction":"BUY","strength":round(lower/rng,3)}
    return {"direction":"NEUTRAL","strength":round(max(upper,lower)/rng,3)}
def displacement(c):
    x=c[-1]; rng=max(0.0000001,x["high"]-x["low"]); body=abs(x["close"]-x["open"]); st=body/rng
    if st<0.58: return {"direction":"NEUTRAL","strength":round(st,3)}
    return {"direction":"BUY" if x["close"]>x["open"] else "SELL","strength":round(st,3)}
def profile(c,bins=18):
    closes=np.array([x["close"] for x in c[-120:]],dtype=float); hist,edges=np.histogram(closes,bins=bins); poc_i=int(hist.argmax()); poc=(edges[poc_i]+edges[poc_i+1])/2
    sel=[]; acc=0; total=hist.sum()
    for i in sorted(range(len(hist)),key=lambda j:hist[j],reverse=True):
        sel.append(i); acc+=hist[i]
        if total and acc/total>=0.70: break
    return {"poc":float(poc),"val":float(min(edges[i] for i in sel)),"vah":float(max(edges[i+1] for i in sel))}
def build(c):
    e9,e20,e50=ema(c,9),ema(c,20),ema(c,50); trend="bullish" if e9>e20>e50 else "bearish" if e9<e20<e50 else "mixed"
    r=c[-120:] if len(c)>=120 else c; highs=[x["high"] for x in r]; lows=[x["low"] for x in r]; closes=[x["close"] for x in r]
    return {"price":c[-1]["close"],"trend":trend,"rsi":rsi(c),"atr":atr(c),"momentum":momentum(c),"pressure":pressure(c),"rejection":wick(c),"displacement":displacement(c),"resistance_soft":float(np.quantile(highs,0.82)),"support_soft":float(np.quantile(lows,0.18)),"prev_high":max(x["high"] for x in r[:-3]),"prev_low":min(x["low"] for x in r[:-3]),"profile":profile(c)}
