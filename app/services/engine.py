from app.config import settings
from app.services.market import ASSETS, normalize, market_snapshot, LiveDataError, CollectingTicks
from app.services.indicators import build
from app.services.session import info as session_info

def rp(symbol,v):
    pip=ASSETS[symbol]["pip"]
    if pip>=0.1: return round(float(v),2)
    if pip>=0.01: return round(float(v),3)
    return round(float(v),5)
def pips(symbol,a,b): return round(abs(a-b)/ASSETS[symbol]["pip"],1)
def al(layer, model, direction, score, msg, interp=""):
    return {"layer":layer,"model":model,"direction":direction,"score":round(score,1),"message":msg,"interpretation":interp}

def master(symbol,c,ind):
    alerts=[]; buy=0; sell=0; last=c[-1]
    if last["low"]<ind["prev_low"] and last["close"]>ind["prev_low"]:
        buy+=28; alerts.append(al("Master Bias","SB Liquidity","BUY",28,"Bullish sweep below previous low.","Primary direction"))
    elif last["high"]>ind["prev_high"] and last["close"]<ind["prev_high"]:
        sell+=28; alerts.append(al("Master Bias","SB Liquidity","SELL",-28,"Bearish sweep above previous high.","Primary direction"))
    recent=c[-12:-1]; hi=max(x["high"] for x in recent); lo=min(x["low"] for x in recent)
    if last["close"]>hi:
        buy+=24; alerts.append(al("Master Bias","SMC Structure","BUY",24,"Bullish BOS/CHOCH.","Primary direction"))
    elif last["close"]<lo:
        sell+=24; alerts.append(al("Master Bias","SMC Structure","SELL",-24,"Bearish BOS/CHOCH.","Primary direction"))
    a,b,cc=c[-3],c[-2],c[-1]
    if cc["low"]>a["high"]:
        buy+=14; alerts.append(al("Master Bias","SMC FVG","BUY",14,"Bullish FVG.","Direction support"))
    elif cc["high"]<a["low"]:
        sell+=14; alerts.append(al("Master Bias","SMC FVG","SELL",-14,"Bearish FVG.","Direction support"))
    prof=ind["profile"]; price=ind["price"]
    if price>prof["vah"]:
        buy+=14; alerts.append(al("Master Bias","Frequency Profile","BUY",14,"Price accepted above VAH.","Auction direction"))
    elif price<prof["val"]:
        sell+=14; alerts.append(al("Master Bias","Frequency Profile","SELL",-14,"Price accepted below VAL.","Auction direction"))
    if ind["trend"]=="bullish":
        buy+=6; alerts.append(al("Master Bias","Trend","BUY",6,"EMA trend bullish.","Small confirmation"))
    elif ind["trend"]=="bearish":
        sell+=6; alerts.append(al("Master Bias","Trend","SELL",-6,"EMA trend bearish.","Small confirmation"))
    net=buy-sell; bias="BUY" if net>10 else "SELL" if net<-10 else "NEUTRAL"
    return {"bias":bias,"buy_score":round(buy,1),"sell_score":round(sell,1),"net":round(net,1),"alerts":alerts}

def execution(ind):
    alerts=[]; buy=0; sell=0
    if ind["pressure"]>0.25:
        buy+=14; alerts.append(al("Execution","RAVEN Pressure","BUY",14,"RAVEN bullish pressure.","Timing only"))
    elif ind["pressure"]<-0.25:
        sell+=14; alerts.append(al("Execution","RAVEN Pressure","SELL",-14,"RAVEN bearish pressure.","Timing only"))
    if ind["momentum"]>0.00025:
        buy+=16; alerts.append(al("Execution","RAVEN Momentum","BUY",16,"RAVEN bullish acceleration.","Timing only"))
    elif ind["momentum"]<-0.00025:
        sell+=16; alerts.append(al("Execution","RAVEN Momentum","SELL",-16,"RAVEN bearish acceleration.","Timing only"))
    if ind["rejection"]["direction"]=="BUY":
        buy+=10; alerts.append(al("Execution","Reaction Wick","BUY",10,"Bullish rejection wick.","Trigger"))
    elif ind["rejection"]["direction"]=="SELL":
        sell+=10; alerts.append(al("Execution","Reaction Wick","SELL",-10,"Bearish rejection wick.","Trigger"))
    if ind["displacement"]["direction"]=="BUY":
        buy+=12; alerts.append(al("Execution","Displacement","BUY",12,"Bullish displacement.","Trigger"))
    elif ind["displacement"]["direction"]=="SELL":
        sell+=12; alerts.append(al("Execution","Displacement","SELL",-12,"Bearish displacement.","Trigger"))
    net=buy-sell; bias="BUY" if net>8 else "SELL" if net<-8 else "NEUTRAL"
    return {"bias":bias,"buy_score":round(buy,1),"sell_score":round(sell,1),"net":round(net,1),"alerts":alerts}

