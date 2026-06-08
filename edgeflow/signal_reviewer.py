from __future__ import annotations
from datetime import datetime, timezone, timedelta
import pandas as pd
from .signal_db import list_signals, save_review, list_price_snapshots
from .data_provider import fetch_twelvedata_candles, fallback_demo_data
HORIZONS={"15m":15,"1h":60,"4h":240}
def _parse_time(s):
    dt=datetime.fromisoformat(str(s).replace('Z','+00:00'))
    if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
def _classify(signal, rows):
    cmd=(signal.get('command') or '').upper(); direction=(signal.get('direction') or '').upper()
    entry=signal.get('entry') or signal.get('price'); stop=signal.get('stop'); target=signal.get('target')
    vals=[float(r['price']) for r in rows if r.get('price') is not None]
    if not vals or entry is None: return {'outcome':'NO DATA','notes':'No future price snapshots/candles available yet.'}
    entry=float(entry); price_after=vals[-1]; high=max(vals); low=min(vals)
    if direction=='BUY':
        fav=(high-entry)/0.00001; adv=(entry-low)/0.00001; tp=bool(target is not None and high>=float(target)); sl=bool(stop is not None and low<=float(stop)); final=(price_after-entry)/0.00001
    elif direction=='SELL':
        fav=(entry-low)/0.00001; adv=(high-entry)/0.00001; tp=bool(target is not None and low<=float(target)); sl=bool(stop is not None and high>=float(stop)); final=(entry-price_after)/0.00001
    else:
        fav=adv=None; tp=sl=False; final=0
    if 'SCALP NOW' in cmd or 'TRADE NOW' in cmd:
        if tp and not sl: outcome,notes='TP HIT','Target was reached.'
        elif sl and not tp: outcome,notes='SL HIT','Stop was hit.'
        elif tp and sl: outcome,notes='AMBIGUOUS','Both TP and SL touched; tick data needed.'
        elif final>=10: outcome,notes='GOOD DIRECTION','Moved in correct direction but did not hit target.'
        elif final<=-10: outcome,notes='WRONG DIRECTION','Moved against signal.'
        else: outcome,notes='FLAT / NO FOLLOW THROUGH','No meaningful movement.'
    elif 'NO TRADE' in cmd or 'PLAN ONLY' in cmd or 'MISSED' in cmd:
        if direction=='BUY' and fav is not None and fav>=30: outcome,notes='MISSED BUY MOVE','No entry, but price moved up strongly.'
        elif direction=='SELL' and fav is not None and fav>=30: outcome,notes='MISSED SELL MOVE','No entry, but price moved down strongly.'
        else: outcome,notes='GOOD BLOCK / NO CLEAR MOVE','No major missed move detected.'
    else: outcome,notes='UNCLASSIFIED','Command not classified.'
    return {'price_after':round(price_after,5),'max_favorable_moves':round(fav,1) if fav is not None else None,'max_adverse_moves':round(adv,1) if adv is not None else None,'tp_hit':tp,'sl_hit':sl,'outcome':outcome,'notes':notes}
async def review_due_signals():
    reviewed=[]; signals=list_signals(limit=700); now=datetime.now(timezone.utc); candles={}
    for s in signals:
        created=_parse_time(s['created_at']); age=(now-created).total_seconds()/60; sym=s['symbol']
        for label,mins in HORIZONS.items():
            if age<mins: continue
            end=created+timedelta(minutes=mins)
            rows=list_price_snapshots(symbol=sym,start_time=created.isoformat(),end_time=end.isoformat(),limit=2000)
            review=_classify(s, rows)
            if review.get('outcome')=='NO DATA':
                if sym not in candles:
                    try: candles[sym]=await fetch_twelvedata_candles(sym,'1min',500)
                    except Exception: candles[sym]=fallback_demo_data(sym)
                df=candles.get(sym)
                if df is not None and not df.empty:
                    dfx=df.copy(); times=pd.to_datetime(dfx['time'], errors='coerce')
                    try:
                        if times.dt.tz is None: times=times.dt.tz_localize('UTC')
                    except Exception: pass
                    dfx['time2']=times
                    fut=dfx[(dfx['time2']>created)&(dfx['time2']<=end)]
                    rows2=[{'price':float(r.close)} for r in fut.itertuples()]
                    r2=_classify(s, rows2)
                    if r2.get('outcome')!='NO DATA': r2['notes']=str(r2.get('notes',''))+' Used candle fallback.'; review=r2
            save_review(int(s['id']),label,review); reviewed.append({'signal_id':s['id'],'horizon':label,'outcome':review.get('outcome')})
    return {'reviewed_count':len(reviewed),'reviewed':reviewed[:100]}
