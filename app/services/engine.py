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


def bias_strength(m, e):
    return abs(m["net"]) * 0.70 + abs(e["net"]) * 0.70

def reward_risk_projection(sym, direction, ind):
    price = ind["price"]
    atr = ind["atr"]
    if direction == "BUY":
        stop = min(ind["support_soft"], price - atr * 0.45)
        target = price + atr * 0.95
        risk = max(0.0000001, price - stop)
        reward = max(0, target - price)
    elif direction == "SELL":
        stop = max(ind["resistance_soft"], price + atr * 0.45)
        target = price - atr * 0.95
        risk = max(0.0000001, stop - price)
        reward = max(0, price - target)
    else:
        return {"rr":0,"risk":0,"reward":0,"ok_active":False,"ok_ready":False}
    rr = reward / risk if risk > 0 else 0
    return {"rr":round(rr,2),"risk":risk,"reward":reward,"ok_active":rr>=settings.MIN_ACTIVE_RR,"ok_ready":rr>=settings.MIN_SCALP_READY_RR}

def adaptive_ok_for_ready(ad):
    if ad.get("probability") is None:
        return True
    return ad.get("probability",0) >= 52 and (ad.get("expected_edge_r") is None or ad.get("expected_edge_r",0) >= -0.15)

def adaptive_ok_for_active(ad):
    if ad.get("probability") is None:
        return True
    return ad.get("probability",0) >= 56 and (ad.get("expected_edge_r") is None or ad.get("expected_edge_r",0) >= 0)

def decide(m,e,ses,ad,ind,sym):
    aligned = m["bias"] != "NEUTRAL" and m["bias"] == e["bias"]
    direction = m["bias"] if m["bias"] != "NEUTRAL" else e["bias"]
    exec_strong = abs(e["net"]) >= 32
    master_ok = abs(m["net"]) >= 20
    score = bias_strength(m,e) + max(0, ses["score"])
    if aligned:
        score += 15
    if ad.get("probability") is not None:
        score = 0.60 * score + 0.40 * ad["probability"]
    if ad.get("expected_edge_r") is not None:
        score += max(-10, min(12, ad["expected_edge_r"] * 8))
    score = round(max(0, min(100, score)), 1)
    rr = reward_risk_projection(sym, direction, ind)
    if ses["score"] < 0:
        risk = "HIGH"
    elif aligned and rr["ok_active"]:
        risk = "LOW"
    elif rr["ok_ready"]:
        risk = "MEDIUM"
    else:
        risk = "MEDIUM"
    if aligned and score >= settings.ACTIVE_PRECISION_SCORE and rr["ok_active"] and adaptive_ok_for_active(ad) and risk != "HIGH":
        action=f"ACTIVE SCALP {direction}"; stage="EXECUTION ACTIVE"; active=True; ready=True
        reason="All main models agree, reward/risk is acceptable, and precision score is active."
    elif aligned and score >= settings.SCALP_READY_SCORE and rr["ok_ready"] and adaptive_ok_for_ready(ad) and risk != "HIGH":
        action=f"{direction} SCALP READY"; stage="SCALP READY"; active=False; ready=True
        reason="Models agree and scalp is nearly ready. Wait for pullback reaction or breakout activation."
    elif direction != "NEUTRAL" and exec_strong and not aligned:
        action=f"{direction} COUNTER-TREND SCALP WATCH"; stage="COUNTER-TREND WATCH"; active=False; ready=False
        reason="Execution pressure is strong, but master bias disagrees. Small-risk scalp only if trigger confirms."
    elif direction != "NEUTRAL" and master_ok:
        action=f"{direction} SETUP READY"; stage="SETUP READY"; active=False; ready=False
        reason="Master bias exists, but execution trigger is not strong enough."
    elif e["bias"] != "NEUTRAL" and abs(e["net"]) >= 20:
        direction=e["bias"]; action=f"{direction} TRIGGER WATCH"; stage="TRIGGER WATCH"; active=False; ready=False
        reason="Execution trigger exists, but master structure is weak."
    else:
        action="WAIT"; stage="WAIT"; active=False; ready=False
        reason="No high-quality setup."
    buy=m["buy_score"]+e["buy_score"]; sell=m["sell_score"]+e["sell_score"]; total=buy+sell+25
    up=round((buy/total)*100,1); down=round((sell/total)*100,1); side=round(max(5,100-up-down),1)
    if active and score >= 86 and risk == "LOW": grade="A+"
    elif active or (ready and score >= 70): grade="A"
    elif ready or score >= 58: grade="B"
    elif score >= 48: grade="C"
    else: grade="D"
    conflict = "Aligned: master bias and execution agree." if aligned else "Not aligned: opposite signals are pullback/risk, not automatic reversal."
    return {"action":action,"stage":stage,"active":active,"ready":ready,"bias":direction,"confidence":score,"grade":grade,"risk_level":risk,"probabilities":{"up":up,"sideways":side,"down":down},"conflict_interpretation":conflict,"decision_reason":reason,"rr":rr}

