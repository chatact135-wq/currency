from app.config import settings
from app.services.market import candles, normalize, ASSETS, LiveDataError
from app.services.indicators import build
from app.services.smc import analyze as smc_analyze, order_block
from app.services.session import info as session_info
from app.services.news import get as news_get

def rp(symbol, val):
    pip=ASSETS[symbol]["pip"]
    if pip>=0.1: return round(float(val),2)
    if pip>=0.01: return round(float(val),3)
    return round(float(val),5)

def direction_from_score(score):
    if score >= settings.STRONG_SIGNAL_SCORE: return "STRONG BUY"
    if score >= settings.MIN_SIGNAL_SCORE: return "BUY"
    if score >= 45: return "SCALP BUY"
    if score <= -settings.STRONG_SIGNAL_SCORE: return "STRONG SELL"
    if score <= -settings.MIN_SIGNAL_SCORE: return "SELL"
    if score <= -45: return "SCALP SELL"
    return "WAIT"

def zone_pips(symbol, low, high):
    return abs(high-low)/ASSETS[symbol]["pip"]

def tight_plan(symbol, direction, ind, ob):
    price=ind["price"]; atr=ind["atr"]; pip=ASSETS[symbol]["pip"]
    # Sniper width capped: forex 4-8 pips, gold/oil adaptive
    if pip == 0.0001:
        width=max(3*pip, min(8*pip, atr*0.18))
    elif pip == 0.10:
        width=max(1.0, min(4.0, atr*0.20))
    else:
        width=max(0.05, min(0.20, atr*0.20))
    if direction=="buy":
        low=max(min(ob["low"],price), price-width)
        high=min(max(ob["high"],price), price+width)
        sl=low - max(width*1.7, atr*0.35)
        tp1=high + max(width*1.5, atr*0.35)
        tp2=high + max(width*2.8, atr*0.7)
        full=high + max(width*3.5, atr*0.9)
        invalid=sl
    elif direction=="sell":
        low=max(min(ob["low"],price), price-width)
        high=min(max(ob["high"],price), price+width)
        sl=high + max(width*1.7, atr*0.35)
        tp1=low - max(width*1.5, atr*0.35)
        tp2=low - max(width*2.8, atr*0.7)
        full=low - max(width*3.5, atr*0.9)
        invalid=sl
    else:
        low=ind["support_soft"]; high=ind["resistance_soft"]; sl=price-atr; tp1=price+atr; tp2=price+atr*1.5; full=price+atr*2; invalid=sl
    return {
        "entry":{"low":rp(symbol,low), "high":rp(symbol,high), "pips":round(zone_pips(symbol, low, high),1)},
        "stop_loss":rp(symbol,sl), "tp1_partial_close":rp(symbol,tp1), "tp2":rp(symbol,tp2),
        "full_close":rp(symbol,full), "invalidation":rp(symbol,invalid),
        "after_tp1":"Close 50% and move SL to breakeven."
    }

def signal(asset):
    symbol=normalize(asset)
    try:
        live=candles(symbol)
    except LiveDataError as e:
        return {"status":"error","asset":symbol,"display":ASSETS[symbol]["display"],"message":"LIVE DATA ERROR — no fake price shown.","error":str(e)}
    cs=live["candles"]; ind=build(cs); smc=smc_analyze(cs,ind); ses=session_info(); nw=news_get(symbol)
    matched=[]; missing=[]
    bull=0; bear=0

    # SMC weighted but not mandatory
    if smc["score"]>0: bull += abs(smc["score"]); matched += smc["matched"]
    elif smc["score"]<0: bear += abs(smc["score"]); matched += smc["matched"]
    missing += smc["missing"]

    # Trend/momentum reacts faster than V5
    if ind["trend"]=="bullish": bull+=15; matched.append("EMA trend bullish.")
    elif ind["trend"]=="bearish": bear+=15; matched.append("EMA trend bearish.")
    else: missing.append("EMA trend mixed.")

    if ind["momentum"]>0.00025: bull+=14; matched.append("Short-term momentum bullish.")
    elif ind["momentum"]<-0.00025: bear+=14; matched.append("Short-term momentum bearish.")
    else: missing.append("Momentum weak.")

    if ind["pressure"]>0.25: bull+=10; matched.append("Recent candle pressure bullish.")
    elif ind["pressure"]<-0.25: bear+=10; matched.append("Recent candle pressure bearish.")
    else: missing.append("Candle pressure neutral.")

    if ind["rsi"]<35: bull+=8; matched.append("RSI low/oversold supports buy bounce.")
    elif ind["rsi"]>65: bear+=8; matched.append("RSI high/overbought supports sell pullback.")
    else: missing.append("RSI not extreme.")

    if nw["score"]>0: bull+=min(14,nw["score"]); matched.append(f"News bias bullish: {nw['explanation']}")
    elif nw["score"]<0: bear+=min(14,abs(nw["score"])); matched.append(f"News bias bearish: {nw['explanation']}")
    else: missing.append(nw["explanation"])

    if ses["score"]>0:
        bull+=ses["score"]/2; bear+=ses["score"]/2; matched.append(f"Good session: {ses['name']}.")
    elif ses["score"]<0:
        bull+=ses["score"]; bear+=ses["score"]; missing.append("Low liquidity session reduces quality.")

    net=bull-bear
    dominant="buy" if net>0 else "sell" if net<0 else "neutral"
    quality=max(bull,bear)
    signed_quality=quality if dominant=="buy" else -quality if dominant=="sell" else 0
    act=direction_from_score(signed_quality)

    # Avoid permanent no-trade: show directional watch if not enough score
    if act=="WAIT":
        act="BUY WATCH" if dominant=="buy" and quality>=35 else "SELL WATCH" if dominant=="sell" and quality>=35 else "WAIT"

    plan_dir="buy" if "BUY" in act else "sell" if "SELL" in act else "none"
    ob=order_block(cs, plan_dir)
    plan=tight_plan(symbol, plan_dir, ind, ob)

    # Timers
    timer=10*60 if "WATCH" in act or "SCALP" in act else 30*60 if act in ["BUY","SELL"] else 45*60
    if act=="WAIT": timer=5*60

    warning = "No forced trade. Wait for trigger." if act=="WAIT" else f"{act}: use exact entry interval only; cancel if invalidation breaks."

    return {
        "status":"live","asset":symbol,"display":ASSETS[symbol]["display"],"price":rp(symbol,ind["price"]),
        "action":act,"bias":dominant,"quality":round(quality,1),"raw_net":round(net,1),
        "source":live["source"],"source_time":live["source_time"],"cache_age":live["cache_age"],
        "indicators":{"trend":ind["trend"],"rsi":ind["rsi"],"momentum":round(ind["momentum"],6),"pressure":round(ind["pressure"],3),"atr":rp(symbol,ind["atr"])},
        "plan":plan,"timer_seconds":timer,"warning":warning,
        "matched":matched[:9],"missing":missing[:9],
        "smc":smc,"news":nw,"session":ses,
        "decision_note":"V6 uses weighted scoring; it does not require liquidity sweep + FVG + BOS all together."
    }
