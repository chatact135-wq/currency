
import os
from datetime import datetime, timezone

_SUMMARY_MEMORY = {}

def _num(v, default=None):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default

def _upper(v):
    return str(v or "").upper()

def _direction(result):
    tr = result.get("trade_readiness") or {}
    d = _upper(tr.get("direction"))
    if d in ["BUY", "SELL"]:
        return d

    mm = result.get("market_map") or {}
    cs = mm.get("current_state") or {}
    b = _upper(cs.get("bias") or result.get("master_bias") or result.get("final_action"))
    if "BUY" in b and "SELL" not in b:
        return "BUY"
    if "SELL" in b and "BUY" not in b:
        return "SELL"

    probs = result.get("probabilities") or {}
    up = _num(probs.get("up"), 0)
    down = _num(probs.get("down"), 0)
    if up - down >= 12:
        return "BUY"
    if down - up >= 12:
        return "SELL"
    return "NEUTRAL"

def _levels(result):
    mm = result.get("market_map") or {}
    tm = mm.get("trade_map") or {}
    tr = result.get("trade_readiness") or {}
    return {
        "entry": tr.get("entry") or tm.get("aggressive_entry"),
        "safe_entry": tr.get("safe_entry") or tm.get("safe_entry"),
        "stop_loss": tr.get("stop_loss") or tm.get("stop_loss"),
        "tp1": tr.get("tp1") or tm.get("tp1_partial_close"),
        "tp2": tr.get("tp2") or tm.get("tp2"),
        "cancel_level": tr.get("cancel_level") or tm.get("cancel_level")
    }

def _has_valid_levels(levels):
    return all(levels.get(k) is not None for k in ["entry", "stop_loss", "tp1"])

def _price_distance_ok(result, direction, levels):
    price = _num(result.get("price"))
    entry = _num(levels.get("entry"))
    tp1 = _num(levels.get("tp1"))
    if price is None or entry is None:
        return False, "Price or entry is missing."

    # Do not allow entry if already past TP1.
    if tp1 is not None:
        if direction == "BUY" and price >= tp1:
            return False, "Price is already near/after first profit target. Too late."
        if direction == "SELL" and price <= tp1:
            return False, "Price is already near/after first profit target. Too late."

    # If price is close enough to entry or already just across entry, allow practical green.
    pip = 0.0001
    if result.get("asset") == "XAUUSD":
        pip = 0.1
    max_distance_pips = float(os.getenv("TRADER_MAX_ENTRY_DISTANCE_PIPS", "3.5"))
    dist_pips = abs(price - entry) / pip
    if dist_pips <= max_distance_pips:
        return True, "Price is close enough to the entry level."

    # If already across entry but not far, still ok.
    if direction == "BUY" and price >= entry and dist_pips <= max_distance_pips * 1.5:
        return True, "Price is above the buy level but not too far."
    if direction == "SELL" and price <= entry and dist_pips <= max_distance_pips * 1.5:
        return True, "Price is below the sell level but not too far."

    return False, f"Price is {round(dist_pips,1)} pips from entry, too far for a clean new entry."

def _blocked(result):
    reasons = []

    if result.get("data_fresh") is False:
        reasons.append("Live data is not fresh.")

    news = result.get("news") or {}
    if news.get("mode") == "NEWS_WAIT":
        reasons.append("News is close. Wait.")

    regime = result.get("regime_guard") or {}
    if regime.get("mode") == "BLOCK_TRADE":
        reasons.append("Market condition is blocked.")

    dl = result.get("direction_lock") or {}
    if dl.get("flip_blocked"):
        reasons.append("Direction changed too quickly. Wait.")

    sm = result.get("strong_move") or {}
    if sm.get("detected") and sm.get("new_entry_rule"):
        # Strong move should not always block, but if entry already too late, it will be blocked by distance.
        pass

    ts = result.get("trigger_state") or {}
    if ts.get("state") == "FAILED_CANCEL":
        reasons.append("The level failed.")
    if ts.get("state") == "TOO_LATE_DO_NOT_CHASE":
        reasons.append("The move already happened. Do not enter late.")

    return reasons

def _score(result):
    tr = result.get("trade_readiness") or {}
    s = _num(tr.get("score"), None)
    if s is not None:
        return int(s)

    probs = result.get("probabilities") or {}
    up = _num(probs.get("up"), 0)
    down = _num(probs.get("down"), 0)
    return int(max(up, down))

