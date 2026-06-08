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
        "price": round(price, 5) if price is not None else None,
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
    if signal.get("rr") is None or signal.get("risk_moves") is None:
        return False
    if signal["command"].startswith("TRADE NOW"):
        return signal["rr"] >= MIN_TRADE_RR and signal["risk_moves"] <= MAX_TRADE_RISK_MOVES
    if signal["command"].startswith("SCALP NOW"):
        return signal["rr"] >= MIN_SCALP_RR and signal["risk_moves"] <= MAX_SCALP_RISK_MOVES
    return False


def analyze_symbol_controlled(symbol: str, df: pd.DataFrame, *, allow_momentum: bool, system_name: str, spread_moves: float | None = None) -> dict:
    """Trend-aligned test engine.

    TEST-A: allow_momentum=False (conservative)
    TEST-B: allow_momentum=True (controlled momentum upgrade)
    """
    if len(df) < 80:
        mode = {"mode": "NO DATA", "bias": "NEUTRAL", "reason": "Not enough candles."}
        return _empty("Need more candles.", mode)

    x = add_indicators(df).dropna().reset_index(drop=True)
    if x.empty:
        mode = {"mode": "NO DATA", "bias": "NEUTRAL", "reason": "Indicators unavailable."}
        return _empty("Indicators unavailable.", mode)

    mode = detect_market_mode(df)
    last = x.iloc[-1]
    price = float(last["close"])

    if spread_moves is not None and spread_moves > 6:
        return _empty(f"Spread too high: {spread_moves:.1f} moves.", mode, price)

    if mode["mode"] in ["NO DATA", "CHOPPY", "DANGER"]:
        cmd = "NO TRADE — DANGER" if mode["mode"] == "DANGER" else "NO TRADE"
        out = _empty(mode.get("reason", "Blocked market condition."), mode, price)
        out["command"] = cmd
        out["strategy"] = "VOLATILITY BLOCK" if mode["mode"] == "DANGER" else "NO STRATEGY"
        return out

    prev_high = float(last["rolling_high_20"])
    prev_low = float(last["rolling_low_20"])
    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])
    recent5_move = signed_moves(float(x.iloc[-5]["open"]), price) if len(x) >= 5 else 0
    recent15_move = signed_moves(float(x.iloc[-15]["open"]), price) if len(x) >= 15 else 0
    body = float(last["body_moves"])
    candle_dir = str(last["direction"])

    candidates: list[dict] = []
    bias = mode.get("bias", "NEUTRAL")

    # Hard rule: only trade in the direction of confirmed market bias.
    # If bias is neutral, no real entry is allowed.
    if bias not in ["BUY", "SELL"]:
        return _empty("Neutral bias. V3 blocks entries until direction is clear.", mode, price)

    if mode["mode"] == "TREND BUY" and bias == "BUY":
        late_moves = moves(prev_high, price) if price > prev_high else 0
        if late_moves > NO_CHASE_MOVES:
            return {**_empty(f"Buy trend is strong but price already moved {late_moves:.1f} moves above recent high. Do not chase.", mode, price),
                    "command": "MOVE MISSED — DO NOT CHASE", "strategy": "TREND BUY NO-CHASE", "direction": "BUY", "quality": "MISSED"}
        # Conservative pullback continuation only
        if price > ema20 and abs(price - ema20) / 0.00001 <= 18 and candle_dir == "BUY":
            entry = price
            candidates.append(_trade("SCALP NOW BUY", "Pullback Continuation Buy", "BUY", entry, back_moves(entry, 20, "BUY"), add_moves(entry, 32, "BUY"), "TREND BUY + pullback near EMA20 held. Trend-aligned V3 entry.", mode, "A"))
        # First breakout is always plan only; V3 avoids raw chasing.
        elif price > prev_high and candle_dir == "BUY" and body >= 8:
            return {**_empty("First breakout is blocked. Wait for pullback/retest confirmation.", mode, price),
                    "command": "PLAN ONLY — DO NOT ENTER", "strategy": "Breakout Watch — Wait Pullback", "direction": "BUY", "quality": "WATCH"}

    elif mode["mode"] == "TREND SELL" and bias == "SELL":
        late_moves = moves(prev_low, price) if price < prev_low else 0
        if late_moves > NO_CHASE_MOVES:
            return {**_empty(f"Sell trend is strong but price already moved {late_moves:.1f} moves below recent low. Do not chase.", mode, price),
                    "command": "MOVE MISSED — DO NOT CHASE", "strategy": "TREND SELL NO-CHASE", "direction": "SELL", "quality": "MISSED"}
        if price < ema20 and abs(price - ema20) / 0.00001 <= 18 and candle_dir == "SELL":
            entry = price
            candidates.append(_trade("SCALP NOW SELL", "Pullback Continuation Sell", "SELL", entry, back_moves(entry, 20, "SELL"), add_moves(entry, 32, "SELL"), "TREND SELL + pullback near EMA20 failed. Trend-aligned V3 entry.", mode, "A"))
        elif price < prev_low and candle_dir == "SELL" and body >= 8:
            return {**_empty("First breakdown is blocked. Wait for pullback/retest confirmation.", mode, price),
                    "command": "PLAN ONLY — DO NOT ENTER", "strategy": "Breakdown Watch — Wait Pullback", "direction": "SELL", "quality": "WATCH"}

    # Normal mode: clean break + retest only, aligned with bias and EMA stack.
    if mode["mode"] == "NORMAL":
        if bias == "BUY" and price > ema20 > ema50 and candle_dir == "BUY":
            dist_to_break = moves(price, prev_high)
            if dist_to_break <= 15 and recent15_move > 25:
                entry = price
                candidates.append(_trade("SCALP NOW BUY", "Break + Retest Continuation Buy", "BUY", entry, back_moves(entry, 16, "BUY"), add_moves(entry, 26, "BUY"), "NORMAL BUY bias + retest near breakout level + resume candle. Trend-aligned V3 entry.", mode, "A"))
        elif bias == "SELL" and price < ema20 < ema50 and candle_dir == "SELL":
            dist_to_break = moves(price, prev_low)
            if dist_to_break <= 15 and recent15_move < -25:
                entry = price
                candidates.append(_trade("SCALP NOW SELL", "Break + Retest Continuation Sell", "SELL", entry, back_moves(entry, 16, "SELL"), add_moves(entry, 26, "SELL"), "NORMAL SELL bias + retest near breakdown level + resume candle. Trend-aligned V3 entry.", mode, "A"))

    # TEST-B only: upgrade setup forming into controlled momentum entry.
    if allow_momentum and not [c for c in candidates if c["command"].startswith(("SCALP NOW", "TRADE NOW"))]:
        dist_ema20 = abs(price - ema20) / 0.00001
        dist_ema50 = abs(price - ema50) / 0.00001
        structure_ok = dist_ema20 <= 55 or dist_ema50 <= 95
        if bias == "BUY" and price > ema20 > ema50 and candle_dir == "BUY":
            not_chasing_high = not (price > prev_high and moves(prev_high, price) > NO_CHASE_MOVES)
            momentum_ok = recent5_move >= 15 or recent15_move >= 35 or body >= 10
            if momentum_ok and structure_ok and not_chasing_high:
                entry = price
                candidates.append(_trade("SCALP NOW BUY", "Momentum Confirmation Buy", "BUY", entry, back_moves(entry, 20, "BUY"), add_moves(entry, 32, "BUY"), "TEST-B controlled upgrade: BUY bias + EMA alignment + candle/momentum confirmation. Designed to reduce MISSED BUY MOVE records.", mode, "A-"))
        elif bias == "SELL" and price < ema20 < ema50 and candle_dir == "SELL":
            not_chasing_low = not (price < prev_low and moves(prev_low, price) > NO_CHASE_MOVES)
            momentum_ok = recent5_move <= -15 or recent15_move <= -35 or body >= 10
            if momentum_ok and structure_ok and not_chasing_low:
                entry = price
                candidates.append(_trade("SCALP NOW SELL", "Momentum Confirmation Sell", "SELL", entry, back_moves(entry, 20, "SELL"), add_moves(entry, 32, "SELL"), "TEST-B controlled upgrade: SELL bias + EMA alignment + candle/momentum confirmation. Only allowed in bearish bias.", mode, "A-"))

    valid = [c for c in candidates if c["command"].startswith(("SCALP NOW", "TRADE NOW")) and _risk_approved(c)]
    if valid:
        best = sorted(valid, key=lambda s: (s.get("rr") or 0, s.get("reward_moves") or 0), reverse=True)[0]
        best["system_version"] = system_name
        return best

    # Plan-only, directionally aligned, if no approved entry.
    if bias == "BUY":
        return {**_empty("BUY setup forming but V3 has no approved entry yet. Wait for pullback, retest, or controlled momentum confirmation.", mode, price),
                "command": "PLAN ONLY — DO NOT ENTER", "strategy": "BUY SETUP FORMING", "direction": "BUY", "watch_level": round(prev_high, 5), "system_version": system_name}
    if bias == "SELL":
        return {**_empty("SELL setup forming but V3 has no approved entry yet. Wait for pullback, retest, or controlled momentum confirmation.", mode, price),
                "command": "PLAN ONLY — DO NOT ENTER", "strategy": "SELL SETUP FORMING", "direction": "SELL", "watch_level": round(prev_low, 5), "system_version": system_name}

    return _empty("No clean strategy event.", mode, price)
