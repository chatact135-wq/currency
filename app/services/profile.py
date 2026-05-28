import numpy as np

def frequency_volume_profile(candles, bins=24):
    recent=candles[-120:] if len(candles)>=120 else candles
    prices=[]; weights=[]
    for c in recent:
        typical=(c['high']+c['low']+c['close'])/3
        # Forex often lacks real volume; weight by provided volume if real, otherwise candle activity.
        activity=max(c['high']-c['low'], abs(c['close']-c['open']), 0.0000001)
        w=float(c.get('volume') or 1.0)*activity
        prices.append(typical); weights.append(w)
    lo,hi=min(prices),max(prices)
    if hi<=lo: hi=lo+0.0001
    hist,edges=np.histogram(prices,bins=bins,range=(lo,hi),weights=weights)
    idx=int(np.argmax(hist)); poc=(edges[idx]+edges[idx+1])/2
    total=hist.sum(); order=np.argsort(hist)[::-1]
    acc=0; selected=[]
    for i in order:
        selected.append(i); acc+=hist[i]
        if total and acc/total>=0.70: break
    val=min(edges[i] for i in selected); vah=max(edges[i+1] for i in selected)
    price=prices[-1]
    if price>vah:
        direction='sell'; score=-14; msg='Price is above value area high; rejection/sell risk from premium zone.'
    elif price<val:
        direction='buy'; score=14; msg='Price is below value area low; bounce/buy risk from discount zone.'
    elif abs(price-poc)/(hi-lo) < 0.08:
        direction='neutral'; score=0; msg='Price is near POC; avoid chasing inside high-frequency balance area.'
    else:
        direction='neutral'; score=0; msg='Price is inside value area; wait for reaction or breakout.'
    return {'name':'Frequency Volume Profile','triggered':direction!='neutral','direction':direction,'score':score,'poc':poc,'vah':vah,'val':val,'message':msg,'note':'Uses real volume when available; otherwise price-frequency/activity proxy.'}