def plan(sym,d,ind):
    direction=d["bias"]; price=ind["price"]; pip=ASSETS[sym]["pip"]; atr=ind["atr"]
    if direction == "BUY":
        pullback=min(price, ind["support_soft"]); breakout=max(price, ind["resistance_soft"])
        setup=f"{rp(sym,pullback)} → {rp(sym,price)}"
        trigger_text=f"Pullback reaction near {rp(sym,pullback)} OR breakout above {rp(sym,breakout)}"
    elif direction == "SELL":
        pullback=max(price, ind["resistance_soft"]); breakdown=min(price, ind["support_soft"])
        setup=f"{rp(sym,pullback)} → {rp(sym,price)}"
        trigger_text=f"Pullback rejection near {rp(sym,pullback)} OR breakdown below {rp(sym,breakdown)}"
    else:
        setup="No valid setup zone"; trigger_text="No trigger"
    if not d["active"]:
        return {"has_exact_entry":False,"setup_zone":setup,"trigger_level":trigger_text,"exact_entry":"No exact entry until ACTIVE SCALP confirms.","after_tp1":"No trade management until exact entry is active.","ready_note":"SCALP READY means direction is good, but exact entry still needs activation." if d.get("ready") else ""}
    if pip==0.0001:
        width=max(settings.MIN_ENTRY_PIPS*pip,min(settings.MAX_ENTRY_PIPS*pip,atr*0.12))
    elif pip==0.10:
        width=max(0.8,min(3.5,atr*0.16))
    else:
        width=max(0.04,min(0.18,atr*0.16))
    if direction=="BUY":
        low=price-width*0.25; high=price+width*0.75; low,high=min(low,high),max(low,high)
        sl=low-max(width*1.4,atr*0.28); tp1=high+max(width*1.1,atr*0.32); tp2=high+max(width*2,atr*0.58); full=high+max(width*2.8,atr*0.78)
        return {"has_exact_entry":True,"direction":"ascending","setup_zone":setup,"trigger_level":trigger_text,"exact_entry":f"{rp(sym,low)} → {rp(sym,high)}","entry_pips":pips(sym,low,high),"stop_loss":rp(sym,sl),"invalidation":rp(sym,sl),"tp1_partial_close":rp(sym,tp1),"tp2":rp(sym,tp2),"full_close":rp(sym,full),"after_tp1":"Close 50% and move SL to breakeven."}
    if direction=="SELL":
        high=price+width*0.25; low=price-width*0.75; high,low=max(high,low),min(high,low)
        sl=high+max(width*1.4,atr*0.28); tp1=low-max(width*1.1,atr*0.32); tp2=low-max(width*2,atr*0.58); full=low-max(width*2.8,atr*0.78)
        return {"has_exact_entry":True,"direction":"descending","setup_zone":setup,"trigger_level":trigger_text,"exact_entry":f"{rp(sym,high)} → {rp(sym,low)}","entry_pips":pips(sym,high,low),"stop_loss":rp(sym,sl),"invalidation":rp(sym,sl),"tp1_partial_close":rp(sym,tp1),"tp2":rp(sym,tp2),"full_close":rp(sym,full),"after_tp1":"Close 50% and move SL to breakeven."}
    return {"has_exact_entry":False,"setup_zone":setup,"trigger_level":trigger_text,"exact_entry":"No valid direction.","after_tp1":"Not active."}

