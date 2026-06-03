from app.config import settings
from app.services.market import ASSETS, normalize, snapshot, LiveDataError
from app.services.indicators import build
from app.services.core import detect
from app.services.adaptive import get_weights, performance_for_active
from app.services.session import info as session_info
from app.services.smc2 import smc2_analysis
from app.services.signal_lock import apply_signal_lock
from app.services.time_forecast import forecast
from app.services.market_map import build_market_map
from app.services.regime_guard import market_regime, trigger_state, apply_regime_to_permission
from app.services.alert_engine import classify_fast_move, remember_alerts
from app.services.freshness_guard import apply_freshness_guard
from app.services.signal_memory import apply_signal_memory
from app.services.active_mode import apply_active_mode
from app.services.simple_words import apply_simple_words
from app.services.news_engine import news_state
from app.services.history_memory import level_memory
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


def micro_trigger_distance(sym):
    pip = ASSETS[sym]["pip"]
    if pip == 0.0001:
        return {"near": 2 * pip, "far": 6 * pip}
    if pip >= 0.10:
        return {"near": 0.8, "far": 2.8}
    return {"near": 0.03, "far": 0.10}

def plan(sym, d, ind):
    direction = d["bias"]
    price = ind["price"]
    pip = ASSETS[sym]["pip"]
    atr = ind["atr"]
    md = micro_trigger_distance(sym)

    if direction == "BUY":
        pullback_high = price - md["near"]
        pullback_low = price - md["far"]
        breakout = price + md["near"]
        setup = f"{rp(sym, pullback_low)} → {rp(sym, pullback_high)}"
        trigger_text = f"Micro pullback zone {rp(sym, pullback_low)} → {rp(sym, pullback_high)} OR breakout above {rp(sym, breakout)}"
        primary_level = breakout
    elif direction == "SELL":
        pullback_low = price + md["near"]
        pullback_high = price + md["far"]
        breakdown = price - md["near"]
        setup = f"{rp(sym, pullback_high)} → {rp(sym, pullback_low)}"
        trigger_text = f"Micro pullback zone {rp(sym, pullback_low)} → {rp(sym, pullback_high)} OR breakdown below {rp(sym, breakdown)}"
        primary_level = breakdown
    else:
        setup = "No valid setup zone"
        trigger_text = "No trigger"
        primary_level = None

    if not d["active"]:
        return {
            "has_exact_entry": False,
            "setup_zone": setup,
            "trigger_level": trigger_text,
            "primary_level": primary_level,
            "exact_entry": "No exact entry until ACTIVE SCALP confirms.",
            "after_tp1": "No trade management until exact entry is active.",
            "ready_note": "SCALP READY means direction is good, but exact entry still needs activation." if d.get("ready") else ""
        }

    # active entry stays tight around live price
    if pip == 0.0001:
        width = max(3 * pip, min(6 * pip, atr * 0.10))
    elif pip >= 0.10:
        width = max(0.8, min(2.6, atr * 0.14))
    else:
        width = max(0.03, min(0.10, atr * 0.14))

    if direction == "BUY":
        low = price - width * 0.25
        high = price + width * 0.75
        low, high = min(low, high), max(low, high)
        sl = low - max(width * 1.25, atr * 0.24)
        tp1 = high + max(width * 1.05, atr * 0.28)
        tp2 = high + max(width * 1.8, atr * 0.48)
        full = high + max(width * 2.5, atr * 0.68)
        return {
            "has_exact_entry": True,
            "direction": "ascending",
            "setup_zone": setup,
            "trigger_level": trigger_text,
            "primary_level": primary_level,
            "exact_entry": f"{rp(sym, low)} → {rp(sym, high)}",
            "entry_pips": pips(sym, low, high),
            "stop_loss": rp(sym, sl),
            "invalidation": rp(sym, sl),
            "tp1_partial_close": rp(sym, tp1),
            "tp2": rp(sym, tp2),
            "full_close": rp(sym, full),
            "after_tp1": "Close 50% and move SL to breakeven."
        }

    if direction == "SELL":
        high = price + width * 0.25
        low = price - width * 0.75
        high, low = max(high, low), min(high, low)
        sl = high + max(width * 1.25, atr * 0.24)
        tp1 = low - max(width * 1.05, atr * 0.28)
        tp2 = low - max(width * 1.8, atr * 0.48)
        full = low - max(width * 2.5, atr * 0.68)
        return {
            "has_exact_entry": True,
            "direction": "descending",
            "setup_zone": setup,
            "trigger_level": trigger_text,
            "primary_level": primary_level,
            "exact_entry": f"{rp(sym, high)} → {rp(sym, low)}",
            "entry_pips": pips(sym, high, low),
            "stop_loss": rp(sym, sl),
            "invalidation": rp(sym, sl),
            "tp1_partial_close": rp(sym, tp1),
            "tp2": rp(sym, tp2),
            "full_close": rp(sym, full),
            "after_tp1": "Close 50% and move SL to breakeven."
        }

    return {"has_exact_entry": False, "setup_zone": setup, "trigger_level": trigger_text, "primary_level": primary_level, "exact_entry": "No valid direction.", "after_tp1": "Not active."}

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


