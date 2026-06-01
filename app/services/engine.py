from app.config import settings
from app.services.market import ASSETS, normalize, snapshot, LiveDataError
from app.services.indicators import build
from app.services.core import detect
from app.services.adaptive import get_weights, performance_for_active
from app.services.session import info as session_info
def rp(sym,v):
    pip=ASSETS[sym]["pip"]
    if pip>=0.1: return round(float(v),2)
    if pip>=0.01: return round(float(v),3)
    return round(float(v),5)
def pips(sym,a,b): return round(abs(a-b)/ASSETS[sym]["pip"],1)
def precision_score(m, e, ses, ad):
    aligned = m["bias"] != "NEUTRAL" and m["bias"] == e["bias"]
    base = abs(m["net"]) * 0.70 + abs(e["net"]) * 0.70 + max(0, ses["score"])
    if aligned:
        base += 12
    if ad.get("probability") is not None:
        base = 0.55 * base + 0.45 * ad["probability"]
    edge = ad.get("expected_edge_r")
    if edge is not None:
        base += max(-12, min(14, edge * 10))
    return round(max(0, min(100, base)), 1), aligned

def risk_reward_ok(sym, direction, ind):
    price = ind["price"]
    atr = ind["atr"]
    if direction == "BUY":
        stop = min(ind["support_soft"], price - atr * 0.45)
        target = price + atr * 0.95
        risk = price - stop
        reward = target - price
    elif direction == "SELL":
        stop = max(ind["resistance_soft"], price + atr * 0.45)
        target = price - atr * 0.95
        risk = stop - price
        reward = price - target
    else:
        return {"ok": False, "rr": 0, "risk": 0, "reward": 0}
    rr = reward / risk if risk > 0 else 0
    return {"ok": rr >= 1.25, "rr": round(rr, 2), "risk": risk, "reward": reward}

def decide(m,e,ses,ad,ind,sym):
    aligned = m["bias"]!="NEUTRAL" and m["bias"]==e["bias"]
    precision, _ = precision_score(m,e,ses,ad)
    direction = m["bias"] if m["bias"]!="NEUTRAL" else e["bias"]
    rr = risk_reward_ok(sym, direction, ind)
    risk = "LOW" if aligned and ses["score"]>=0 and rr["ok"] else "MEDIUM" if ses["score"]>=0 else "HIGH"
    learned_ok = ad.get("probability") is None or ad.get("probability",0) >= 55
    edge_ok = ad.get("expected_edge_r") is None or ad.get("expected_edge_r",0) >= 0
    if aligned and precision >= 64 and rr["ok"] and learned_ok and edge_ok and risk != "HIGH":
        action=f"ACTIVE SCALP {direction}"; stage="EXECUTION ACTIVE"; active=True
        reason="Master bias, execution trigger, adaptive edge and reward/risk are acceptable."
    elif direction!="NEUTRAL" and abs(m["net"])>=22 and abs(e["net"])>=14:
        action=f"{direction} PRECISION WATCH"; stage="PRECISION WATCH"; active=False
        reason="Setup exists, but exact trigger or reward/risk is not strong enough yet."
    elif direction!="NEUTRAL" and abs(m["net"])>=22:
        action=f"{direction} SETUP READY"; stage="SETUP READY"; active=False
        reason="Master bias exists, waiting for execution trigger."
    elif e["bias"]!="NEUTRAL" and abs(e["net"])>=20:
        action=f"{e['bias']} TRIGGER WATCH"; stage="TRIGGER WATCH"; active=False; direction=e["bias"]
        reason="Execution trigger exists, but master structure is weak."
    else:
        action="WAIT"; stage="WAIT"; active=False
        reason="No high-quality trigger."
    conf=round(max(35,min(97,precision)),1)
    edge=ad.get("expected_edge_r")
    grade="A+" if active and conf>=88 and risk=="LOW" else "A" if active and conf>=74 else "B" if conf>=62 else "C" if conf>=50 else "D"
    buy=m["buy_score"]+e["buy_score"]; sell=m["sell_score"]+e["sell_score"]; total=buy+sell+25
    up=round((buy/total)*100,1); down=round((sell/total)*100,1); side=round(max(5,100-up-down),1)
    conflict="Aligned: master bias and execution agree." if aligned else "Not aligned: opposite signals are pullback/risk, not automatic reversal."
    return {"action":action,"stage":stage,"active":active,"bias":direction,"confidence":conf,"grade":grade,"risk_level":risk,"probabilities":{"up":up,"sideways":side,"down":down},"conflict_interpretation":conflict,"decision_reason":reason,"rr":rr}

def close_rules(sym, direction, ind, pl):
    if not pl.get("has_exact_entry"):
        return {"close_status":"No active trade","partial_close":"No partial close until ACTIVE SCALP entry.","full_close":"No full close until ACTIVE SCALP entry.","emergency_close":"Cancel setup if opposite BOS/CHOCH appears before entry.","trailing_stop":"Not active."}
    atr = ind["atr"]
    if direction == "BUY":
        emergency = "Close manually if candle closes below support/entry invalidation or opposite SELL structure appears."
        trail = f"After TP1, trail stop by about {rp(sym, atr*0.45)} below recent swing low."
    elif direction == "SELL":
        emergency = "Close manually if candle closes above resistance/entry invalidation or opposite BUY structure appears."
        trail = f"After TP1, trail stop by about {rp(sym, atr*0.45)} above recent swing high."
    else:
        emergency = "No active direction."; trail = "Not active."
    return {"close_status":"Active management","partial_close":f"Close 50% at TP1: {pl.get('tp1_partial_close')}","full_close":f"Full close target: {pl.get('full_close')}","emergency_close":emergency,"trailing_stop":trail}

