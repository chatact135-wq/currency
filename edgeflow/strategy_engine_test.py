from __future__ import annotations
import pandas as pd
from .indicators import add_indicators
from .market_mode import detect_market_mode
from .utils import moves, signed_moves, add_moves, back_moves, rr
from .config import MIN_SCALP_RR, MIN_TRADE_RR, MAX_SCALP_RISK_MOVES, MAX_TRADE_RISK_MOVES, NO_CHASE_MOVES


# Experimental /test engine
# Main idea:
# - keep current production engine unchanged on /
# - /test uses stricter breakout logic and prioritizes pullback continuation
# - breakout trades need follow-through or breakout+hold instead of one first spike candle


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
        "engine_variant": "test",
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
        "engine_variant": "test",
    }


def _risk_approved(signal: dict) -> bool:
    if signal["rr"] is None or signal["risk_moves"] is None:
        return False
    if signal["command"].startswith("TRADE NOW"):
        return signal["rr"] >= MIN_TRADE_RR and signal["risk_moves"] <= MAX_TRADE_RISK_MOVES
    if signal["command"].startswith("SCALP NOW"):
        return signal["rr"] >= MIN_SCALP_RR and signal["risk_moves"] <= MAX_SCALP_RISK_MOVES
    return False


def analyze_symbol_test(symbol: str, df: pd.DataFrame, spread_moves: float | None = None) -> dict:
    if len(df) < 80:
        mode = {"mode": "NO DATA", "bias": "NEUTRAL", "reason": "Not enough candles."}
        return _empty("Need more candles.", mode)

    x = add_indicators(df).dropna().reset_index(drop=True)
    mode = detect_market_mode(df)
    last = x.iloc[-1]
    prev1 = x.iloc[-2]
    prev2 = x.iloc[-3]
    price = float(last["close"])

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

    prev_high = float(last["rolling_high_20"])
    prev_low = float(last["rolling_low_20"])
    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])

    recent5_move = signed_moves(float(x.iloc[-5]["open"]), price) if len(x) >= 5 else 0
    recent15_move = signed_moves(float(x.iloc[-15]["open"]), price) if len(x) >= 15 else 0
    body = float(last["body_moves"])
    candle_dir = last["direction"]

    prev_close = float(prev1["close"])
    prev_prev_close = float(prev2["close"])
    prev_dir = prev1["direction"]

    above_prev_high = price > prev_high
    below_prev_low = price < prev_low
    close_above_prev_high_prev_candle = prev_close > float(prev1["rolling_high_20"])
    close_below_prev_low_prev_candle = prev_close < float(prev1["rolling_low_20"])

    late_up = moves(prev_high, price) if price > prev_high else 0
    late_down = moves(prev_low, price) if price < prev_low else 0

    candidates = []

    # --- Trend continuation, but only with stronger confirmation on /test ---
    if mode["mode"] == "TREND BUY":
        if late_up > max(NO_CHASE_MOVES, 25):
            candidates.append({
                "command": "MOVE MISSED — DO NOT CHASE",
                "strategy": "TREND BUY NO-CHASE",
                "direction": "BUY",
                "entry": None, "stop": None, "target": None,
                "risk_moves": None, "reward_moves": None, "rr": None,
                "price": round(price, 5),
                "reason": f"Test engine: buy trend is strong but price already moved {late_up:.1f} moves above recent high.",
                "market_mode": mode,
                "quality": "MISSED",
                "engine_variant": "test",
            })
        else:
            # Pullback continuation = preferred in test mode
            touched_ema_zone = abs(float(prev1["low"]) - ema20) / 0.00001 <= 10 or abs(float(last["low"]) - ema20) / 0.00001 <= 10
            if price > ema20 > ema50 and candle_dir == "BUY" and body >= 5 and touched_ema_zone and recent15_move > 8:
                entry = price
                stop = back_moves(entry, 18, "BUY")
                target = add_moves(entry, 30, "BUY")
                candidates.append(_trade("SCALP NOW BUY", "Pullback Continuation Buy (Test)", "BUY", entry, stop, target, "TREND BUY + pullback into EMA20 zone held + green confirmation candle.", mode, "A"))

            # Breakout continuation requires follow-through / not first spike only
            follow_through_buy = above_prev_high and candle_dir == "BUY" and body >= 6 and recent5_move > 10 and (close_above_prev_high_prev_candle or prev_dir == "BUY")
            if follow_through_buy:
                entry = price
                stop = back_moves(entry, 16, "BUY")
                target = add_moves(entry, 26, "BUY")
                candidates.append(_trade("SCALP NOW BUY", "Breakout Continuation Buy (Test)", "BUY", entry, stop, target, "TREND BUY + breakout with follow-through, not first spike only.", mode, "B"))

    elif mode["mode"] == "TREND SELL":
        if late_down > max(NO_CHASE_MOVES, 25):
            candidates.append({
                "command": "MOVE MISSED — DO NOT CHASE",
                "strategy": "TREND SELL NO-CHASE",
                "direction": "SELL",
                "entry": None, "stop": None, "target": None,
                "risk_moves": None, "reward_moves": None, "rr": None,
                "price": round(price, 5),
                "reason": f"Test engine: sell trend is strong but price already moved {late_down:.1f} moves below recent low.",
                "market_mode": mode,
                "quality": "MISSED",
                "engine_variant": "test",
            })
        else:
            touched_ema_zone = abs(float(prev1["high"]) - ema20) / 0.00001 <= 10 or abs(float(last["high"]) - ema20) / 0.00001 <= 10
            if price < ema20 < ema50 and candle_dir == "SELL" and body >= 5 and touched_ema_zone and recent15_move < -8:
                entry = price
                stop = back_moves(entry, 18, "SELL")
                target = add_moves(entry, 30, "SELL")
                candidates.append(_trade("SCALP NOW SELL", "Pullback Continuation Sell (Test)", "SELL", entry, stop, target, "TREND SELL + pullback into EMA20 zone failed + red confirmation candle.", mode, "A"))

            follow_through_sell = below_prev_low and candle_dir == "SELL" and body >= 6 and recent5_move < -10 and (close_below_prev_low_prev_candle or prev_dir == "SELL")
            if follow_through_sell:
                entry = price
                stop = back_moves(entry, 16, "SELL")
                target = add_moves(entry, 26, "SELL")
                candidates.append(_trade("SCALP NOW SELL", "Breakdown Continuation Sell (Test)", "SELL", entry, stop, target, "TREND SELL + breakdown with follow-through, not first spike only.", mode, "B"))

    # Normal mode break + retest continuation
    if mode["mode"] == "NORMAL":
        if mode["bias"] == "BUY" and price > ema20 > ema50 and candle_dir == "BUY":
            if moves(price, prev_high) <= 12 and recent15_move > 18 and body >= 4:
                entry = price
                stop = back_moves(entry, 14, "BUY")
                target = add_moves(entry, 24, "BUY")
                candidates.append(_trade("SCALP NOW BUY", "Break + Retest Continuation Buy (Test)", "BUY", entry, stop, target, "NORMAL BUY bias + price resumed from retest zone.", mode, "B"))
        elif mode["bias"] == "SELL" and price < ema20 < ema50 and candle_dir == "SELL":
            if moves(price, prev_low) <= 12 and recent15_move < -18 and body >= 4:
                entry = price
                stop = back_moves(entry, 14, "SELL")
                target = add_moves(entry, 24, "SELL")
                candidates.append(_trade("SCALP NOW SELL", "Break + Retest Continuation Sell (Test)", "SELL", entry, stop, target, "NORMAL SELL bias + price resumed from breakdown retest zone.", mode, "B"))

    # Sweeps, confirmed only
    recent20_high = float(x["high"].tail(20).max())
    recent20_low = float(x["low"].tail(20).min())
    if mode["mode"] != "TREND SELL":
        if float(last["low"]) < recent20_low and price > recent20_low and candle_dir == "BUY" and body >= 6:
            entry = price
            stop = back_moves(entry, 14, "BUY")
            target = add_moves(entry, 24, "BUY")
            candidates.append(_trade("SCALP NOW BUY", "Liquidity Sweep Reversal Buy (Test)", "BUY", entry, stop, target, "Swept recent low then closed back above with clear green confirmation.", mode, "C"))
    if mode["mode"] != "TREND BUY":
        if float(last["high"]) > recent20_high and price < recent20_high and candle_dir == "SELL" and body >= 6:
            entry = price
            stop = back_moves(entry, 14, "SELL")
            target = add_moves(entry, 24, "SELL")
            candidates.append(_trade("SCALP NOW SELL", "Liquidity Sweep Reversal Sell (Test)", "SELL", entry, stop, target, "Swept recent high then closed back below with clear red confirmation.", mode, "C"))

    if not candidates:
        if mode["bias"] == "BUY":
            return {
                **_empty("Test engine: setup forming but not active yet. Need real confirmation, not just direction.", mode, price),
                "command": "PLAN ONLY — DO NOT ENTER",
                "strategy": "BUY SETUP FORMING (Test)",
                "direction": "BUY",
                "watch_level": round(prev_high, 5),
            }
        elif mode["bias"] == "SELL":
            return {
                **_empty("Test engine: setup forming but not active yet. Need real confirmation, not just direction.", mode, price),
                "command": "PLAN ONLY — DO NOT ENTER",
                "strategy": "SELL SETUP FORMING (Test)",
                "direction": "SELL",
                "watch_level": round(prev_low, 5),
            }
        return _empty("No clean strategy event.", mode, price)

    valid = [c for c in candidates if c["command"].startswith(("SCALP NOW", "TRADE NOW")) and _risk_approved(c)]
    if valid:
        best = sorted(valid, key=lambda s: ((s["quality"] == "A"), s["rr"] or 0, s["reward_moves"] or 0), reverse=True)[0]
        return best

    missed = [c for c in candidates if "MISSED" in c["quality"]]
    if missed:
        return missed[0]

    first = candidates[0]
    return {
        **_empty("Test engine: strategy appeared but risk/reward filter did not approve entry.", mode, price),
        "command": "PLAN ONLY — DO NOT ENTER",
        "strategy": first["strategy"],
        "direction": first["direction"],
    }