def historical_ok(hm):
    if not hm or hm.get("success_rate") is None:
        return True
    return hm.get("success_rate", 0) >= 42

def historical_strong(hm):
    return bool(hm and hm.get("success_rate") is not None and hm.get("success_rate", 0) >= 55)

def direction_probability(d):
    if d.get("bias") == "BUY":
        return d["probabilities"].get("up", 0)
    if d.get("bias") == "SELL":
        return d["probabilities"].get("down", 0)
    return 0

def pretrade_levels(sym, direction, price, ind):
    pip = ASSETS[sym]["pip"]
    atr = ind["atr"]
    if pip == 0.0001:
        entry_width = max(3*pip, min(6*pip, atr*0.10))
    elif pip >= 0.10:
        entry_width = max(0.8, min(2.6, atr*0.14))
    else:
        entry_width = max(0.03, min(0.10, atr*0.14))
    if direction == "BUY":
        entry_low = price - entry_width*0.25
        entry_high = price + entry_width*0.75
        sl = entry_low - max(entry_width*1.25, atr*0.24)
        tp1 = entry_high + max(entry_width*1.05, atr*0.28)
        tp2 = entry_high + max(entry_width*1.8, atr*0.48)
        full = entry_high + max(entry_width*2.5, atr*0.68)
        return {"entry": f"{rp(sym, entry_low)} → {rp(sym, entry_high)}", "stop": rp(sym, sl), "tp1": rp(sym, tp1), "tp2": rp(sym, tp2), "full": rp(sym, full)}
    if direction == "SELL":
        entry_high = price + entry_width*0.25
        entry_low = price - entry_width*0.75
        sl = entry_high + max(entry_width*1.25, atr*0.24)
        tp1 = entry_low - max(entry_width*1.05, atr*0.28)
        tp2 = entry_low - max(entry_width*1.8, atr*0.48)
        full = entry_low - max(entry_width*2.5, atr*0.68)
        return {"entry": f"{rp(sym, entry_high)} → {rp(sym, entry_low)}", "stop": rp(sym, sl), "tp1": rp(sym, tp1), "tp2": rp(sym, tp2), "full": rp(sym, full)}
    return {"entry":"-", "stop":"-", "tp1":"-", "tp2":"-", "full":"-"}

