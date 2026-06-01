DEFAULTS={"SB_LIQUIDITY":28,"SMC_STRUCTURE":26,"SMC_FVG":14,"PROFILE":16,"TREND":7,"RAVEN_PRESSURE":14,"RAVEN_MOMENTUM":16,"REACTION_WICK":10,"DISPLACEMENT":12}
def alert(layer,model,direction,score,msg,strategy): return {"layer":layer,"model":model,"direction":direction,"score":round(score,2),"message":msg,"strategy":strategy}
def detect(c,ind,weights=None):
    weights=weights or {}
    def W(k): return float(weights.get(k,DEFAULTS[k]))
    alerts=[]; buy=sell=ebuy=esell=0; last=c[-1]
    if last["low"]<ind["prev_low"] and last["close"]>ind["prev_low"]:
        sc=W("SB_LIQUIDITY"); buy+=sc; alerts.append(alert("Master Bias","SB Liquidity","BUY",sc,"Bullish sweep below previous low.","SB_LIQUIDITY"))
    elif last["high"]>ind["prev_high"] and last["close"]<ind["prev_high"]:
        sc=W("SB_LIQUIDITY"); sell+=sc; alerts.append(alert("Master Bias","SB Liquidity","SELL",-sc,"Bearish sweep above previous high.","SB_LIQUIDITY"))
    r=c[-15:-1]; hi=max(x["high"] for x in r); lo=min(x["low"] for x in r)
    if last["close"]>hi:
        sc=W("SMC_STRUCTURE"); buy+=sc; alerts.append(alert("Master Bias","SMC Structure","BUY",sc,"Bullish BOS/CHOCH.","SMC_STRUCTURE"))
    elif last["close"]<lo:
        sc=W("SMC_STRUCTURE"); sell+=sc; alerts.append(alert("Master Bias","SMC Structure","SELL",-sc,"Bearish BOS/CHOCH.","SMC_STRUCTURE"))
    a,b,cc=c[-3],c[-2],c[-1]
    if cc["low"]>a["high"]:
        sc=W("SMC_FVG"); buy+=sc; alerts.append(alert("Master Bias","SMC FVG","BUY",sc,"Bullish FVG.","SMC_FVG"))
    elif cc["high"]<a["low"]:
        sc=W("SMC_FVG"); sell+=sc; alerts.append(alert("Master Bias","SMC FVG","SELL",-sc,"Bearish FVG.","SMC_FVG"))
    p=ind["profile"]; price=ind["price"]
    if price>p["vah"]:
        sc=W("PROFILE"); buy+=sc; alerts.append(alert("Master Bias","Frequency Profile","BUY",sc,"Price accepted above VAH.","PROFILE"))
    elif price<p["val"]:
        sc=W("PROFILE"); sell+=sc; alerts.append(alert("Master Bias","Frequency Profile","SELL",-sc,"Price accepted below VAL.","PROFILE"))
    if ind["trend"]=="bullish":
        sc=W("TREND"); buy+=sc; alerts.append(alert("Master Bias","Trend","BUY",sc,"EMA trend bullish.","TREND"))
    elif ind["trend"]=="bearish":
        sc=W("TREND"); sell+=sc; alerts.append(alert("Master Bias","Trend","SELL",-sc,"EMA trend bearish.","TREND"))
    if ind["pressure"]>0.25:
        sc=W("RAVEN_PRESSURE"); ebuy+=sc; alerts.append(alert("Execution","RAVEN Pressure","BUY",sc,"RAVEN bullish pressure.","RAVEN_PRESSURE"))
    elif ind["pressure"]<-0.25:
        sc=W("RAVEN_PRESSURE"); esell+=sc; alerts.append(alert("Execution","RAVEN Pressure","SELL",-sc,"RAVEN bearish pressure.","RAVEN_PRESSURE"))
    if ind["momentum"]>0.00025:
        sc=W("RAVEN_MOMENTUM"); ebuy+=sc; alerts.append(alert("Execution","RAVEN Momentum","BUY",sc,"RAVEN bullish acceleration.","RAVEN_MOMENTUM"))
    elif ind["momentum"]<-0.00025:
        sc=W("RAVEN_MOMENTUM"); esell+=sc; alerts.append(alert("Execution","RAVEN Momentum","SELL",-sc,"RAVEN bearish acceleration.","RAVEN_MOMENTUM"))
    if ind["rejection"]["direction"]=="BUY":
        sc=W("REACTION_WICK"); ebuy+=sc; alerts.append(alert("Execution","Reaction Wick","BUY",sc,"Bullish rejection wick.","REACTION_WICK"))
    elif ind["rejection"]["direction"]=="SELL":
        sc=W("REACTION_WICK"); esell+=sc; alerts.append(alert("Execution","Reaction Wick","SELL",-sc,"Bearish rejection wick.","REACTION_WICK"))
    if ind["displacement"]["direction"]=="BUY":
        sc=W("DISPLACEMENT"); ebuy+=sc; alerts.append(alert("Execution","Displacement","BUY",sc,"Bullish displacement.","DISPLACEMENT"))
    elif ind["displacement"]["direction"]=="SELL":
        sc=W("DISPLACEMENT"); esell+=sc; alerts.append(alert("Execution","Displacement","SELL",-sc,"Bearish displacement.","DISPLACEMENT"))
    mn=buy-sell; en=ebuy-esell
    return {"master":{"bias":"BUY" if mn>10 else "SELL" if mn<-10 else "NEUTRAL","buy_score":round(buy,2),"sell_score":round(sell,2),"net":round(mn,2)},"execution":{"bias":"BUY" if en>8 else "SELL" if en<-8 else "NEUTRAL","buy_score":round(ebuy,2),"sell_score":round(esell,2),"net":round(en,2)},"alerts":alerts}