def apply_simple_trader(result):
    if result.get("status") != "live":
        return result

    asset = result.get("asset")
    direction = _direction(result)
    levels = _levels(result)
    score = _score(result)
    blocks = _blocked(result)
    price_ok, price_reason = _price_distance_ok(result, direction, levels) if direction in ["BUY","SELL"] else (False, "No clear direction.")
    valid_levels = _has_valid_levels(levels)

    ts = result.get("trigger_state") or {}
    perm = _upper(ts.get("entry_permission"))
    state = _upper(ts.get("state"))
    tr_state = _upper((result.get("trade_readiness") or {}).get("state"))

    sensitivity = os.getenv("TRADER_MODE", "balanced").lower()
    green_score = 62 if sensitivity == "balanced" else 72
    prepare_score = 43 if sensitivity == "balanced" else 52

    final_command = "DO NOT ENTER"
    color = "red"
    reason = "Conditions are not clear enough."
    action_steps = ["Do not open a new trade now."]

    if direction == "NEUTRAL":
        final_command = "DO NOT ENTER"
        color = "red"
        reason = "No clear buy or sell direction."
        action_steps = ["Do not buy.", "Do not sell.", "Wait for clearer direction."]
    elif blocks:
        if any("move already happened" in b.lower() for b in blocks):
            final_command = "DO NOT CHASE"
            color = "red"
            reason = "The move already happened."
            action_steps = ["Do not enter late.", "Wait for price to come back to a better area."]
        else:
            final_command = "DO NOT ENTER"
            color = "red"
            reason = " ".join(blocks)
            action_steps = ["Wait until the warning is gone."]
    elif not valid_levels:
        final_command = f"WAIT FOR {direction}"
        color = "yellow"
        reason = "Entry, stop loss, or target is missing."
        action_steps = ["Do not enter until entry, stop loss, and target are all shown."]
    elif ("ENTRY_ALLOWED" in perm or "ACTIVE" in tr_state or score >= green_score) and price_ok:
        final_command = f"{direction} NOW"
        color = "green"
        reason = price_reason
        if direction == "BUY":
            action_steps = [
                f"Buy around {levels.get('entry')}.",
                f"Stop loss: {levels.get('stop_loss')}.",
                f"Take some profit: {levels.get('tp1')}.",
                f"Next target: {levels.get('tp2')}.",
                f"Cancel buy if price goes below {levels.get('cancel_level')}."
            ]
        else:
            action_steps = [
                f"Sell around {levels.get('entry')}.",
                f"Stop loss: {levels.get('stop_loss')}.",
                f"Take some profit: {levels.get('tp1')}.",
                f"Next target: {levels.get('tp2')}.",
                f"Cancel sell if price goes above {levels.get('cancel_level')}."
            ]
    elif score >= prepare_score:
        final_command = f"WAIT FOR {direction}"
        color = "yellow"
        reason = "Direction exists, but entry is not ready yet."
        if direction == "BUY":
            action_steps = [
                f"Do not buy now.",
                f"Buy only if price reaches {levels.get('entry')} and stays above it.",
                f"Cancel buy if price goes below {levels.get('cancel_level')}."
            ]
        else:
            action_steps = [
                f"Do not sell now.",
                f"Sell only if price reaches {levels.get('entry')} and stays below it.",
                f"Cancel sell if price goes above {levels.get('cancel_level')}."
            ]
    else:
        final_command = "DO NOT ENTER"
        color = "red"
        reason = "The signal is too weak."
        action_steps = ["Do not trade this setup.", "Wait for a better signal."]

    sm = result.get("strong_move") or {}
    if sm.get("detected") and final_command not in ["BUY NOW", "SELL NOW"]:
        # Add management note but do not override clear green entries.
        management = sm.get("simple_message")
    else:
        management = None

    simple_trader = {
        "final_command": final_command,
        "color": color,
        "direction": direction,
        "score": score,
        "reason": reason,
        "action_steps": action_steps,
        "levels": levels,
        "management_note": management,
        "rule": "Only BUY NOW or SELL NOW means new entry. WAIT, WATCH, PREPARE, DO NOT CHASE, or DO NOT ENTER means no new trade.",
        "mode": sensitivity,
        "time": datetime.now(timezone.utc).isoformat()
    }

    result["simple_trader"] = simple_trader

    # Override visible final action to make dashboard simple and consistent.
    result["final_action"] = final_command
    if color == "green":
        result["entry_permission"] = "ENTRY_ALLOWED"
    else:
        result["entry_permission"] = "NO_ENTRY"

    fd = result.get("final_decision") or {}
    if fd:
        fd["final_action"] = final_command
        fd["command"] = final_command
        fd["entry_permission"] = result["entry_permission"]
        fd["summary"] = reason
        result["final_decision"] = fd

    _SUMMARY_MEMORY[asset] = simple_trader
    return result

def trader_summary_report():
    return {"summary": _SUMMARY_MEMORY}