def build_best_action(sym, d, pl, hm, ad, ind, det):
    direction = d.get("bias")
    prob = direction_probability(d)
    rr = (d.get("rr") or {}).get("rr", 0)
    aligned = d.get("conflict_interpretation", "").startswith("Aligned")
    hist_ok = historical_ok(hm)
    hist_strong = historical_strong(hm)
    adaptive_prob = ad.get("probability")
    adaptive_ok = adaptive_prob is None or adaptive_prob >= 52
    confidence = d.get("confidence", 0)
    levels = pretrade_levels(sym, direction, ind["price"], ind)

    # Practical executor score. This is not a guarantee; it ranks the current opportunity.
    score = 0
    score += min(30, confidence * 0.30)
    score += 18 if aligned else 0
    score += 15 if prob >= 60 else 8 if prob >= 52 else 0
    score += 12 if rr >= 1.2 else 6 if rr >= 0.9 else 0
    score += 12 if hist_strong else 6 if hist_ok else -10
    score += 10 if adaptive_prob is None else 10 if adaptive_prob >= 58 else 5 if adaptive_prob >= 52 else -8
    score = round(max(0, min(100, score)), 1)

    if direction not in ["BUY", "SELL"]:
        label = "NO TRADE"
        mode = "WAIT"
        instruction = "Do nothing. No clear direction."
    elif d.get("active") and score >= 70:
        label = f"EXECUTE {direction}"
        mode = "EXECUTE"
        instruction = f"{direction} is active. Use exact entry {levels['entry']}. Stop {levels['stop']}. TP1 {levels['tp1']}."
    elif aligned and score >= 58 and hist_ok and adaptive_ok:
        label = f"CONDITIONAL {direction}"
        mode = "CONDITIONAL"
        instruction = f"Prepare {direction}, but only enter if trigger activates. Entry {levels['entry']}. Stop {levels['stop']}. TP1 {levels['tp1']}."
    elif d.get("stage") in ["SETUP READY", "SCALP READY", "PRECISION WATCH"] and score >= 48:
        label = f"WATCH {direction}"
        mode = "WATCH"
        instruction = f"Direction is {direction}, but confirmation is not enough. Wait for trigger: {pl.get('trigger_level','-')}"
    else:
        label = "NO TRADE"
        mode = "WAIT"
        instruction = "Do not enter now. Conditions are not strong enough."

    if direction == "BUY":
        trigger = pl.get("trigger_level", "Buy only after pullback reaction or breakout activation.")
        cancel = f"Cancel BUY if price closes below stop/invalidation {levels['stop']} or opposite SELL structure appears."
    elif direction == "SELL":
        trigger = pl.get("trigger_level", "Sell only after pullback rejection or breakdown activation.")
        cancel = f"Cancel SELL if price closes above stop/invalidation {levels['stop']} or opposite BUY structure appears."
    else:
        trigger = "No trigger."
        cancel = "No trade."

    return {
        "label": label,
        "mode": mode,
        "score": score,
        "direction": direction,
        "probability_used": prob,
        "reward_risk": rr,
        "trigger": trigger,
        "instruction": instruction,
        "entry": levels["entry"],
        "stop": levels["stop"],
        "tp1": levels["tp1"],
        "tp2": levels["tp2"],
        "full_close": levels["full"],
        "cancel": cancel,
        "why": {
            "aligned": aligned,
            "history_ok": hist_ok,
            "history_success": hm.get("success_rate") if hm else None,
            "adaptive_probability": adaptive_prob,
            "confidence": confidence,
            "probability": prob
        }
    }


def smc2_final_adjustment(result_direction, result_action, smc2, probability_up, probability_down):
    # SMC 2.0 is a context/zone/trigger module.
    # It can upgrade confidence when it agrees, or downgrade when it conflicts.
    smc_dir = smc2.get("direction", "NEUTRAL")
    smc_conf = smc2.get("confidence", 0)
    note = "SMC 2.0 neutral; normal decision rules used."

    if smc_dir == "NEUTRAL":
        return result_action, note, 0

    if smc_dir in result_action:
        note = "SMC 2.0 agrees with the final direction."
        return result_action, note, 8

    if result_action == "WAIT" or "WATCH" in result_action or "SETUP" in result_action:
        if smc_conf >= 60:
            note = f"SMC 2.0 favors {smc_dir}; final action stays conditional until trigger confirms."
            return f"CONDITIONAL {smc_dir}", note, 5

    # Conflict: SMC says opposite direction.
    if smc_conf >= 65:
        note = f"SMC 2.0 conflicts with current direction; avoid execution until resolved."
        return f"NO TRADE - SMC CONFLICT", note, -12

    return result_action, "SMC 2.0 weak conflict/mixed; no upgrade.", -4



