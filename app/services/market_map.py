
from app.services.market import ASSETS, normalize

def rp(sym, v):
    pip=ASSETS[sym]["pip"]
    if pip>=0.1: return round(float(v),2)
    if pip>=0.01: return round(float(v),3)
    return round(float(v),5)

def pips(sym,a,b):
    return round(abs(float(a)-float(b))/ASSETS[sym]["pip"],1)

def levels(c, n=24):
    d=c[-n:] if len(c)>=n else c
    highs=[x["high"] for x in d]; lows=[x["low"] for x in d]
    return {"prev_high":max(highs[:-1]) if len(highs)>1 else max(highs),
            "prev_low":min(lows[:-1]) if len(lows)>1 else min(lows),
            "high":max(highs),"low":min(lows),"mid":(max(highs)+min(lows))/2}

def speed(c,n=6):
    d=c[-n:] if len(c)>=n else c
    if len(d)<2: return {"direction":"SIDEWAYS","strength":0}
    net=d[-1]["close"]-d[0]["close"]
    avg=sum(abs(x["high"]-x["low"]) for x in d)/len(d)
    if avg<=0: return {"direction":"SIDEWAYS","strength":0}
    if abs(net)<avg*0.35: return {"direction":"SIDEWAYS","strength":round(abs(net)/avg*100,1)}
    return {"direction":"UP" if net>0 else "DOWN","strength":round(abs(net)/avg*100,1)}

def dist(sym, atr):
    pip=ASSETS[sym]["pip"]
    if pip==0.0001:
        return {"ag":2*pip,"safe":5*pip,"sl":max(6*pip,atr*.35),"tp1":max(5*pip,atr*.30),"tp2":max(9*pip,atr*.55),"full":max(13*pip,atr*.80)}
    if pip>=0.1:
        return {"ag":0.8,"safe":2.0,"sl":max(2.5,atr*.35),"tp1":max(2.0,atr*.30),"tp2":max(4.0,atr*.55),"full":max(6.0,atr*.80)}
    return {"ag":0.03,"safe":0.08,"sl":max(.10,atr*.35),"tp1":max(.08,atr*.30),"tp2":max(.14,atr*.55),"full":max(.20,atr*.80)}

def infer_bias(res):
    txt=(str(res.get("final_action",""))+" "+str((res.get("final_decision") or {}).get("final_action",""))+" "+str(res.get("master_bias",""))).upper()
    if "BUY" in txt and "SELL" not in txt: return "BUY"
    if "SELL" in txt and "BUY" not in txt: return "SELL"
    pr=res.get("probabilities") or {}
    up=float(pr.get("up") or 0); down=float(pr.get("down") or 0)
    if up-down>=15: return "BUY"
    if down-up>=15: return "SELL"
    return "NEUTRAL"

def build_market_map(sym,c,ind,res):
    sym=normalize(sym); price=float(ind["price"]); atr=float(ind["atr"])
    lv=levels(c); sp=speed(c); d=dist(sym,atr); bias=infer_bias(res)
    buy_switch=max(price+d["ag"], lv["prev_high"]+d["ag"]*.25)
    sell_switch=min(price-d["ag"], lv["prev_low"]-d["ag"]*.25)
    buy_ag=buy_switch; buy_safe=max(price+d["safe"], lv["prev_high"]+d["ag"])
    sell_ag=sell_switch; sell_safe=min(price-d["safe"], lv["prev_low"]-d["ag"])
    if bias=="BUY":
        ag,safe=buy_ag,buy_safe; sl=price-d["sl"]; tp1=price+d["tp1"]; tp2=price+d["tp2"]; full=price+d["full"]; cancel=sell_switch
        cmd=f"BUY BIAS - aggressive above {rp(sym,ag)}, safe above {rp(sym,safe)}"
        flip=f"Flip to SELL watch if price breaks below {rp(sym,sell_switch)}"
        rule="Buy only after buy switch breakout or pullback bullish reaction."
    elif bias=="SELL":
        ag,safe=sell_ag,sell_safe; sl=price+d["sl"]; tp1=price-d["tp1"]; tp2=price-d["tp2"]; full=price-d["full"]; cancel=buy_switch
        cmd=f"SELL BIAS - aggressive below {rp(sym,ag)}, safe below {rp(sym,safe)}"
        flip=f"Flip to BUY watch if price breaks above {rp(sym,buy_switch)}"
        rule="Sell only after sell switch breakdown or pullback bearish rejection."
    else:
        ag=safe=sl=tp1=tp2=full=cancel=None
        cmd="WAIT - trade only if buy or sell switch breaks"
        flip="No side yet. Watch both switch levels."
        rule="No prediction trade; wait for switch."
    return {
        "current_state":{"price":rp(sym,price),"bias":bias,"speed_direction":sp["direction"],"speed_strength":sp["strength"]},
        "switch_levels":{"buy_switch":rp(sym,buy_switch),"sell_switch":rp(sym,sell_switch),"buy_distance_pips":pips(sym,price,buy_switch),"sell_distance_pips":pips(sym,price,sell_switch),"flip_rule":flip},
        "trade_map":{"command":cmd,"open_rule":rule,"aggressive_entry":rp(sym,ag) if ag is not None else None,"safe_entry":rp(sym,safe) if safe is not None else None,"stop_loss":rp(sym,sl) if sl is not None else None,"tp1_partial_close":rp(sym,tp1) if tp1 is not None else None,"tp2":rp(sym,tp2) if tp2 is not None else None,"full_close":rp(sym,full) if full is not None else None,"cancel_level":rp(sym,cancel) if cancel is not None else None,"risk_note":"Aggressive is faster/riskier. Safe waits for more confirmation."},
        "pip_plan":{"stop_pips":pips(sym,price,sl) if sl is not None else None,"tp1_pips":pips(sym,price,tp1) if tp1 is not None else None,"tp2_pips":pips(sym,price,tp2) if tp2 is not None else None,"full_close_pips":pips(sym,price,full) if full is not None else None}
    }
