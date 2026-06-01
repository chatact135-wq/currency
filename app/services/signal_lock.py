
from datetime import datetime, timezone, timedelta
from app.models import TradeState

LOCK_MINUTES = 5

def _now():
    return datetime.now(timezone.utc)

def action_direction(action):
    a = (action or "").upper()
    if "BUY" in a:
        return "BUY"
    if "SELL" in a:
        return "SELL"
    return "NEUTRAL"

def has_entry_permission(action, stage):
    a = (action or "").upper()
    s = (stage or "").upper()
    # The system must not allow real entry from SETUP/WATCH/probability alone.
    if "EXECUTE" in a or "ACTIVE SCALP" in a or "EXECUTION ACTIVE" in s:
        return True
    return False

def invalidated(direction, price, invalidation):
    if invalidation is None or direction not in ["BUY", "SELL"]:
        return False
    if direction == "BUY" and price <= invalidation:
        return True
    if direction == "SELL" and price >= invalidation:
        return True
    return False

def apply_signal_lock(db, result):
    asset = result.get("asset")
    price = float(result.get("price") or 0)
    action = result.get("final_action", "WAIT")
    stage = result.get("stage", "WAIT")
    direction = action_direction(action)
    confidence = float(result.get("confidence") or 0)
    plan = result.get("plan") or {}
    invalidation = plan.get("invalidation") or plan.get("stop_loss")

    permission = has_entry_permission(action, stage)

    state = db.query(TradeState).filter(TradeState.asset == asset).first()
    now = _now()

    if not state:
        state = TradeState(asset=asset, direction=direction, status="NONE")
        db.add(state)
        db.commit()
        db.refresh(state)

    # If an active/locked signal is invalidated, explicitly cancel/exit.
    if state.status in ["LOCKED", "ACTIVE"] and invalidated(state.direction, price, state.invalidation):
        state.status = "CANCELLED"
        state.action = f"CANCEL {state.direction}"
        state.entry_permission = "NO_ENTRY"
        state.reason = "Previous signal invalidated by price crossing invalidation level."
        state.updated_at = now
        db.commit()
        result["trade_state"] = {
            "status": state.status,
            "entry_permission": state.entry_permission,
            "locked_direction": state.direction,
            "reason": state.reason
        }
        result["final_action"] = state.action
        result["warning"] = state.reason
        return result

    # If current signal is entry-grade, lock it.
    if permission and direction in ["BUY", "SELL"]:
        state.direction = direction
        state.status = "ACTIVE"
        state.action = action
        state.entry_permission = "ENTRY_ALLOWED"
        state.locked_price = price
        state.invalidation = invalidation
        state.confidence = confidence
        state.reason = "Entry-grade signal confirmed. Signal is locked unless invalidated."
        state.updated_at = now
        db.commit()
        result["trade_state"] = {
            "status": state.status,
            "entry_permission": state.entry_permission,
            "locked_direction": state.direction,
            "locked_price": state.locked_price,
            "invalidation": state.invalidation,
            "reason": state.reason
        }
        result["entry_permission"] = "ENTRY_ALLOWED"
        return result

    # If recently there was a locked/active signal, do not silently flip to NO TRADE.
    age_ok = False
    try:
        age_ok = (now - state.updated_at.replace(tzinfo=timezone.utc)) <= timedelta(minutes=LOCK_MINUTES)
    except Exception:
        age_ok = False

    if state.status in ["ACTIVE", "LOCKED"] and age_ok:
        result["trade_state"] = {
            "status": "HOLD_OR_MANAGE",
            "entry_permission": "NO_NEW_ENTRY",
            "locked_direction": state.direction,
            "locked_price": state.locked_price,
            "invalidation": state.invalidation,
            "reason": "Previous entry-grade signal is still within lock window. Do not open a new opposite trade unless invalidated."
        }
        result["entry_permission"] = "NO_NEW_ENTRY"
        result["final_action"] = f"MANAGE {state.direction}"
        result["warning"] = "Manage previous signal. Do not open a new trade from this update."
        return result

    # For WATCH/SETUP/CONDITIONAL, explicitly block entry.
    state.direction = direction
    state.status = "WATCH" if direction in ["BUY", "SELL"] else "NONE"
    state.action = action
    state.entry_permission = "NO_ENTRY"
    state.locked_price = None
    state.invalidation = invalidation
    state.confidence = confidence
    state.reason = "No entry permission. Setup/watch is not a trade."
    state.updated_at = now
    db.commit()

    result["trade_state"] = {
        "status": state.status,
        "entry_permission": state.entry_permission,
        "locked_direction": state.direction,
        "reason": state.reason
    }
    result["entry_permission"] = "NO_ENTRY"
    return result