def final_decision_gate(d, ad, hm=None, smc2=None):
    action = d.get("action", "WAIT")
    stage = d.get("stage", "WAIT")
    direction = d.get("bias", "NEUTRAL")
    conf = float(d.get("confidence") or 0)

    # Default: no entry unless the system reaches active/execute status.
    permission = "NO_ENTRY"
    final = "WAIT"
    command = "WAIT"

    if "CANCEL" in action or "NO TRADE" in action:
        final = "CANCEL / NO TRADE"
        command = "DO NOT ENTER"
    elif ("ACTIVE" in action or "EXECUTE" in action or stage == "EXECUTION ACTIVE") and direction in ["BUY", "SELL"]:
        permission = "ENTRY_ALLOWED"
        final = f"ENTER {direction}"
        command = f"ENTER {direction} ONLY WITH SL/TP"
    elif "READY" in action or "WATCH" in action or "CONDITIONAL" in action or "SETUP" in action:
        final = f"WAIT FOR {direction} TRIGGER" if direction in ["BUY", "SELL"] else "WAIT"
        command = "WAIT - DO NOT ENTER YET"
    else:
        final = "WAIT"
        command = "WAIT - NO TRADE"

    # Historical memory/adaptive can downgrade but not blindly upgrade.
    if hm and hm.get("success_rate") is not None and hm.get("success_rate", 0) < 40 and permission == "ENTRY_ALLOWED":
        permission = "NO_ENTRY"
        final = f"WAIT - HISTORY WEAK FOR {direction}"
        command = "WAIT - HISTORY DOES NOT SUPPORT ENTRY"

    if ad and ad.get("probability") is not None and ad.get("probability", 0) < 52 and permission == "ENTRY_ALLOWED":
        permission = "NO_ENTRY"
        final = f"WAIT - BACKTEST EDGE WEAK FOR {direction}"
        command = "WAIT - ADAPTIVE EDGE WEAK"

    return {
        "final_action": final,
        "command": command,
        "entry_permission": permission,
        "direction": direction,
        "confidence": conf,
        "rule": "Entry is allowed only when final decision gate permits it. Probability alone is not entry permission."
    }



def apply_news_gate(result, news):
    result["news"]=news
    fd=result.get("final_decision") or {}
    if news.get("risk")=="HIGH" and news.get("mode")=="NEWS_WAIT":
        result["final_action"]="WAIT - NEWS COMING"
        result["warning"]="High-impact news is close. Wait until release and first impulse confirms."
        result["entry_permission"]="NO_ENTRY"
        if fd:
            fd["final_action"]="WAIT - NEWS COMING"; fd["command"]="DO NOT ENTER BEFORE NEWS"; fd["entry_permission"]="NO_ENTRY"; fd["rule"]="News gate blocks new entries before high-impact news."; result["final_decision"]=fd
    elif news.get("risk")=="HIGH" and news.get("mode")=="POST_NEWS_IMPULSE":
        result["warning"]="Post-news impulse window. Use only confirmed breakout/pullback, smaller risk."
        if fd:
            fd["rule"]=fd.get("rule","")+" Post-news impulse mode active."; result["final_decision"]=fd
    return result


