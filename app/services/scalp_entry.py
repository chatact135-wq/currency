
import os
from datetime import datetime, timezone
from app.services.market import ASSETS, normalize

_MEM = {}

def _now(): return datetime.now(timezone.utc)

def _num(v):
    try:
        if v is None: return None
        return float(v)
    except Exception:
        return None

def _upper(v): return str(v or "").upper()

def _moves(sym,a,b):
    try: return abs(float(a)-float(b))/(ASSETS[sym]["pip"]/10)
    except Exception: return None

def _pips(sym,a,b):
    try: return abs(float(a)-float(b))/ASSETS[sym]["pip"]
    except Exception: return None

def _dist(sym, price, level):
    return {
        "level": level,
        "moves": round(_moves(sym,price,level),1) if price is not None and level is not None else None,
        "pips": round(_pips(sym,price,level),1) if price is not None and level is not None else None,
    }

def _levels(result):
    mm=result.get("market_map") or {}
    sw=mm.get("switch_levels") or {}
    tm=mm.get("trade_map") or {}
    tr=result.get("trade_readiness") or {}
    pp=result.get("price_position") or {}

    buy_above=_num(sw.get("buy_switch"))
    sell_below=_num(sw.get("sell_switch"))

    # fallbacks for display when one side is missing
    if buy_above is None:
        buy_above=_num(tr.get("safe_entry") or tm.get("safe_entry") or pp.get("confirmation_level"))
    if sell_below is None:
        sell_below=_num(tr.get("cancel_level") or tm.get("cancel_level") or tr.get("entry") or tm.get("aggressive_entry"))

    return {
        "buy_above": buy_above,
        "sell_below": sell_below,
        "cancel": _num(tr.get("cancel_level") or tm.get("cancel_level")),
        "sl": _num(tr.get("stop_loss") or tm.get("stop_loss")),
        "tp1": _num(tr.get("tp1") or tm.get("tp1_partial_close")),
        "tp2": _num(tr.get("tp2") or tm.get("tp2")),
    }

def _direction(result):
    for obj in [result.get("master_decision") or {}, result.get("fast_start") or {}, result.get("early_risk") or {}, result.get("trade_readiness") or {}, result.get("price_position") or {}]:
        d=_upper(obj.get("direction"))
        if d in ["BUY","SELL"]: return d
        s=_upper(obj.get("state"))
        if "BUY" in s and "SELL" not in s: return "BUY"
        if "SELL" in s and "BUY" not in s: return "SELL"
    probs=result.get("probabilities") or {}
    up=_num(probs.get("up")) or 0
    down=_num(probs.get("down")) or 0
    if up-down>=10: return "BUY"
    if down-up>=10: return "SELL"
    return "NEUTRAL"

def _target(direction, price, lv):
    if price is None: return None
    if direction=="BUY":
        for t in [lv.get("tp1"), lv.get("tp2")]:
            if t is not None and t>price: return t
    if direction=="SELL":
        for t in [lv.get("tp1"), lv.get("tp2")]:
            if t is not None and t<price: return t
    return None

