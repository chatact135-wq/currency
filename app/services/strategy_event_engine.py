
from datetime import datetime, timezone
import os
from app.services.market import ASSETS, normalize

_LAST = {}
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

def _add_moves(sym, price, moves, direction):
    if price is None:
        return None
    step = _step(sym)
    if direction == "BUY":
        return round(price + moves * step, 5)
    if direction == "SELL":
        return round(price - moves * step, 5)
    return None

def _back_moves(sym, price, moves, direction):
    if price is None:
        return None
    step = _step(sym)
    if direction == "BUY":
        return round(price - moves * step, 5)
    if direction == "SELL":
        return round(price + moves * step, 5)
    return None

def _levels(result):
    pc = result.get("permission_clarity") or {}
    pp = result.get("pro_panel") or {}
    sp = result.get("strategy_permission") or {}
    ba = result.get("break_activation") or {}
    se = result.get("scalp_entry") or {}
    return {
        "buy_above": _num(pc.get("watch_buy_above") or sp.get("buy_above") or pp.get("buy_above") or se.get("buy_above")),
        "sell_below": _num(pc.get("watch_sell_below") or sp.get("sell_below") or pp.get("sell_below") or se.get("sell_below")),
        "old_entry": _num(sp.get("entry") or pp.get("entry") or ba.get("break_level")),
        "old_stop": _num(sp.get("stop") or pp.get("stop_or_cancel")),
        "old_target": _num(sp.get("target") or pp.get("target")),
    }

def _last_candle(sym, candles):
    if not candles:
        return {}
    c = candles[-1]
    o=_num(c.get("open")); h=_num(c.get("high")); l=_num(c.get("low")); cl=_num(c.get("close"))
    if None in [o,h,l,cl]:
        return {}
    d = "BUY" if cl > o else "SELL" if cl < o else "NEUTRAL"
    return {
        "open": o, "high": h, "low": l, "close": cl,
        "direction": d,
        "body_moves": round(_moves(sym,o,cl) or 0,1),
        "range_moves": round(_moves(sym,l,h) or 0,1)
    }

def _recent_direction(sym, candles, lookback=4):
    if not candles or len(candles) < lookback:
        return "NEUTRAL", 0
    a=_num(candles[-lookback].get("open"))
    b=_num(candles[-1].get("close"))
    if a is None or b is None:
        return "NEUTRAL", 0
    moved=_moves(sym,a,b) or 0
    if b>a: return "BUY", round(moved,1)
    if b<a: return "SELL", round(moved,1)
    return "NEUTRAL", round(moved,1)

def _velocity(sym, asset, price):
    now=_now()
    last=_LAST.get(asset)
    _LAST[asset] = {"price": price, "time": now}
    if not last or price is None or last.get("price") is None:
        return None, None
    secs=max(1, (now-last["time"]).total_seconds())
    mv=_moves(sym,last["price"],price)
    if mv is None:
        return None, secs
    return round(mv/secs,3), secs

def _rr(sym, entry, stop, target):
    risk=_moves(sym,entry,stop) if entry is not None and stop is not None else None
    reward=_moves(sym,entry,target) if entry is not None and target is not None else None
    rr=(reward/risk) if reward is not None and risk and risk>0 else None
    return risk,reward,rr