def close_rules(sym,direction,ind,pl):
    if not pl.get("has_exact_entry"):
        return {"close_status":"No active trade","partial_close":"No partial close until ACTIVE SCALP entry.","full_close":"No full close until ACTIVE SCALP entry.","emergency_close":"If opposite BOS/CHOCH appears before entry, cancel setup.","trailing_stop":"Not active."}
    atr=ind["atr"]
    if direction=="BUY":
        emergency="Close manually if candle closes below invalidation or opposite SELL structure appears."; trail=f"After TP1, trail stop by about {rp(sym,atr*0.45)} below recent swing low."
    elif direction=="SELL":
        emergency="Close manually if candle closes above invalidation or opposite BUY structure appears."; trail=f"After TP1, trail stop by about {rp(sym,atr*0.45)} above recent swing high."
    else:
        emergency="No active direction."; trail="Not active."
    return {"close_status":"Active management","partial_close":f"Close 50% at TP1: {pl.get('tp1_partial_close')}","full_close":f"Full close target: {pl.get('full_close')}","emergency_close":emergency,"trailing_stop":trail}

def signal(db,asset):
    sym=normalize(asset)
    try: snap=snapshot(db,sym)
    except LiveDataError as exc: return {"status":"error","asset":sym,"display":ASSETS[sym]["display"],"message":"LIVE DATA ERROR — no live price shown.","error":str(exc)}
    c=snap["candles"]; ind=build(c); weights=get_weights(db,sym); det=detect(c,ind,weights); alerts=det["alerts"]; active=list({a["strategy"] for a in alerts})
    ad=performance_for_active(db,sym,active); ses=session_info(); d=decide(det["master"],det["execution"],ses,ad,ind,sym); pl=plan(sym,d,ind); cr=close_rules(sym,d["bias"],ind,pl)
    warning=f"{d['action']}: exact entry active." if d["active"] else f"{d['action']}: {d.get('decision_reason','wait for exact trigger')}"
    return {"status":"live","asset":sym,"display":ASSETS[sym]["display"],"price":rp(sym,snap["price"]),"source":snap["source"],"source_time":snap["source_time"],"cache_age":snap["cache_age"],"stored_candles":snap["stored_candles"],"final_action":d["action"],"stage":d["stage"],"master_bias":d["bias"],"confidence":d["confidence"],"grade":d["grade"],"risk_level":d["risk_level"],"probabilities":d["probabilities"],"adaptive":ad,"conflict_interpretation":d["conflict_interpretation"],"warning":warning,"master_engine":det["master"],"execution_engine":det["execution"],"plan":pl,"close_rules":cr,"decision_reason":d.get("decision_reason"),"reward_risk":d.get("rr"),"close_rules":cr,"decision_reason":d.get("decision_reason"),"reward_risk":d.get("rr"),"timer_seconds":600 if d["active"] else 900,"indicators":{"trend":ind["trend"],"rsi":ind["rsi"],"momentum":round(ind["momentum"],6),"pressure":round(ind["pressure"],3),"atr":rp(sym,ind["atr"])},"profile":{"poc":rp(sym,ind["profile"]["poc"]),"val":rp(sym,ind["profile"]["val"]),"vah":rp(sym,ind["profile"]["vah"])},"alerts":alerts,"features":{"active_strategies":active,"setup_score":det["master"]["net"],"trigger_score":det["execution"]["net"]},"logic_note":"V15 uses SCALP READY, clear pullback/breakout triggers, adaptive backtest weights, and reward/risk filtering."}