def apply_scalp_entry(result):
    if result.get("status")!="live": return result

    sym=normalize(result.get("asset"))
    price=_num(result.get("price"))
    direction=_direction(result)
    lv=_levels(result)
    buy_above=lv.get("buy_above")
    sell_below=lv.get("sell_below")

    min_reward=float(os.getenv("SCALP_MIN_REWARD_MOVES","15"))
    max_risk=float(os.getenv("SCALP_MAX_RISK_MOVES","20"))
    min_rr=float(os.getenv("SCALP_MIN_RR","1.0"))
    max_dist=float(os.getenv("SCALP_MAX_DISTANCE_TO_TRIGGER_MOVES","25"))

    position="UNKNOWN"
    if price is not None and buy_above is not None and sell_below is not None:
        if price>=buy_above: position="ABOVE BUY LEVEL"
        elif price<=sell_below: position="BELOW SELL LEVEL"
        else: position="BETWEEN BUY ABOVE AND SELL BELOW"

    safe_entry = result.get("entry_permission") in ["VALIDATED_ENTRY_ALLOWED","TRIGGER_LOCK_CONFIRMED","ENTRY_ALLOWED"]
    trigger=buy_above if direction=="BUY" else sell_below if direction=="SELL" else None
    trigger_dist=_moves(sym, price, trigger) if price is not None and trigger is not None else None

    target=_target(direction, price, lv)
    risk_level=lv.get("cancel") or lv.get("sl")
    reward=_moves(sym, price, target) if price is not None and target is not None else None
    risk=_moves(sym, price, risk_level) if price is not None and risk_level is not None else None
    rr=(reward/risk) if reward is not None and risk and risk>0 else None

    reasons=[]
    if direction not in ["BUY","SELL"]: reasons.append("No clear scalp direction.")
    if trigger_dist is None: reasons.append("Trigger distance not clear.")
    elif trigger_dist>max_dist: reasons.append(f"Trigger too far: {round(trigger_dist,1)} moves. Max {max_dist}.")
    if reward is None: reasons.append("Target not clear.")
    elif reward<min_reward: reasons.append(f"Target too close: {round(reward,1)} moves. Need {min_reward}.")
    if risk is None: reasons.append("Risk/cancel not clear.")
    elif risk>max_risk: reasons.append(f"Risk too big: {round(risk,1)} moves. Max {max_risk}.")
    if rr is None: reasons.append("Reward/risk not clear.")
    elif rr<min_rr: reasons.append(f"Reward/risk weak: {round(rr,2)}. Need {min_rr}.")
    if result.get("direction_unstable"): reasons.append("Direction unstable.")
    if (result.get("move_completion") or {}).get("block_entry"): reasons.append("Move already extended/finished.")
    if (result.get("final_guard") or {}).get("blocked"): reasons.append("Final safety check blocked.")
    if (result.get("news") or {}).get("mode")=="NEWS_WAIT": reasons.append("News too close.")

    allowed = len(reasons)==0
    state = f"SCALP {direction} ALLOWED" if allowed and direction in ["BUY","SELL"] else (f"SCALP {direction} BLOCKED" if direction in ["BUY","SELL"] else "SCALP BLOCKED")
    simple = "Scalp entry allowed with small risk only." if allowed else "Scalp entry blocked. Do not enter from WATCH only."

    report={
        "state":state, "allowed":allowed, "direction":direction,
        "safe_entry":"YES" if safe_entry else "NO",
        "position":position, "current_price":price,
        "buy_above":buy_above, "sell_below":sell_below,
        "distance_to_buy":_dist(sym, price, buy_above),
        "distance_to_sell":_dist(sym, price, sell_below),
        "trigger_distance_moves":round(trigger_dist,1) if trigger_dist is not None else None,
        "target":target, "risk_level":risk_level,
        "reward_moves":round(reward,1) if reward is not None else None,
        "risk_moves":round(risk,1) if risk is not None else None,
        "rr":round(rr,2) if rr is not None else None,
        "simple_message":simple, "reasons":reasons,
        "moves_note":"Moves = last digit movement. 10 moves = 1 pip on EUR/USD and GBP/USD.",
        "time":_now().isoformat()
    }
    result["scalp_entry"]=report
    _MEM[sym]=report

    if allowed and not safe_entry:
        result["entry_permission"]="SCALP_ENTRY_ALLOWED_SMALL_RISK"
        result["final_action"]=state
        fd=result.get("final_decision") or {}
        if fd:
            fd["final_action"]=state
            fd["command"]=state
            fd["entry_permission"]="SCALP_ENTRY_ALLOWED_SMALL_RISK"
            fd["summary"]=simple
            result["final_decision"]=fd
    return result

def scalp_entry_report():
    return {"scalp_entry":list(_MEM.values())}