def plan(sym,d,ind):
    direction=d["bias"]; price=ind["price"]; pip=ASSETS[sym]["pip"]; atr=ind["atr"]
    if not d["active"]:
        if direction=="BUY": setup=f"{rp(sym,min(ind['support_soft'],price))} → {rp(sym,max(ind['support_soft'],price))}"; trigger=ind["resistance_soft"]
        elif direction=="SELL": setup=f"{rp(sym,max(ind['resistance_soft'],price))} → {rp(sym,min(ind['resistance_soft'],price))}"; trigger=ind["support_soft"]
        else: setup="No valid setup zone"; trigger=price
        return {"has_exact_entry":False,"setup_zone":setup,"trigger_level":rp(sym,trigger),"exact_entry":"No exact entry until ACTIVE SCALP confirms.","after_tp1":"No trade management until exact entry is active."}
    if pip==0.0001: width=max(settings.MIN_ENTRY_PIPS*pip,min(settings.MAX_ENTRY_PIPS*pip,atr*0.12))
    elif pip==0.10: width=max(0.8,min(3.5,atr*0.16))
    else: width=max(0.04,min(0.18,atr*0.16))
    if direction=="BUY":
        low=price-width*.25; high=price+width*.75; sl=low-max(width*1.4,atr*.28); tp1=high+max(width*1.1,atr*.32); tp2=high+max(width*2,atr*.58); full=high+max(width*2.8,atr*.78)
        return {"has_exact_entry":True,"direction":"ascending","exact_entry":f"{rp(sym,low)} → {rp(sym,high)}","entry_pips":pips(sym,low,high),"stop_loss":rp(sym,sl),"invalidation":rp(sym,sl),"tp1_partial_close":rp(sym,tp1),"tp2":rp(sym,tp2),"full_close":rp(sym,full),"after_tp1":"Close 50% and move SL to breakeven."}
    high=price+width*.25; low=price-width*.75; sl=high+max(width*1.4,atr*.28); tp1=low-max(width*1.1,atr*.32); tp2=low-max(width*2,atr*.58); full=low-max(width*2.8,atr*.78)
    return {"has_exact_entry":True,"direction":"descending","exact_entry":f"{rp(sym,high)} → {rp(sym,low)}","entry_pips":pips(sym,high,low),"stop_loss":rp(sym,sl),"invalidation":rp(sym,sl),"tp1_partial_close":rp(sym,tp1),"tp2":rp(sym,tp2),"full_close":rp(sym,full),"after_tp1":"Close 50% and move SL to breakeven."}
def signal(db,asset):
    sym=normalize(asset)
    try: snap=snapshot(db,sym)
    except LiveDataError as exc: return {"status":"error","asset":sym,"display":ASSETS[sym]["display"],"message":"LIVE DATA ERROR — no live price shown.","error":str(exc)}
    c=snap["candles"]; ind=build(c); weights=get_weights(db,sym); det=detect(c,ind,weights); alerts=det["alerts"]; active=list({a["strategy"] for a in alerts})
    ad=performance_for_active(db,sym,active); ses=session_info(); d=decide(det["master"],det["execution"],ses,ad,ind,sym); pl=plan(sym,d,ind); cr=close_rules(sym,d["bias"],ind,pl)
    warning=f"{d['action']}: exact entry active." if d["active"] else f"{d['action']}: {d.get('decision_reason','wait for exact trigger')}"
    return {"status":"live","asset":sym,"display":ASSETS[sym]["display"],"price":rp(sym,snap["price"]),"source":snap["source"],"source_time":snap["source_time"],"cache_age":snap["cache_age"],"stored_candles":snap["stored_candles"],"final_action":d["action"],"stage":d["stage"],"master_bias":d["bias"],"confidence":d["confidence"],"grade":d["grade"],"risk_level":d["risk_level"],"probabilities":d["probabilities"],"adaptive":ad,"conflict_interpretation":d["conflict_interpretation"],"warning":warning,"master_engine":det["master"],"execution_engine":det["execution"],"plan":pl,"close_rules":cr,"decision_reason":d.get("decision_reason"),"reward_risk":d.get("rr"),"timer_seconds":600 if d["active"] else 900,"indicators":{"trend":ind["trend"],"rsi":ind["rsi"],"momentum":round(ind["momentum"],6),"pressure":round(ind["pressure"],3),"atr":rp(sym,ind["atr"])},"profile":{"poc":rp(sym,ind["profile"]["poc"]),"val":rp(sym,ind["profile"]["val"]),"vah":rp(sym,ind["profile"]["vah"])},"alerts":alerts,"features":{"active_strategies":active,"setup_score":det["master"]["net"],"trigger_score":det["execution"]["net"]},"logic_note":"V14 uses precision trigger + adaptive weights from historical backtest results when enough data exists."}
