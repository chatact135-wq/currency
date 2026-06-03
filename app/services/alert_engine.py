
from datetime import datetime, timezone
from app.services.market import ASSETS, normalize

_ALERT_MEMORY = {}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def pips(sym, a, b):
    return round(abs(float(a)-float(b)) / ASSETS[sym]["pip"], 1)

def recent_move(sym, candles, lookback=5):
    sym = normalize(sym)
    if len(candles) < 3:
        return None
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    first = recent[0]["open"]
    last = recent[-1]["close"]
    high = max(x["high"] for x in recent)
    low = min(x["low"] for x in recent)
    net = last - first
    direction = "BUY" if net > 0 else "SELL" if net < 0 else "SIDEWAYS"
    return {
        "direction": direction,
        "first": first,
        "last": last,
        "high": high,
        "low": low,
        "net_pips": pips(sym, first, last),
        "range_pips": pips(sym, low, high),
        "candles": len(recent)
    }

def reversal_alert(sym, candles):
    if len(candles) < 3:
        return None
    prev = candles[-2]
    last = candles[-1]
    if prev["close"] < prev["open"] and last["close"] > last["open"] and last["close"] > prev["open"]:
        return ("BUY_REBOUND_DETECTED", "Previous sell pressure may have failed. Watch retest/continuation.")
    if prev["close"] > prev["open"] and last["close"] < last["open"] and last["close"] < prev["open"]:
        return ("SELL_REJECTION_DETECTED", "Previous buy pressure may have failed. Watch retest/continuation.")
    return None

def classify_fast_move(sym, candles, signal_result):
    sym = normalize(sym)
    pip = ASSETS[sym]["pip"]
    move = recent_move(sym, candles, 5)
    alerts = []
    if not move:
        return alerts

    price = signal_result.get("price")
    news = signal_result.get("news") or {}
    tstate = signal_result.get("trigger_state") or {}

    fast_threshold = 4 if pip == 0.0001 else 5 if pip >= 0.1 else 0.15
    chase_threshold = 7 if pip == 0.0001 else 8 if pip >= 0.1 else 0.25

    if move["direction"] in ["BUY", "SELL"] and move["net_pips"] >= fast_threshold:
        title = "FAST BUY MOVE DETECTED" if move["direction"] == "BUY" else "FAST SELL MOVE DETECTED"
        action = "WAIT RETEST"
        severity = "info"
        if move["net_pips"] >= chase_threshold:
            action = "DO NOT CHASE - WAIT PULLBACK"
            severity = "warning"
        if news.get("mode") == "POST_NEWS_IMPULSE":
            action = "POST-NEWS MOVE - USE SMALL RISK OR WAIT RETEST"
            severity = "warning"
        if tstate.get("entry_permission") == "ENTRY_ALLOWED":
            action = "ENTRY POSSIBLE ONLY IF REGIME SAFE"
            severity = "trade_watch"
        alerts.append({
            "asset": sym,
            "type": "FAST_MOVE",
            "title": title,
            "direction": move["direction"],
            "severity": severity,
            "action": action,
            "reason": f"{sym} moved {move['net_pips']} pips {move['direction']} across recent candles.",
            "price": price,
            "move_pips": move["net_pips"],
            "range_pips": move["range_pips"],
            "time": now_iso()
        })

    rev = reversal_alert(sym, candles)
    if rev:
        alerts.append({
            "asset": sym,
            "type": "REVERSAL_ALERT",
            "title": rev[0],
            "severity": "info",
            "action": "DO NOT CHASE - WAIT CONFIRMATION",
            "reason": rev[1],
            "price": price,
            "time": now_iso()
        })

    if tstate.get("state") in ["TOO_LATE_DO_NOT_CHASE", "BROKEN_WAIT_HOLD", "ACTIVE", "FAILED_CANCEL"]:
        alerts.append({
            "asset": sym,
            "type": "TRIGGER_STATE",
            "title": tstate.get("state"),
            "severity": "warning" if tstate.get("state") != "ACTIVE" else "trade_watch",
            "action": tstate.get("entry_permission"),
            "reason": tstate.get("message"),
            "price": price,
            "time": now_iso()
        })

    return alerts

def remember_alerts(asset, alerts):
    sym = normalize(asset)
    old = _ALERT_MEMORY.get(sym, [])
    merged = old + alerts
    _ALERT_MEMORY[sym] = merged[-20:]
    return _ALERT_MEMORY[sym]

def all_alerts():
    out = []
    for vals in _ALERT_MEMORY.values():
        out.extend(vals)
    return sorted(out, key=lambda x: x.get("time",""), reverse=True)[:50]
