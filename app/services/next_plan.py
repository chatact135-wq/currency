
from datetime import datetime, timezone
import os
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

def _step(sym): return ASSETS[sym]["pip"]/10

def _moves(sym,a,b):
    try: return abs(float(a)-float(b))/_step(sym)
    except Exception: return None

def _price(sym, base, moves, mode, direction):
    if base is None: return None
    step = _step(sym)
    # mode "back" = pullback against direction
    # mode "forward" = continuation with direction
    if direction == "BUY":
        return round(base - moves*step, 5) if mode == "back" else round(base + moves*step, 5)
    if direction == "SELL":
        return round(base + moves*step, 5) if mode == "back" else round(base - moves*step, 5)
    return None

def _direction(result):
    for obj in [
        result.get("pro_panel") or {},
        result.get("move_completion") or {},
        result.get("master_decision") or {},
        result.get("scalp_entry") or {},
        result.get("fast_start") or {},
        result.get("trade_readiness") or {},
    ]:
        d=_upper(obj.get("direction"))
        if d in ["BUY","SELL"]: return d
        s=_upper(obj.get("decision") or obj.get("state") or obj.get("final_action"))
        if "BUY" in s and "SELL" not in s: return "BUY"
        if "SELL" in s and "BUY" not in s: return "SELL"
    probs=result.get("probabilities") or {}
    up=_num(probs.get("up")) or 0
    down=_num(probs.get("down")) or 0
    if up-down>=10: return "BUY"
    if down-up>=10: return "SELL"
    return "NEUTRAL"

def _levels(result):
    se=result.get("scalp_entry") or {}
    pp=result.get("pro_panel") or {}
    tr=result.get("trade_readiness") or {}
    mm=result.get("market_map") or {}
    tm=mm.get("trade_map") or {}
    sw=mm.get("switch_levels") or {}
    return {
        "buy_above": _num(pp.get("buy_above") or se.get("buy_above") or sw.get("buy_switch")),
        "sell_below": _num(pp.get("sell_below") or se.get("sell_below") or sw.get("sell_switch")),
        "stop": _num(pp.get("stop_or_cancel") or tr.get("stop_loss") or tm.get("stop_loss") or tr.get("cancel_level") or tm.get("cancel_level")),
        "target": _num(pp.get("target") or tr.get("tp1") or tm.get("tp1_partial_close") or tr.get("tp2") or tm.get("tp2")),
    }

def apply_next_plan(result):
    if result.get("status") != "live":
        return result

    sym=normalize(result.get("asset"))
    price=_num(result.get("price"))
    direction=_direction(result)
    mc=result.get("move_completion") or {}
    cont=result.get("continuation_entry") or {}
    lv=_levels(result)

    pull_min=float(os.getenv("NEXT_PLAN_PULLBACK_MIN_MOVES","12"))
    pull_max=float(os.getenv("NEXT_PLAN_PULLBACK_MAX_MOVES","28"))
    trigger_buffer=float(os.getenv("NEXT_PLAN_TRIGGER_BUFFER_MOVES","5"))
    stop_moves=float(os.getenv("NEXT_PLAN_STOP_MOVES","18"))
    target_moves=float(os.getenv("NEXT_PLAN_TARGET_MOVES","25"))
    missed_threshold=float(os.getenv("NEXT_PLAN_MISSED_MOVE_MOVES","55"))

    moved=_num(mc.get("moved_moves"))
    pullback=_num(mc.get("pullback_from_extreme_moves")) or 0

    state="NO NEXT PLAN"
    instruction="No clear direction yet."
    immediate_entry_allowed=False

    pullback_low=None
    pullback_high=None
    continuation_trigger=None
    stop=None
    target=None

    if direction in ["BUY","SELL"] and price is not None:
        # Always calculate a future plan, not only when pullback already happened.
        a=_price(sym, price, pull_min, "back", direction)
        b=_price(sym, price, pull_max, "back", direction)
        pullback_low=min(a,b) if a is not None and b is not None else None
        pullback_high=max(a,b) if a is not None and b is not None else None

        # If already pulled back enough, trigger is close to current price with direction.
        # If not pulled back, trigger is after the pullback zone: use the near edge plus buffer.
        if pullback >= pull_min and pullback <= pull_max:
            continuation_trigger=_price(sym, price, trigger_buffer, "forward", direction)
            state=f"WAIT CONTINUATION {direction}"
            instruction=f"Price already pulled back {round(pullback,1)} moves. Wait for {direction} continuation trigger."
        elif pullback > pull_max:
            continuation_trigger=None
            state=f"{direction} PULLBACK TOO DEEP - WAIT NEW SETUP"
            instruction="Price came back too much. Continuation is not clean."
        else:
            # future trigger after price comes into pullback zone and turns again
            base_for_trigger = pullback_high if direction=="BUY" else pullback_low
            continuation_trigger=_price(sym, base_for_trigger, trigger_buffer, "forward", direction)
            state=f"{direction} NEXT PLAN - WAIT PULLBACK"
            instruction=f"Do not chase. Wait price to enter pullback zone, then watch continuation trigger."

        if continuation_trigger is not None:
            stop=_price(sym, continuation_trigger, stop_moves, "back", direction)
            target=_price(sym, continuation_trigger, target_moves, "forward", direction)

        if moved is not None and moved >= missed_threshold:
            state=f"{direction} MOVE MISSED - NEXT PLAN READY" if "TOO DEEP" not in state else state
            if "TOO DEEP" not in state:
                instruction=f"{direction} move already moved {round(moved,1)} moves. Do not chase; use the next pullback/continuation plan only."

    risk=_moves(sym, continuation_trigger, stop) if continuation_trigger is not None and stop is not None else None
    reward=_moves(sym, continuation_trigger, target) if continuation_trigger is not None and target is not None else None
    rr=(reward/risk) if reward is not None and risk and risk>0 else None

    report={
        "state":state,
        "direction":direction,
        "current_price":price,
        "moved_moves":moved,
        "pullback_from_extreme_moves":pullback,
        "pullback_zone":[pullback_low,pullback_high] if pullback_low is not None and pullback_high is not None else None,
        "continuation_trigger":continuation_trigger,
        "stop":stop,
        "target":target,
        "risk_moves":round(risk,1) if risk is not None else None,
        "reward_moves":round(reward,1) if reward is not None else None,
        "rr":round(rr,2) if rr is not None else None,
        "instruction":instruction,
        "immediate_entry_allowed":immediate_entry_allowed,
        "moves_note":"Moves = last digit movement. 10 moves = 1 pip on EUR/USD and GBP/USD.",
        "time":_now().isoformat()
    }

    result["next_plan"]=report
    _MEM[sym]=report

    # Make pro panel show next plan when decision is missed / do not enter due to extended move
    pp=result.get("pro_panel") or {}
    pp_dec=_upper(pp.get("decision"))
    if pp and (("DO NOT ENTER" in pp_dec and moved is not None and moved >= missed_threshold) or "MOVE MISSED" in _upper((result.get("continuation_entry") or {}).get("state"))):
        pp["decision"]=state
        pp["decision_type"]="NEXT_PLAN"
        pp["reason"]=instruction
        pp["entry"]=continuation_trigger
        pp["stop_or_cancel"]=stop
        pp["target"]=target
        pp["risk_moves"]=report["risk_moves"]
        pp["reward_moves"]=report["reward_moves"]
        pp["rr"]=report["rr"]
        result["pro_panel"]=pp
        result["final_action"]=state
        result["entry_permission"]="NO_ENTRY_NEXT_PLAN_READY"

    return result

def next_plan_report():
    return {"next_plan":list(_MEM.values())}
