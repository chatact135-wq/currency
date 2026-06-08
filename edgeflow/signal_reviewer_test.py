from __future__ import annotations
from datetime import datetime, timezone, timedelta
import pandas as pd
from .signal_db_test import list_signals, save_review
from .data_provider import fetch_twelvedata_candles, fallback_demo_data

HORIZONS = {"15m": 15, "1h": 60, "4h": 240}

def _parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def _classify(signal, future):
    command=(signal.get("command") or "").upper()
    direction=(signal.get("direction") or "").upper()
    entry=signal.get("entry") or signal.get("price")
    stop=signal.get("stop")
    target=signal.get("target")
    if future.empty or entry is None:
        return {"outcome":"NO DATA","notes":"No future candles available yet."}
    entry=float(entry)
    price_after=float(future["close"].iloc[-1])
    high=float(future["high"].max())
    low=float(future["low"].min())
    if direction=="BUY":
        max_fav=(high-entry)/0.00001
        max_adv=(entry-low)/0.00001
        tp_hit=bool(target is not None and high>=float(target))
        sl_hit=bool(stop is not None and low<=float(stop))
        final_dir=(price_after-entry)/0.00001
    elif direction=="SELL":
        max_fav=(entry-low)/0.00001
        max_adv=(high-entry)/0.00001
        tp_hit=bool(target is not None and low<=float(target))
        sl_hit=bool(stop is not None and high>=float(stop))
        final_dir=(entry-price_after)/0.00001
    else:
        max_fav=max_adv=None; tp_hit=sl_hit=False; final_dir=0

    if "SCALP NOW" in command or "TRADE NOW" in command:
        if tp_hit and not sl_hit:
            outcome="TP HIT"; notes="Target was reached."
        elif sl_hit and not tp_hit:
            outcome="SL HIT"; notes="Stop was hit."
        elif tp_hit and sl_hit:
            outcome="AMBIGUOUS"; notes="Both TP and SL touched; tick data needed."
        elif final_dir>=10:
            outcome="GOOD DIRECTION"; notes="Moved in correct direction but did not hit target."
        elif final_dir<=-10:
            outcome="WRONG DIRECTION"; notes="Moved against signal."
        else:
            outcome="FLAT / NO FOLLOW THROUGH"; notes="No meaningful movement."
    elif "NO TRADE" in command or "PLAN ONLY" in command or "MISSED" in command:
        if direction=="BUY" and max_fav is not None and max_fav>=30:
            outcome="MISSED BUY MOVE"; notes="No entry, but price moved up strongly."
        elif direction=="SELL" and max_fav is not None and max_fav>=30:
            outcome="MISSED SELL MOVE"; notes="No entry, but price moved down strongly."
        else:
            outcome="GOOD BLOCK / NO CLEAR MOVE"; notes="No major missed move detected."
    else:
        outcome="UNCLASSIFIED"; notes="Command not classified."

    return {
        "price_after": round(price_after,5),
        "max_favorable_moves": round(max_fav,1) if max_fav is not None else None,
        "max_adverse_moves": round(max_adv,1) if max_adv is not None else None,
        "tp_hit": tp_hit,
        "sl_hit": sl_hit,
        "outcome": outcome,
        "notes": notes
    }

async def review_due_signals():
    reviewed=[]
    signals=list_signals(limit=500)
    now=datetime.now(timezone.utc)
    data_by_symbol={}
    for s in signals:
        sym=s["symbol"]
        if sym not in data_by_symbol:
            try:
                data_by_symbol[sym]=await fetch_twelvedata_candles(sym,"1min",500)
            except Exception:
                data_by_symbol[sym]=fallback_demo_data(sym)
    for s in signals:
        created=_parse_time(s["created_at"])
        age_min=(now-created).total_seconds()/60
        df=data_by_symbol.get(s["symbol"])
        if df is None or df.empty:
            continue
        df=df.copy()
        times=pd.to_datetime(df["time"], errors="coerce")
        try:
            if times.dt.tz is None:
                times=times.dt.tz_localize("UTC")
        except Exception:
            pass
        df["time2"]=times
        for label, mins in HORIZONS.items():
            if age_min < mins:
                continue
            end_time=created+timedelta(minutes=mins)
            future=df[(df["time2"]>created)&(df["time2"]<=end_time)]
            review=_classify(s,future)
            save_review(int(s["id"]), label, review)
            reviewed.append({"signal_id":s["id"],"horizon":label,"outcome":review.get("outcome")})
    return {"reviewed_count":len(reviewed),"reviewed":reviewed[:100]}
