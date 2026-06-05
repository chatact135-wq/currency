
import os
from datetime import datetime, timezone
from app.services.market import normalize

_PLAN_LOCKS = {}

def _now(): return datetime.now(timezone.utc)

def _upper(v): return str(v or "").upper()

def _num(v):
    try:
        if v is None: return None
        return float(v)
    except Exception:
        return None

def _direction(result):
    for obj in [result.get("pro_panel") or {}, result.get("next_plan") or {}, result.get("continuation_entry") or {}, result.get("master_decision") or {}]:
        d=_upper(obj.get("direction"))
        if d in ["BUY","SELL"]: return d
        s=_upper(obj.get("decision") or obj.get("state"))
        if "BUY" in s and "SELL" not in s: return "BUY"
        if "SELL" in s and "BUY" not in s: return "SELL"
    return "NEUTRAL"

def _candidate(result):
    pp=result.get("pro_panel") or {}
    np=result.get("next_plan") or {}
    se=result.get("scalp_entry") or {}
    direction=_direction(result)
    entry=_num(pp.get("entry") or np.get("continuation_trigger"))
    buy_above=_num(pp.get("buy_above") or se.get("buy_above"))
    sell_below=_num(pp.get("sell_below") or se.get("sell_below"))
    if entry is None:
        entry = buy_above if direction=="BUY" else sell_below if direction=="SELL" else None
    return {
        "direction":direction,
        "decision":pp.get("decision") or result.get("final_action") or "",
        "entry":entry,
        "buy_above":buy_above,
        "sell_below":sell_below,
        "stop":_num(pp.get("stop_or_cancel") or np.get("stop")),
        "target":_num(pp.get("target") or np.get("target")),
        "risk_moves":_num(pp.get("risk_moves") or np.get("risk_moves")),
        "reward_moves":_num(pp.get("reward_moves") or np.get("reward_moves")),
        "rr":_num(pp.get("rr") or np.get("rr")),
        "reason":pp.get("reason") or np.get("instruction") or ""
    }

def apply_plan_lock(result):
    if result.get("status")!="live":
        return result

    asset=normalize(result.get("asset"))
    cand=_candidate(result)
    direction=cand["direction"]
    now=_now()
    lock_seconds=int(os.getenv("NEXT_PLAN_LOCK_SECONDS","300"))

    if direction not in ["BUY","SELL"] or cand.get("entry") is None:
        result["plan_lock"]={"state":"NO PLAN LOCK","simple_message":"No valid next plan entry to lock."}
        return result

    if (result.get("open_trade") or {}).get("has_open_trade"):
        result["plan_lock"]={"state":"OPEN TRADE MODE","simple_message":"Plan lock disabled while managing open trade."}
        return result

    lock=_PLAN_LOCKS.get(asset)
    if lock:
        age=int((now-lock["created_at"]).total_seconds())
        if age>lock_seconds or lock["direction"]!=direction:
            _PLAN_LOCKS.pop(asset,None)
            lock=None

    if not lock:
        lock=dict(cand)
        lock.update({"asset":asset,"created_at":now,"state":f"{direction} NEXT PLAN LOCKED","blocked_updates":0})
        _PLAN_LOCKS[asset]=lock
    else:
        if cand.get("entry") is not None and cand.get("entry") != lock.get("entry"):
            lock["blocked_updates"]=lock.get("blocked_updates",0)+1

    age=int((now-lock["created_at"]).total_seconds())
    result["plan_lock"]={
        "state":lock["state"],
        "direction":lock["direction"],
        "locked_entry":lock["entry"],
        "locked_buy_above":lock["buy_above"],
        "locked_sell_below":lock["sell_below"],
        "locked_stop":lock["stop"],
        "locked_target":lock["target"],
        "risk_moves":lock["risk_moves"],
        "reward_moves":lock["reward_moves"],
        "rr":lock["rr"],
        "reason":lock["reason"],
        "expires_in_seconds":max(0,lock_seconds-age),
        "blocked_updates":lock.get("blocked_updates",0),
        "simple_message":"Next plan is locked. Entry/stop/target will not move every refresh.",
        "time":now.isoformat()
    }

    pp=result.get("pro_panel") or {}
    if pp:
        pp["entry"]=lock["entry"]
        pp["buy_above"]=lock["buy_above"]
        pp["sell_below"]=lock["sell_below"]
        pp["stop_or_cancel"]=lock["stop"]
        pp["target"]=lock["target"]
        pp["risk_moves"]=lock["risk_moves"]
        pp["reward_moves"]=lock["reward_moves"]
        pp["rr"]=lock["rr"]
        pp["reason"]=lock["reason"] or pp.get("reason")
        result["pro_panel"]=pp

    np=result.get("next_plan") or {}
    if np:
        np["continuation_trigger"]=lock["entry"]
        np["stop"]=lock["stop"]
        np["target"]=lock["target"]
        np["risk_moves"]=lock["risk_moves"]
        np["reward_moves"]=lock["reward_moves"]
        np["rr"]=lock["rr"]
        result["next_plan"]=np

    return result

def plan_lock_report():
    now=_now()
    out=[]
    for asset,lock in _PLAN_LOCKS.items():
        d=dict(lock)
        d["created_at"]=d["created_at"].isoformat()
        d["age_seconds"]=int((now-lock["created_at"]).total_seconds())
        out.append(d)
    return {"plan_locks":out}
