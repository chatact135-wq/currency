
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

def _from_moves(sym, price, moves, direction):
    if price is None: return None
    if direction=="BUY": return round(price - moves*_step(sym), 5)
    if direction=="SELL": return round(price + moves*_step(sym), 5)
    return None

def _add_moves(sym, price, moves, direction):
    if price is None: return None
    if direction=="BUY": return round(price + moves*_step(sym), 5)
    if direction=="SELL": return round(price - moves*_step(sym), 5)
    return None

def _direction(result):
    for obj in [result.get("pro_panel") or {}, result.get("move_completion") or {}, result.get("master_decision") or {}, result.get("fast_start") or {}, result.get("scalp_entry") or {}]:
        d=_upper(obj.get("direction"))
        if d in ["BUY","SELL"]: return d
        s=_upper(obj.get("decision") or obj.get("state"))
        if "BUY" in s and "SELL" not in s: return "BUY"
        if "SELL" in s and "BUY" not in s: return "SELL"
    probs=result.get("probabilities") or {}
    up=_num(probs.get("up")) or 0
    down=_num(probs.get("down")) or 0
    if up-down>=10: return "BUY"
    if down-up>=10: return "SELL"
    return "NEUTRAL"

def apply_continuation_entry(result):
    if result.get("status")!="live":
        return result

    sym=normalize(result.get("asset"))
    price=_num(result.get("price"))
    direction=_direction(result)
    mc=result.get("move_completion") or {}

    min_missed=float(os.getenv("MISSED_MOVE_MIN_MOVES","60"))
    pull_min=float(os.getenv("CONTINUATION_PULLBACK_MIN_MOVES","12"))
    pull_max=float(os.getenv("CONTINUATION_PULLBACK_MAX_MOVES","28"))
    buffer=float(os.getenv("CONTINUATION_TRIGGER_BUFFER_MOVES","5"))
    stop_moves=float(os.getenv("CONTINUATION_STOP_MOVES","18"))
    target_moves=float(os.getenv("CONTINUATION_TARGET_MOVES","25"))

    moved=_num(mc.get("moved_moves"))
    pullback=_num(mc.get("pullback_from_extreme_moves")) or 0

    state="NO CONTINUATION SETUP"
    reason="No missed move or continuation setup."
    action="WAIT"
    pullback_zone=None
    trigger=None
    stop=None
    target=None

    if direction in ["BUY","SELL"] and moved is not None and moved>=min_missed:
        state=f"{direction} MOVE MISSED - DO NOT CHASE"
        reason=f"{direction} already moved {round(moved,1)} moves. Do not enter late."
        action="WAIT PULLBACK / CONTINUATION"
        a=_from_moves(sym, price, pull_min, direction)
        b=_from_moves(sym, price, pull_max, direction)
        if a is not None and b is not None:
            pullback_zone=[min(a,b), max(a,b)]
        if pullback>=pull_min and pullback<=pull_max:
            state=f"WAIT CONTINUATION {direction}"
            reason=f"Move was missed, but price came back {round(pullback,1)} moves. Wait continuation trigger."
            action=f"{direction} only if continuation trigger breaks."
            trigger=_add_moves(sym, price, buffer, direction)
            stop=_from_moves(sym, price, stop_moves, direction)
            target=_add_moves(sym, price, target_moves, direction)
        elif pullback>pull_max:
            state=f"{direction} MOVE MAY BE REVERSING"
            reason="Price came back too much after the move. Continuation is not clean."
            action="WAIT NEW SETUP"

    report={
        "state":state,
        "direction":direction,
        "current_price":price,
        "moved_moves":moved,
        "pullback_from_extreme_moves":pullback,
        "pullback_zone":pullback_zone,
        "continuation_trigger":trigger,
        "stop":stop,
        "target":target,
        "reason":reason,
        "action":action,
        "moves_note":"Moves = last digit movement. 10 moves = 1 pip on EUR/USD and GBP/USD.",
        "time":_now().isoformat()
    }

    result["continuation_entry"]=report
    _MEM[sym]=report

    if "MOVE MISSED" in state or "WAIT CONTINUATION" in state or "MAY BE REVERSING" in state:
        pp=result.get("pro_panel") or {}
        if pp:
            pp["decision"]=state
            pp["decision_type"]="MISSED_MOVE_CONTINUATION"
            pp["reason"]=reason
            pp["current_price"]=price
            pp["entry"]=trigger
            pp["stop_or_cancel"]=stop
            pp["target"]=target
            pp["risk_moves"]=stop_moves if stop else None
            pp["reward_moves"]=target_moves if target else None
            pp["rr"]=round(target_moves/stop_moves,2) if stop and target and stop_moves else None
            result["pro_panel"]=pp
        result["final_action"]=state
        result["entry_permission"]="NO_ENTRY_WAIT_CONTINUATION"

    return result

def continuation_report():
    return {"continuation":list(_MEM.values())}
