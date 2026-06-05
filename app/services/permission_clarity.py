
from datetime import datetime, timezone

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

def _inactive_reason(sp, pp):
    rr = _num(sp.get("rr") or pp.get("rr"))
    risk = _num(sp.get("risk_moves") or pp.get("risk_moves"))
    reward = _num(sp.get("reward_moves") or pp.get("reward_moves"))
    decision = _upper(sp.get("decision") or pp.get("decision"))

    if "NO TRADE" in decision:
        return sp.get("reason") or pp.get("reason") or "No trade permission."
    if rr is not None and rr < 1:
        return f"Reward/risk is weak: R/R {rr}. Risk is bigger than reward."
    if risk is not None and reward is not None and risk > reward:
        return f"Risk {risk} moves is bigger than reward {reward} moves."
    return sp.get("reason") or pp.get("reason") or "Strategy exists but trigger is not confirmed."

def _must_change(sp, pp, direction):
    rr = _num(sp.get("rr") or pp.get("rr"))
    risk = _num(sp.get("risk_moves") or pp.get("risk_moves"))
    reward = _num(sp.get("reward_moves") or pp.get("reward_moves"))
    out = [f"Decision must change to SCALP NOW {direction} or TRADE NOW {direction}."]

    if rr is not None and rr < 1:
        out.append("Reward/risk must improve above 1.0.")
    if risk is not None and reward is not None and risk > reward:
        out.append("Risk must become smaller than reward.")
    out.append("Strategy trigger must confirm, not only touch the watch level.")
    return out

def apply_permission_clarity(result):
    if result.get("status") != "live":
        return result

    asset = result.get("asset") or result.get("display") or "UNKNOWN"
    sp = result.get("strategy_permission") or {}
    pp = result.get("pro_panel") or {}

    decision = sp.get("decision") or pp.get("decision") or result.get("final_action") or "NO DATA"
    dupper = _upper(decision)
    active = ("TRADE NOW" in dupper) or ("SCALP NOW" in dupper)

    direction = sp.get("direction") or pp.get("direction") or "-"
    current = sp.get("current_price") or pp.get("current_price") or result.get("price")

    watch_buy = sp.get("buy_above") or pp.get("buy_above")
    watch_sell = sp.get("sell_below") or pp.get("sell_below")

    active_entry = (sp.get("entry") or pp.get("entry")) if active else None
    active_stop = (sp.get("stop") or pp.get("stop_or_cancel")) if active else None
    active_target = (sp.get("target") or pp.get("target")) if active else None

    report = {
        "asset": asset,
        "status": "ACTIVE ENTRY" if active else "WATCH ONLY — DO NOT ENTER",
        "decision": decision,
        "direction": direction,
        "current_price": current,
        "active_entry": active_entry,
        "active_stop": active_stop,
        "active_target": active_target,
        "watch_buy_above": watch_buy,
        "watch_sell_below": watch_sell,
        "risk_moves": sp.get("risk_moves") or pp.get("risk_moves"),
        "reward_moves": sp.get("reward_moves") or pp.get("reward_moves"),
        "rr": sp.get("rr") or pp.get("rr"),
        "why_not_active": None if active else _inactive_reason(sp, pp),
        "what_must_change": [] if active else _must_change(sp, pp, direction),
        "rule": "Do not enter from watch levels. Enter only when status is ACTIVE ENTRY and decision says TRADE NOW or SCALP NOW.",
        "time": _now().isoformat()
    }

    result["permission_clarity"] = report
    _MEM[asset] = report

    # Make old top panel less confusing
    if pp and not active:
        pp["entry"] = "NOT ACTIVE"
        pp["reason"] = report["why_not_active"]
        result["pro_panel"] = pp

    return result

def permission_clarity_report():
    return {"permission_clarity": list(_MEM.values())}
