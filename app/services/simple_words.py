
TECH_WORDS = {
    "pullback": "price came back a little after moving",
    "retest": "price came back to check the same level again",
    "resistance": "upper price area where price may stop",
    "support": "lower price area where price may stop",
    "breakout": "price crossed the level",
    "breakdown": "price crossed down below the level",
    "rejection": "price touched the area and failed",
    "liquidity sweep": "fake move that grabs stops then comes back",
    "sweep": "fake move that grabs stops then comes back",
    "wick": "thin candle line showing price went there then came back",
    "fvg": "empty price gap area",
    "fair value gap": "empty price gap area",
    "bos": "price broke the old high or low",
    "choch": "possible direction change",
    "premium": "upper expensive area",
    "discount": "lower cheaper area",
    "mitigation": "price returned to an old decision area",
    "imbalance": "fast move area where price may come back later",
    "range": "sideways market",
    "trend": "main direction",
    "scalp": "quick short trade",
    "intraday": "trade inside the same day",
    "do not chase": "do not enter late because the move already happened",
    "no chase": "do not enter late because the move already happened",
    "hold": "stay above or below the level for a short time",
    "trigger": "price level that can activate the idea",
    "entry": "your possible open price",
    "stop loss": "price where you close if the trade is wrong",
    "take profit": "price where you close with profit",
}

def replace_terms(text):
    if text is None:
        return text
    out = str(text)
    # Replace longer phrases first
    for k in sorted(TECH_WORDS.keys(), key=len, reverse=True):
        out = re_case_replace(out, k, TECH_WORDS[k])
    return out

def re_case_replace(text, old, new):
    import re
    return re.sub(re.escape(old), new, text, flags=re.IGNORECASE)

def build_simple_action(result):
    mm = result.get("market_map") or {}
    tm = mm.get("trade_map") or {}
    tr = result.get("trade_readiness") or {}
    ts = result.get("trigger_state") or {}
    state = str(tr.get("state") or result.get("final_action") or "").upper()
    direction = str(tr.get("direction") or mm.get("current_state", {}).get("bias") or "").upper()

    entry = tr.get("entry") or tm.get("aggressive_entry")
    safe = tr.get("safe_entry") or tm.get("safe_entry")
    sl = tr.get("stop_loss") or tm.get("stop_loss")
    tp1 = tr.get("tp1") or tm.get("tp1_partial_close")
    tp2 = tr.get("tp2") or tm.get("tp2")
    cancel = tr.get("cancel_level") or tm.get("cancel_level")

    if "TOO LATE" in state or "DO NOT CHASE" in state:
        headline = "The move already happened. Do not enter late."
        steps = [
            "Do not buy or sell now.",
            "Wait for price to come back to a better area.",
            "Only trade again if a new clear signal appears."
        ]
    elif "ACTIVE" in state and direction in ["BUY", "SELL"]:
        headline = f"{direction} is active, but use small risk."
        if direction == "BUY":
            steps = [
                f"Buy is allowed only if price is still above {entry}.",
                f"If price falls to {sl}, the buy idea is wrong.",
                f"Take some profit near {tp1}.",
                f"If price keeps going up, next target is {tp2}.",
                f"Cancel buy if price goes below {cancel}."
            ]
        else:
            steps = [
                f"Sell is allowed only if price is still below {entry}.",
                f"If price rises to {sl}, the sell idea is wrong.",
                f"Take some profit near {tp1}.",
                f"If price keeps going down, next target is {tp2}.",
                f"Cancel sell if price goes above {cancel}."
            ]
    elif "PREPARE" in state and direction in ["BUY", "SELL"]:
        headline = f"Prepare {direction}, but do not enter yet."
        if direction == "BUY":
            steps = [
                f"Watch if price goes above {entry}.",
                "Do not buy just because price touches the number.",
                "Buy becomes better only if price stays above that number.",
                f"Cancel the buy idea if price goes below {cancel}."
            ]
        else:
            steps = [
                f"Watch if price goes below {entry}.",
                "Do not sell just because price touches the number.",
                "Sell becomes better only if price stays below that number.",
                f"Cancel the sell idea if price goes above {cancel}."
            ]
    elif "WATCH" in state and direction in ["BUY", "SELL"]:
        headline = f"{direction} idea exists, but it is still early."
        steps = [
            "Do not enter now.",
            "Wait until the price reaches the important level.",
            "If price moves too fast before you enter, do not enter late."
        ]
    else:
        headline = "No trade now."
        steps = [
            "Do not buy now.",
            "Do not sell now.",
            "Wait for a clearer level and direction."
        ]

    return {
        "headline": replace_terms(headline),
        "steps": [replace_terms(x) for x in steps],
        "dictionary": TECH_WORDS,
        "trigger_state_simple": replace_terms(ts.get("message")),
        "note": "This box avoids technical words and explains the action in simple words."
    }

def apply_simple_words(result):
    if result.get("status") != "live":
        return result

    # Add simple action summary
    result["simple_action"] = build_simple_action(result)

    # Simplify known message fields without removing original logic
    fields = ["final_action", "warning"]
    for f in fields:
        if f in result and isinstance(result.get(f), str):
            result[f + "_simple"] = replace_terms(result.get(f))

    fd = result.get("final_decision") or {}
    if fd:
        fd["summary_simple"] = replace_terms(fd.get("summary"))
        fd["command_simple"] = replace_terms(fd.get("command"))
        result["final_decision"] = fd

    mm = result.get("market_map") or {}
    sp = mm.get("simple_trade_plan") or {}
    if sp and sp.get("simple_steps"):
        sp["simple_steps"] = [replace_terms(x) for x in sp.get("simple_steps")]
        sp["headline"] = replace_terms(sp.get("headline"))
        mm["simple_trade_plan"] = sp
        result["market_map"] = mm

    tr = result.get("trade_readiness") or {}
    if tr:
        tr["headline_simple"] = replace_terms(tr.get("headline"))
        tr["reasons_simple"] = [replace_terms(x) for x in tr.get("reasons", [])]
        result["trade_readiness"] = tr

    alerts = result.get("alerts") or []
    for a in alerts:
        if isinstance(a, dict):
            a["title_simple"] = replace_terms(a.get("title"))
            a["action_simple"] = replace_terms(a.get("action"))
            a["reason_simple"] = replace_terms(a.get("reason"))
    result["alerts"] = alerts

    return result
