
from datetime import datetime, timezone
import os
from app.services.market import ASSETS, normalize

_MEM = {}

def _now():
    return datetime.now(timezone.utc)

def _upper(v):
    return str(v or "").upper()

def _num(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def _step(sym):
    return ASSETS[sym]["pip"] / 10

def _moves(sym, a, b):
    try:
        return abs(float(a) - float(b)) / _step(sym)
    except Exception:
        return None

def _last_candle(sym, candles):
    if not candles:
        return {}
    c = candles[-1]
    o = _num(c.get("open"))
    h = _num(c.get("high"))
    l = _num(c.get("low"))
    cl = _num(c.get("close"))
    if None in [o,h,l,cl]:
        return {}
    d = "BUY" if cl > o else "SELL" if cl < o else "NEUTRAL"
    return {"open":o,"high":h,"low":l,"close":cl,"direction":d,
            "body_moves":round(_moves(sym,o,cl) or 0,1),
            "range_moves":round(_moves(sym,l,h) or 0,1)}

def _recent_range(candles, n=12):
    if not candles or len(candles) < 6:
        return None
    recent = candles[-n:] if len(candles) >= n else candles
    highs = [_num(c.get("high")) for c in recent if _num(c.get("high")) is not None]
    lows = [_num(c.get("low")) for c in recent if _num(c.get("low")) is not None]
    if not highs or not lows:
        return None
    return {"high":max(highs),"low":min(lows)}

def _direction(result, candles):
    for obj in [result.get("pro_panel") or {}, result.get("scalp_entry") or {}, result.get("fast_start") or {}, result.get("next_plan") or {}, result.get("trade_readiness") or {}]:
        d=_upper(obj.get("direction"))
        if d in ["BUY","SELL"]:
            return d
        s=_upper(obj.get("decision") or obj.get("state") or obj.get("final_action"))
        if "BUY" in s and "SELL" not in s:
            return "BUY"
        if "SELL" in s and "BUY" not in s:
            return "SELL"
    probs=result.get("probabilities") or {}
    up=_num(probs.get("up")) or 0
    down=_num(probs.get("down")) or 0
    if up-down>=10:
        return "BUY"
    if down-up>=10:
        return "SELL"
    if candles and len(candles)>=4:
        a=_num(candles[-4].get("open"))
        b=_num(candles[-1].get("close"))
        if a is not None and b is not None:
            if b>a: return "BUY"
            if b<a: return "SELL"
    return "NEUTRAL"

def _levels(result, direction):
    pp=result.get("pro_panel") or {}
    np=result.get("next_plan") or {}
    pl=result.get("plan_lock") or {}
    se=result.get("scalp_entry") or {}
    tr=result.get("trade_readiness") or {}
    mm=result.get("market_map") or {}
    tm=mm.get("trade_map") or {}
    sw=mm.get("switch_levels") or {}
    buy_above=_num(pl.get("locked_buy_above") or pp.get("buy_above") or se.get("buy_above") or sw.get("buy_switch"))
    sell_below=_num(pl.get("locked_sell_below") or pp.get("sell_below") or se.get("sell_below") or sw.get("sell_switch"))
    entry=_num(pl.get("locked_entry") or pp.get("entry") or np.get("continuation_trigger"))
    if entry is None:
        entry = buy_above if direction=="BUY" else sell_below if direction=="SELL" else None
    stop=_num(pl.get("locked_stop") or pp.get("stop_or_cancel") or np.get("stop") or tr.get("stop_loss") or tm.get("stop_loss") or tr.get("cancel_level") or tm.get("cancel_level"))
    target=_num(pl.get("locked_target") or pp.get("target") or np.get("target") or tr.get("tp1") or tm.get("tp1_partial_close") or tr.get("tp2") or tm.get("tp2"))
    return {"buy_above":buy_above,"sell_below":sell_below,"entry":entry,"stop":stop,"target":target}

def _rr(sym, entry, stop, target):
    risk=_moves(sym, entry, stop) if entry is not None and stop is not None else None
    reward=_moves(sym, entry, target) if entry is not None and target is not None else None
    rr=(reward/risk) if reward is not None and risk and risk>0 else None
    return risk,reward,rr

def _condition(result):
    if (result.get("news") or {}).get("mode") == "NEWS_WAIT":
        return "NEWS_RISK","News is too close."
    if (result.get("regime_guard") or {}).get("mode") == "BLOCK_TRADE":
        return "BAD_MARKET","Market condition blocks trade."
    if result.get("direction_unstable") or (result.get("direction_lock") or {}).get("flip_blocked"):
        return "CHOPPY","Direction changed too quickly."
    return "TRADABLE","Market is tradable."

def _strategy(sym,result,candles,direction):
    price=_num(result.get("price"))
    last=_last_candle(sym,candles)
    rrng=_recent_range(candles)
    fs=result.get("fast_start") or {}
    se=result.get("scalp_entry") or {}
    np=result.get("next_plan") or {}
    tl=result.get("trigger_lock") or {}
    mc=result.get("move_completion") or {}
    confirm=float(os.getenv("STRATEGY_CONFIRM_BODY_MOVES","8"))

    name="NO STRATEGY"
    grade="C"
    reason="No clean professional setup yet."

    if direction in ["BUY","SELL"] and np.get("continuation_trigger"):
        name=f"PULLBACK CONTINUATION {direction}"
        grade="C"
        reason="Plan exists. Wait for trigger."
        if last.get("direction")==direction and last.get("body_moves",0)>=confirm:
            grade="B"
            reason="Continuation started after plan."

    if "CONFIRMED" in _upper(tl.get("state")) and direction in ["BUY","SELL"]:
        name=f"BREAK / RETEST {direction}"
        grade="A"
        reason="Locked trigger confirmed."

    if fs.get("allowed") and direction in ["BUY","SELL"]:
        name=f"FAST SCALP MOMENTUM {direction}"
        grade="B"
        reason="Fast start allowed with small-risk rules."

    if se.get("allowed") and direction in ["BUY","SELL"]:
        name=f"SCALP CONTINUATION {direction}"
        grade="B"
        reason="Scalp entry passed risk filter."

    if rrng and last and price is not None:
        if last.get("high") is not None and last["high"]>rrng["high"] and last.get("close") is not None and last["close"]<rrng["high"]:
            name="LIQUIDITY SWEEP SELL"; grade="B"; direction="SELL"; reason="Swept recent high and closed back below."
        if last.get("low") is not None and last["low"]<rrng["low"] and last.get("close") is not None and last["close"]>rrng["low"]:
            name="LIQUIDITY SWEEP BUY"; grade="B"; direction="BUY"; reason="Swept recent low and closed back above."
        top=_moves(sym,price,rrng["high"])
        bottom=_moves(sym,price,rrng["low"])
        if top is not None and top<=15 and last.get("direction")=="SELL":
            name="RANGE TOP SELL"; grade="B"; direction="SELL"; reason="Rejected range top."
        if bottom is not None and bottom<=15 and last.get("direction")=="BUY":
            name="RANGE BOTTOM BUY"; grade="B"; direction="BUY"; reason="Rejected range bottom."

    if mc.get("block_entry") and grade!="C":
        grade="C"
        reason="Move may already be extended. Treat as plan only."

    return name,grade,reason,direction

def apply_strategy_permission(result, candles=None):
    if result.get("status")!="live":
        return result
    candles=candles or []
    sym=normalize(result.get("asset"))
    price=_num(result.get("price"))
    direction=_direction(result,candles)
    cond,cond_reason=_condition(result)
    strategy,grade,reason,direction=_strategy(sym,result,candles,direction)
    lv=_levels(result,direction)
    risk,reward,rr=_rr(sym,lv.get("entry"),lv.get("stop"),lv.get("target"))

    mode=os.getenv("STRATEGY_MODE","balanced").lower()
    if mode=="aggressive":
        scalp_min_rr=float(os.getenv("STRATEGY_SCALP_MIN_RR","0.8")); scalp_max_risk=float(os.getenv("STRATEGY_SCALP_MAX_RISK_MOVES","25")); scalp_min_reward=float(os.getenv("STRATEGY_SCALP_MIN_REWARD_MOVES","10")); trade_min_rr=float(os.getenv("STRATEGY_TRADE_MIN_RR","1.0"))
    elif mode=="safe":
        scalp_min_rr=float(os.getenv("STRATEGY_SCALP_MIN_RR","1.0")); scalp_max_risk=float(os.getenv("STRATEGY_SCALP_MAX_RISK_MOVES","18")); scalp_min_reward=float(os.getenv("STRATEGY_SCALP_MIN_REWARD_MOVES","15")); trade_min_rr=float(os.getenv("STRATEGY_TRADE_MIN_RR","1.3"))
    else:
        scalp_min_rr=float(os.getenv("STRATEGY_SCALP_MIN_RR","0.9")); scalp_max_risk=float(os.getenv("STRATEGY_SCALP_MAX_RISK_MOVES","22")); scalp_min_reward=float(os.getenv("STRATEGY_SCALP_MIN_REWARD_MOVES","12")); trade_min_rr=float(os.getenv("STRATEGY_TRADE_MIN_RR","1.15"))

    blockers=[]
    if cond!="TRADABLE": blockers.append(cond_reason)
    if risk is None or reward is None or rr is None: blockers.append("Risk/reward is not clear.")

    decision="PLAN ONLY — DO NOT ENTER"; permission="PLAN_ONLY"; final_reason=reason
    if blockers:
        decision="NO TRADE"; permission="NO_TRADE"; final_reason=blockers[0]
    elif grade=="A" and rr>=trade_min_rr:
        decision=f"TRADE NOW {direction}"; permission="TRADE_NOW"; final_reason=reason
    elif grade in ["A","B"] and rr>=scalp_min_rr and risk<=scalp_max_risk and reward>=scalp_min_reward:
        decision=f"SCALP NOW {direction}"; permission="SCALP_NOW"; final_reason=reason
    elif strategy=="NO STRATEGY":
        decision="NO TRADE"; permission="NO_STRATEGY"; final_reason="No professional strategy detected."
    else:
        final_reason="Strategy exists but not enough for entry yet."

    report={
        "system":"EdgeFlow FX Pro",
        "decision":decision,"permission":permission,"strategy":strategy,"setup_grade":grade,
        "direction":direction,"market_condition":cond,"reason":final_reason,
        "current_price":price,"entry":lv.get("entry"),"buy_above":lv.get("buy_above"),"sell_below":lv.get("sell_below"),
        "stop":lv.get("stop"),"target":lv.get("target"),
        "risk_moves":round(risk,1) if risk is not None else None,
        "reward_moves":round(reward,1) if reward is not None else None,
        "rr":round(rr,2) if rr is not None else None,
        "mode":mode,
        "rule":"A+ = TRADE NOW, B = SCALP NOW, C = PLAN ONLY, bad market = NO TRADE.",
        "moves_note":"Moves = last digit movement. 10 moves = 1 pip on EUR/USD and GBP/USD.",
        "time":_now().isoformat()
    }
    result["strategy_permission"]=report
    _MEM[sym]=report

    pp=result.get("pro_panel") or {}
    pp.update({
        "decision":decision,"decision_type":permission,"direction":direction,"reason":final_reason,
        "current_price":price,"buy_above":lv.get("buy_above"),"sell_below":lv.get("sell_below"),
        "entry":lv.get("entry"),"stop_or_cancel":lv.get("stop"),"target":lv.get("target"),
        "risk_moves":report["risk_moves"],"reward_moves":report["reward_moves"],"rr":report["rr"]
    })
    result["pro_panel"]=pp
    result["final_action"]=decision
    result["entry_permission"]="EDGEFLOW_TRADE_NOW" if permission=="TRADE_NOW" else "EDGEFLOW_SCALP_NOW_SMALL_RISK" if permission=="SCALP_NOW" else "NO_ENTRY"

    fd=result.get("final_decision") or {}
    if fd:
        fd["final_action"]=decision; fd["command"]=decision; fd["entry_permission"]=result["entry_permission"]; fd["summary"]=final_reason
        result["final_decision"]=fd
    return result

def strategy_permission_report():
    return {"strategy_permission":list(_MEM.values())}
