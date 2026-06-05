from __future__ import annotations
import pandas as pd
from .indicators import add_indicators
from .market_mode import detect_market_mode
from .utils import moves, signed_moves, add_moves, back_moves, rr
from .config import MIN_SCALP_RR, MIN_TRADE_RR, MAX_SCALP_RISK_MOVES, MAX_TRADE_RISK_MOVES, NO_CHASE_MOVES

def _empty(reason: str, mode: dict, price: float | None = None) -> dict:
    return {
        "command": "NO TRADE",
        "strategy": "NO STRATEGY",
        "direction": "NEUTRAL",
        "entry": None,
        "stop": None,
        "target": None,
        "risk_moves": None,
        "reward_moves": None,
        "rr": None,
        "price": price,
        "reason": reason,
        "market_mode": mode,
        "quality": "BLOCKED",
    }

def _trade(command: str, strategy: str, direction: str, entry: float, stop: float, target: float, reason: str, mode: dict, quality: str = "B") -> dict:
    risk, reward, ratio = rr(entry, stop, target, direction)
    return {
        "command": command,
        "strategy": strategy,
        "direction": direction,
        "entry": round(entry, 5),
        "stop": round(stop, 5),
        "target": round(target, 5),
        "risk_moves": round(risk, 1) if risk is not None else None,
        "reward_moves": round(reward, 1) if reward is not None else None,
        "rr": round(ratio, 2) if ratio is not None else None,
        "price": round(entry, 5),
        "reason": reason,
        "market_mode": mode,
        "quality": quality,
    }

def _risk_approved(signal: dict) -> bool:
    if signal["rr"] is None or signal["risk_moves"] is None:
        return False
    if signal["command"].startswith("TRADE NOW"):
        return signal["rr"] >= MIN_TRADE_RR and signal["risk_moves"] <= MAX_TRADE_RISK_MOVES
    if signal["command"].startswith("SCALP NOW"):
        return signal["rr"] >= MIN_SCALP_RR and signal["risk_moves"] <= MAX_SCALP_RISK_MOVES
    return False