def signal(db,asset):
    sym=normalize(asset)
    try: snap=snapshot(db,sym)
    except LiveDataError as exc: return {"status":"error","asset":sym,"display":ASSETS[sym]["display"],"message":"LIVE DATA ERROR — no live price shown.","error":str(exc)}
    nw=news_state(sym)
    c=snap["candles"]; ind=build(c); ind["price"]=snap["price"]; smc2=smc2_analysis(sym,c,ind,ASSETS); weights=get_weights(db,sym); det=detect(c,ind,weights); alerts=det["alerts"]; active=list({a["strategy"] for a in alerts})
    ad=performance_for_active(db,sym,active); ses=session_info(); d=decide(det["master"],det["execution"],ses,ad,ind,sym); pl=plan(sym,d,ind); hm=level_memory(db,sym,pl.get("primary_level"),d["bias"]); cr=close_rules(sym,d["bias"],ind,pl)
    fd=final_decision_gate(d,ad,hm if "hm" in locals() else None,smc2 if "smc2" in locals() else None)
    tf=forecast(sym,c,snap["price"],fd["final_action"],pl,ind); ba=build_best_action(sym,d,pl,hm,ad,ind,det)
    adjusted_action, smc_note, smc_bonus = smc2_final_adjustment(d["bias"], d["action"], smc2, d["probabilities"]["up"], d["probabilities"]["down"])
    d["action"] = adjusted_action
    d["confidence"] = max(20, min(99, d["confidence"] + smc_bonus))
    warning=f"{d['action']}: exact entry active." if d["active"] else f"{d['action']}: {d.get('decision_reason','wait for exact trigger')}"
    result={"status":"live","asset":sym,"display":ASSETS[sym]["display"],"price":rp(sym,snap["price"]),"source":snap["source"],"source_time":snap["source_time"],"cache_age":snap["cache_age"],"stored_candles":snap["stored_candles"],"chart_candles":[{"t":x.get("datetime"),"o":round(float(x.get("open",0)),5),"h":round(float(x.get("high",0)),5),"l":round(float(x.get("low",0)),5),"c":round(float(x.get("close",0)),5)} for x in c[-40:]],"data_fresh":snap.get("data_fresh"),"stale_reasons":snap.get("stale_reasons",[]),"live_price_cache_age":snap.get("live_price_cache_age"),"candle_close_price":rp(sym,snap.get("candle_close_price",snap["price"])),"price_difference_from_candle":rp(sym,snap.get("price_difference_from_candle",0)),"final_action":d["action"],"stage":d["stage"],"master_bias":d["bias"],"confidence":d["confidence"],"grade":d["grade"],"risk_level":d["risk_level"],"probabilities":d["probabilities"],"adaptive":ad,"news":nw,"final_decision":fd,"time_forecast":tf,"smc2":smc2,"smc_note":smc_note,"conflict_interpretation":d["conflict_interpretation"],"warning":warning,"master_engine":det["master"],"execution_engine":det["execution"],"plan":pl,"best_action":ba,"close_rules":cr,"decision_reason":d.get("decision_reason"),"reward_risk":d.get("rr"),"history_memory":hm,"close_rules":cr,"decision_reason":d.get("decision_reason"),"reward_risk":d.get("rr"),"history_memory":hm,"timer_seconds":600 if d["active"] else 900,"indicators":{"trend":ind["trend"],"rsi":ind["rsi"],"momentum":round(ind["momentum"],6),"pressure":round(ind["pressure"],3),"atr":rp(sym,ind["atr"])},"profile":{"poc":rp(sym,ind["profile"]["poc"]),"val":rp(sym,ind["profile"]["val"]),"vah":rp(sym,ind["profile"]["vah"])},"alerts":alerts,"features":{"smc2_direction":smc2.get("direction"),"active_strategies":active,"setup_score":det["master"]["net"],"trigger_score":det["execution"]["net"]},"logic_note":"V28 adds alert engine and fast-move detector for fast buy/sell, retest and no-chase alerts."}
    result=apply_signal_lock(db,result)
    result["market_map"] = build_market_map(sym,c,ind,result)
    mm = result.get("market_map") or {}
    tm = mm.get("trade_map") or {}
    cs = mm.get("current_state") or {}
    rg = market_regime(sym,c,result)
    ts = trigger_state(sym, result.get("price"), cs.get("bias"), tm.get("aggressive_entry"), tm.get("safe_entry"), tm.get("cancel_level"))
    result = apply_regime_to_permission(result, rg, ts)
    fast_alerts = classify_fast_move(sym,c,result)
    result["alerts"] = remember_alerts(sym, fast_alerts)
    result = apply_signal_memory(db,result)
    result = apply_active_mode(result)
    result = apply_simple_words(result)
    result=apply_freshness_guard(result)
    return apply_news_gate(result,nw)