def decide(m,e,session):
    conflict="Master bias and execution aligned." if m["bias"]==e["bias"] and m["bias"]!="NEUTRAL" else "Pullback/risk or incomplete alignment."
    aligned=m["bias"]!="NEUTRAL" and m["bias"]==e["bias"]
    strength=abs(m["net"])*0.75+abs(e["net"])*0.65+max(0,session["score"])
    risk="LOW" if session["score"]>=0 and "aligned" in conflict else "MEDIUM"
    if aligned and strength>=settings.ACTIVE_SCORE:
        action=f"ACTIVE SCALP {m['bias']}"; stage="EXECUTION ACTIVE"; active=True; bias=m["bias"]
    elif m["bias"]!="NEUTRAL" and abs(m["net"])>=settings.SETUP_SCORE:
        action=f"{m['bias']} SETUP READY"; stage="SETUP READY"; active=False; bias=m["bias"]
    elif e["bias"]!="NEUTRAL" and abs(e["net"])>=settings.WATCH_SCORE:
        action=f"{e['bias']} TRIGGER WATCH"; stage="TRIGGER WATCH"; active=False; bias=e["bias"]
    else:
        action="WAIT"; stage="WAIT"; active=False; bias=m["bias"] if m["bias"]!="NEUTRAL" else e["bias"]
    conf=round(min(95,max(35,strength)),1)
    grade="A+" if active and conf>=88 and risk=="LOW" else "A" if active and conf>=76 else "B" if conf>=64 else "C" if conf>=50 else "D"
    buy=m["buy_score"]+e["buy_score"]; sell=m["sell_score"]+e["sell_score"]; total=buy+sell+25
    up=round((buy/total)*100,1); down=round((sell/total)*100,1); side=round(max(5,100-up-down),1)
    return {"action":action,"stage":stage,"active":active,"bias":bias,"confidence":conf,"grade":grade,"risk_level":risk,"probabilities":{"up":up,"sideways":side,"down":down},"conflict_interpretation":conflict}