def apply_strategy_event_engine(result, candles=None):
    if result.get("status") != "live":
        return result

    candles = candles or []
    asset = normalize(result.get("asset"))
    sym = asset
    price = _num(result.get("price"))
    lv = _levels(result)
    last = _last_candle(sym, candles)
    recent_dir, recent_moves = _recent_direction(sym, candles, 4)
    velocity, secs = _velocity(sym, asset, price)

    impulse_candle_moves = float(os.getenv("EVENT_IMPULSE_CANDLE_MOVES","12"))
    impulse_recent_moves = float(os.getenv("EVENT_IMPULSE_RECENT_MOVES","25"))
    fast_velocity = float(os.getenv("EVENT_FAST_VELOCITY_MOVES_PER_SEC","0.6"))
    prebreak_distance = float(os.getenv("EVENT_PREBREAK_DISTANCE_MOVES","12"))
    late_after_break = float(os.getenv("EVENT_LATE_AFTER_BREAK_MOVES","35"))
    scalp_stop_moves = float(os.getenv("EVENT_SCALP_STOP_MOVES","18"))
    scalp_target_moves = float(os.getenv("EVENT_SCALP_TARGET_MOVES","25"))
    trade_target_moves = float(os.getenv("EVENT_TRADE_TARGET_MOVES","35"))
    min_scalp_rr = float(os.getenv("EVENT_MIN_SCALP_RR","1.0"))
    min_trade_rr = float(os.getenv("EVENT_MIN_TRADE_RR","1.25"))

    buy_above = lv.get("buy_above")
    sell_below = lv.get("sell_below")

    broke_buy = price is not None and buy_above is not None and price >= buy_above
    broke_sell = price is not None and sell_below is not None and price <= sell_below

    dist_to_buy = _moves(sym, price, buy_above) if price is not None and buy_above is not None else None
    dist_to_sell = _moves(sym, price, sell_below) if price is not None and sell_below is not None else None

    impulse_dir = "NEUTRAL"
    impulse_strength = 0

    if last.get("body_moves",0) >= impulse_candle_moves:
        impulse_dir = last.get("direction","NEUTRAL")
        impulse_strength = max(impulse_strength, last.get("body_moves",0))

    if recent_moves >= impulse_recent_moves and recent_dir in ["BUY","SELL"]:
        impulse_dir = recent_dir
        impulse_strength = max(impulse_strength, recent_moves)

    if velocity is not None and velocity >= fast_velocity:
        # Use recent direction for velocity direction
        if recent_dir in ["BUY","SELL"]:
            impulse_dir = recent_dir
            impulse_strength = max(impulse_strength, round(velocity * max(secs or 1,1),1))

    decision = "NO STRATEGY"
    permission = "NO_ENTRY"
    strategy = "NO STRATEGY"
    reason = "No fast strategy event detected."
    direction = impulse_dir if impulse_dir in ["BUY","SELL"] else "NEUTRAL"
    entry = None
    stop = None
    target = None
    state = "NO EVENT"

    # Event logic
    if broke_buy:
        direction="BUY"
        after=_moves(sym,buy_above,price) or 0
        if after > late_after_break:
            state="MOVE MISSED AFTER BREAK"
            strategy="BREAKOUT BUY MISSED"
            decision="BUY MOVE MISSED — DO NOT CHASE"
            reason=f"Price broke BUY level and already moved {round(after,1)} moves after break."
        elif impulse_dir=="BUY":
            state="ACTIVE FAST BREAKOUT"
            strategy="FAST IMPULSE BREAKOUT BUY"
            entry=price
            stop=_back_moves(sym, entry, scalp_stop_moves, "BUY")
            target=_add_moves(sym, entry, scalp_target_moves, "BUY")
            risk,reward,rr=_rr(sym,entry,stop,target)
            if rr is not None and rr >= min_scalp_rr:
                decision="SCALP NOW BUY"
                permission="EVENT_SCALP_NOW"
                reason=f"BUY break + fast impulse detected. Risk {round(risk,1)} moves, reward {round(reward,1)} moves."
            else:
                decision="PLAN ONLY — DO NOT ENTER"
                reason="Break detected but event risk/reward is not approved."
        else:
            state="BREAK WITHOUT IMPULSE"
            strategy="BREAKOUT BUY WAIT CONFIRM"
            decision="BREAK BUY — WAIT IMPULSE CONFIRMATION"
            reason="Price broke BUY level, but fast impulse is not confirmed yet."

    elif broke_sell:
        direction="SELL"
        after=_moves(sym,sell_below,price) or 0
        if after > late_after_break:
            state="MOVE MISSED AFTER BREAK"
            strategy="BREAKOUT SELL MISSED"
            decision="SELL MOVE MISSED — DO NOT CHASE"
            reason=f"Price broke SELL level and already moved {round(after,1)} moves after break."
        elif impulse_dir=="SELL":
            state="ACTIVE FAST BREAKOUT"
            strategy="FAST IMPULSE BREAKOUT SELL"
            entry=price
            stop=_back_moves(sym, entry, scalp_stop_moves, "SELL")
            target=_add_moves(sym, entry, scalp_target_moves, "SELL")
            risk,reward,rr=_rr(sym,entry,stop,target)
            if rr is not None and rr >= min_scalp_rr:
                decision="SCALP NOW SELL"
                permission="EVENT_SCALP_NOW"
                reason=f"SELL break + fast impulse detected. Risk {round(risk,1)} moves, reward {round(reward,1)} moves."
            else:
                decision="PLAN ONLY — DO NOT ENTER"
                reason="Break detected but event risk/reward is not approved."
        else:
            state="BREAK WITHOUT IMPULSE"
            strategy="BREAKOUT SELL WAIT CONFIRM"
            decision="BREAK SELL — WAIT IMPULSE CONFIRMATION"
            reason="Price broke SELL level, but fast impulse is not confirmed yet."

    else:
        # Pre-break momentum: not entry, but smarter warning
        if impulse_dir=="BUY" and dist_to_buy is not None and dist_to_buy <= prebreak_distance:
            state="PRE-BREAK MOMENTUM"
            strategy="PRE-BREAK MOMENTUM BUY"
            decision="PRE-BREAK BUY — WATCH BREAK"
            direction="BUY"
            reason=f"Fast BUY impulse is approaching BUY level. Wait break; do not enter before break."
        elif impulse_dir=="SELL" and dist_to_sell is not None and dist_to_sell <= prebreak_distance:
            state="PRE-BREAK MOMENTUM"
            strategy="PRE-BREAK MOMENTUM SELL"
            decision="PRE-BREAK SELL — WATCH BREAK"
            direction="SELL"
            reason=f"Fast SELL impulse is approaching SELL level. Wait break; do not enter before break."

    if entry is None and decision.startswith("SCALP NOW"):
        entry=price

    risk,reward,rr=_rr(sym,entry,stop,target)

    # Upgrade to trade now if event is strong and bigger target still acceptable
    if decision.startswith("SCALP NOW") and impulse_strength >= float(os.getenv("EVENT_TRADE_STRENGTH_MOVES","35")):
        trade_target = _add_moves(sym, entry, trade_target_moves, direction)
        trisk, treward, trr = _rr(sym, entry, stop, trade_target)
        if trr is not None and trr >= min_trade_rr:
            decision=f"TRADE NOW {direction}"
            permission="EVENT_TRADE_NOW"
            target=trade_target
            risk,reward,rr=trisk,treward,trr
            reason=f"Strong {direction} event detected. Trade target accepted with R/R {round(rr,2)}."

    report={
        "system":"EdgeFlow FX Pro V4",
        "state":state,
        "decision":decision,
        "permission":permission,
        "strategy":strategy,
        "direction":direction,
        "current_price":price,
        "buy_above":buy_above,
        "sell_below":sell_below,
        "distance_to_buy_moves":round(dist_to_buy,1) if dist_to_buy is not None else None,
        "distance_to_sell_moves":round(dist_to_sell,1) if dist_to_sell is not None else None,
        "last_candle_direction":last.get("direction"),
        "last_candle_body_moves":last.get("body_moves"),
        "recent_direction":recent_dir,
        "recent_moves":recent_moves,
        "velocity_moves_per_sec":velocity,
        "impulse_direction":impulse_dir,
        "impulse_strength_moves":round(impulse_strength,1) if impulse_strength is not None else None,
        "entry":entry,
        "stop":stop,
        "target":target,
        "risk_moves":round(risk,1) if risk is not None else None,
        "reward_moves":round(reward,1) if reward is not None else None,
        "rr":round(rr,2) if rr is not None else None,
        "reason":reason,
        "rule":"Real strategy event must detect break + impulse. If move is already far after break, it becomes missed, not entry.",
        "time":_now().isoformat()
    }

    result["strategy_event"] = report
    _MEM[asset]=report

    # Override only when event engine has a meaningful current event.
    if decision != "NO STRATEGY":
        pp=result.get("pro_panel") or {}
        pp.update({
            "decision":decision,
            "decision_type":permission,
            "direction":direction,
            "reason":reason,
            "current_price":price,
            "buy_above":buy_above,
            "sell_below":sell_below,
            "entry":entry if permission in ["EVENT_SCALP_NOW","EVENT_TRADE_NOW"] else "NOT ACTIVE",
            "stop_or_cancel":stop,
            "target":target,
            "risk_moves":report["risk_moves"],
            "reward_moves":report["reward_moves"],
            "rr":report["rr"],
        })
        result["pro_panel"]=pp
        result["final_action"]=decision
        result["entry_permission"]=permission if permission!="NO_ENTRY" else "NO_ENTRY"

        pc=result.get("permission_clarity") or {}
        if pc:
            pc["decision"]=decision
            pc["status"]="ACTIVE ENTRY" if permission in ["EVENT_SCALP_NOW","EVENT_TRADE_NOW"] else "WATCH ONLY — DO NOT ENTER"
            pc["active_entry"]=entry if pc["status"]=="ACTIVE ENTRY" else None
            pc["active_stop"]=stop if pc["status"]=="ACTIVE ENTRY" else None
            pc["active_target"]=target if pc["status"]=="ACTIVE ENTRY" else None
            pc["why_not_active"]=None if pc["status"]=="ACTIVE ENTRY" else reason
            result["permission_clarity"]=pc

    return result

def strategy_events_report():
    return {"strategy_events":list(_MEM.values())}