def analyze_symbol(symbol: str, df: pd.DataFrame, spread_moves: float | None = None) -> dict:
    if len(df) < 80:
        mode = {"mode": "NO DATA", "bias": "NEUTRAL", "reason": "Not enough candles."}
        return _empty("Need more candles.", mode)

    x = add_indicators(df).dropna().reset_index(drop=True)
    mode = detect_market_mode(df)
    last = x.iloc[-1]
    price = float(last["close"])

    # Safety blocks
    if spread_moves is not None and spread_moves > 6:
        return _empty(f"Spread too high: {spread_moves:.1f} moves.", mode, price)

    if mode["mode"] in ["NO DATA", "CHOPPY"]:
        return _empty(mode["reason"], mode, price)

    if mode["mode"] == "DANGER":
        return {
            **_empty(mode["reason"], mode, price),
            "command": "NO TRADE — DANGER",
            "strategy": "VOLATILITY BLOCK",
        }

    # Key levels
    prev_high = float(last["rolling_high_20"])
    prev_low = float(last["rolling_low_20"])
    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])

    recent5_move = signed_moves(float(x.iloc[-5]["open"]), price) if len(x) >= 5 else 0
    recent15_move = signed_moves(float(x.iloc[-15]["open"]), price) if len(x) >= 15 else 0
    body = float(last["body_moves"])
    candle_dir = last["direction"]

    candidates = []

    # Strong Trend Day Continuation
    if mode["mode"] == "TREND SELL":
        # Block buying during sell trend
        # Sell continuation if price below EMA20 and breaking/retesting lows
        late_moves = moves(prev_low, price) if price < prev_low else 0
        if late_moves > NO_CHASE_MOVES:
            candidates.append({
                "command": "MOVE MISSED — DO NOT CHASE",
                "strategy": "TREND SELL NO-CHASE",
                "direction": "SELL",
                "entry": None, "stop": None, "target": None,
                "risk_moves": None, "reward_moves": None, "rr": None,
                "price": round(price,5),
                "reason": f"Sell trend is strong but price already moved {late_moves:.1f} moves below recent low.",
                "market_mode": mode,
                "quality": "MISSED",
            })
        elif price < prev_low and candle_dir == "SELL" and body >= 8:
            entry = price
            stop = back_moves(entry, 18, "SELL")
            target = add_moves(entry, 30, "SELL")
            candidates.append(_trade("SCALP NOW SELL", "Strong Trend Day Breakdown", "SELL", entry, stop, target, "TREND SELL + break below recent low with red candle.", mode, "B"))
        elif price < ema20 and abs(price - ema20) / 0.00001 <= 18 and candle_dir == "SELL":
            entry = price
            stop = back_moves(entry, 20, "SELL")
            target = add_moves(entry, 32, "SELL")
            candidates.append(_trade("SCALP NOW SELL", "Pullback Continuation Sell", "SELL", entry, stop, target, "TREND SELL + pullback near EMA20 failed.", mode, "B"))

    elif mode["mode"] == "TREND BUY":
        late_moves = moves(prev_high, price) if price > prev_high else 0
        if late_moves > NO_CHASE_MOVES:
            candidates.append({
                "command": "MOVE MISSED — DO NOT CHASE",
                "strategy": "TREND BUY NO-CHASE",
                "direction": "BUY",
                "entry": None, "stop": None, "target": None,
                "risk_moves": None, "reward_moves": None, "rr": None,
                "price": round(price,5),
                "reason": f"Buy trend is strong but price already moved {late_moves:.1f} moves above recent high.",
                "market_mode": mode,
                "quality": "MISSED",
            })
        elif price > prev_high and candle_dir == "BUY" and body >= 8:
            entry = price
            stop = back_moves(entry, 18, "BUY")
            target = add_moves(entry, 30, "BUY")
            candidates.append(_trade("SCALP NOW BUY", "Strong Trend Day Breakout", "BUY", entry, stop, target, "TREND BUY + break above recent high with green candle.", mode, "B"))
        elif price > ema20 and abs(price - ema20) / 0.00001 <= 18 and candle_dir == "BUY":
            entry = price
            stop = back_moves(entry, 20, "BUY")
            target = add_moves(entry, 32, "BUY")
            candidates.append(_trade("SCALP NOW BUY", "Pullback Continuation Buy", "BUY", entry, stop, target, "TREND BUY + pullback near EMA20 held.", mode, "B"))

    # Normal mode: only clean break + retest, not first spike
    if mode["mode"] == "NORMAL":
        # Break + retest buy: price above prev high recently, came back near level, resumes
        recent_high = float(x["high"].tail(10).max())
        recent_low = float(x["low"].tail(10).min())
        if mode["bias"] == "BUY" and price > ema20 > ema50 and candle_dir == "BUY":
            dist_to_break = moves(price, prev_high)
            if dist_to_break <= 15 and recent15_move > 25:
                entry = price
                stop = back_moves(entry, 16, "BUY")
                target = add_moves(entry, 26, "BUY")
                candidates.append(_trade("SCALP NOW BUY", "Break + Retest Continuation Buy", "BUY", entry, stop, target, "NORMAL BUY bias + retest near breakout level + resume candle.", mode, "B"))
        elif mode["bias"] == "SELL" and price < ema20 < ema50 and candle_dir == "SELL":
            dist_to_break = moves(price, prev_low)
            if dist_to_break <= 15 and recent15_move < -25:
                entry = price
                stop = back_moves(entry, 16, "SELL")
                target = add_moves(entry, 26, "SELL")
                candidates.append(_trade("SCALP NOW SELL", "Break + Retest Continuation Sell", "SELL", entry, stop, target, "NORMAL SELL bias + retest near breakdown level + resume candle.", mode, "B"))

    # Liquidity sweep reversal, only when not strong trend against it
    recent20_high = float(x["high"].tail(20).max())
    recent20_low = float(x["low"].tail(20).min())
    if mode["mode"] != "TREND SELL":
        if float(last["low"]) < recent20_low and price > recent20_low and candle_dir == "BUY":
            entry = price
            stop = back_moves(entry, 16, "BUY")
            target = add_moves(entry, 28, "BUY")
            candidates.append(_trade("SCALP NOW BUY", "Liquidity Sweep Reversal Buy", "BUY", entry, stop, target, "Swept recent low then closed back above. Allowed because not TREND SELL.", mode, "C"))
    if mode["mode"] != "TREND BUY":
        if float(last["high"]) > recent20_high and price < recent20_high and candle_dir == "SELL":
            entry = price
            stop = back_moves(entry, 16, "SELL")
            target = add_moves(entry, 28, "SELL")
            candidates.append(_trade("SCALP NOW SELL", "Liquidity Sweep Reversal Sell", "SELL", entry, stop, target, "Swept recent high then closed back below. Allowed because not TREND BUY.", mode, "C"))

    # Approaching levels = plan only
    if not candidates:
        if mode["bias"] == "BUY":
            return {
                **_empty("Setup forming but not active yet. Wait for breakout/retest or pullback confirmation.", mode, price),
                "command": "PLAN ONLY — DO NOT ENTER",
                "strategy": "BUY SETUP FORMING",
                "direction": "BUY",
                "watch_level": round(prev_high, 5),
            }
        elif mode["bias"] == "SELL":
            return {
                **_empty("Setup forming but not active yet. Wait for breakdown/retest or pullback confirmation.", mode, price),
                "command": "PLAN ONLY — DO NOT ENTER",
                "strategy": "SELL SETUP FORMING",
                "direction": "SELL",
                "watch_level": round(prev_low, 5),
            }
        return _empty("No clean strategy event.", mode, price)

    # Prefer valid risk-approved trades; otherwise return most informative no-chase/plan.
    valid = [c for c in candidates if c["command"].startswith(("SCALP NOW", "TRADE NOW")) and _risk_approved(c)]
    if valid:
        # choose best RR then quality
        best = sorted(valid, key=lambda s: (s["rr"] or 0, s["reward_moves"] or 0), reverse=True)[0]
        return best

    # If only missed or rejected trades
    missed = [c for c in candidates if "MISSED" in c["quality"]]
    if missed:
        return missed[0]

    return {
        **_empty("Strategy appeared but risk/reward filter did not approve entry.", mode, price),
        "command": "PLAN ONLY — DO NOT ENTER",
        "strategy": candidates[0]["strategy"],
        "direction": candidates[0]["direction"],
    }