def plan(symbol,d,ind):
    direction=d["bias"]; price=ind["price"]; pip=ASSETS[symbol]["pip"]; atr=ind["atr"]
    if not d["active"]:
        if direction=="BUY":
            setup=f"{rp(symbol,min(ind['support_soft'],price))} → {rp(symbol,max(ind['support_soft'],price))}"; trigger=ind["resistance_soft"]
        elif direction=="SELL":
            setup=f"{rp(symbol,max(ind['resistance_soft'],price))} → {rp(symbol,min(ind['resistance_soft'],price))}"; trigger=ind["support_soft"]
        else:
            setup="No valid setup zone"; trigger=price
        return {"has_exact_entry":False,"setup_zone":setup,"trigger_level":rp(symbol,trigger),"exact_entry":"No exact entry until ACTIVE SCALP confirms.","after_tp1":"No trade management until exact entry is active."}
    if pip==0.0001: width=max(settings.MIN_ENTRY_PIPS*pip,min(settings.MAX_ENTRY_PIPS*pip,atr*0.12))
    elif pip==0.10: width=max(0.8,min(3.5,atr*0.16))
    else: width=max(0.04,min(0.18,atr*0.16))
    if direction=="BUY":
        low=price-width*.25; high=price+width*.75; low,high=min(low,high),max(low,high)
        sl=low-max(width*1.4,atr*.28); tp1=high+max(width*1.1,atr*.32); tp2=high+max(width*2,atr*.58); full=high+max(width*2.8,atr*.78)
        return {"has_exact_entry":True,"direction":"ascending","exact_entry":f"{rp(symbol,low)} → {rp(symbol,high)}","entry_pips":pips(symbol,low,high),"stop_loss":rp(symbol,sl),"invalidation":rp(symbol,sl),"tp1_partial_close":rp(symbol,tp1),"tp2":rp(symbol,tp2),"full_close":rp(symbol,full),"after_tp1":"Close 50% and move SL to breakeven."}
    high=price+width*.25; low=price-width*.75; high,low=max(high,low),min(high,low)
    sl=high+max(width*1.4,atr*.28); tp1=low-max(width*1.1,atr*.32); tp2=low-max(width*2,atr*.58); full=low-max(width*2.8,atr*.78)
    return {"has_exact_entry":True,"direction":"descending","exact_entry":f"{rp(symbol,high)} → {rp(symbol,low)}","entry_pips":pips(symbol,high,low),"stop_loss":rp(symbol,sl),"invalidation":rp(symbol,sl),"tp1_partial_close":rp(symbol,tp1),"tp2":rp(symbol,tp2),"full_close":rp(symbol,full),"after_tp1":"Close 50% and move SL to breakeven."}

def signal(db, asset):
    symbol=normalize(asset)
    try:
        snap=market_snapshot(db,symbol)
    except CollectingTicks as exc:
        return {"status":"collecting","asset":symbol,"display":ASSETS[symbol]["display"],"message":str(exc)}
    except LiveDataError as exc:
        return {"status":"error","asset":symbol,"display":ASSETS[symbol]["display"],"message":"LIVE DATA ERROR — no live price shown.","error":str(exc)}
    c=snap["candles"]; ind=build(c); ses=session_info(); m=master(symbol,c,ind); e=execution(ind); d=decide(m,e,ses); pl=plan(symbol,d,ind)
    warning=f"{d['action']}: exact entry active." if d["active"] else f"{d['action']}: wait for exact trigger."
    return {"status":"live","asset":symbol,"display":ASSETS[symbol]["display"],"price":rp(symbol,snap["price"]),"source":snap["source"],"source_time":snap["source_time"],"cache_age":snap["cache_age"],"tick_count":snap["tick_count"],"final_action":d["action"],"stage":d["stage"],"master_bias":d["bias"],"confidence":d["confidence"],"grade":d["grade"],"risk_level":d["risk_level"],"probabilities":d["probabilities"],"conflict_interpretation":d["conflict_interpretation"],"warning":warning,"master_engine":m,"execution_engine":e,"confirmation_engine":{"modifier":ses["score"],"alerts":[al("Confirmation","Session","NEUTRAL",ses["score"],f"Session: {ses['name']}","Risk/confidence")]},"plan":pl,"timer_seconds":600 if d["active"] else 900,"indicators":{"trend":ind["trend"],"rsi":ind["rsi"],"momentum":round(ind["momentum"],6),"pressure":round(ind["pressure"],3),"atr":rp(symbol,ind["atr"]),"rejection":ind["rejection"],"displacement":ind["displacement"]},"profile":{"poc":rp(symbol,ind["profile"]["poc"]),"val":rp(symbol,ind["profile"]["val"]),"vah":rp(symbol,ind["profile"]["vah"])},"alerts":m["alerts"]+e["alerts"],"features":{"trend":ind["trend"],"rsi":ind["rsi"],"atr":ind["atr"],"momentum":ind["momentum"],"pressure":ind["pressure"],"master_bias":m["bias"],"execution_bias":e["bias"],"session":ses["name"]},"logic_note":"V11 uses Finnhub live quotes + Neon tick memory + self-built candles. No blocked candle endpoint."}
