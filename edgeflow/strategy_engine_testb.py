from __future__ import annotations
import pandas as pd
from .indicators import add_indicators
from .market_mode import detect_market_mode
from .utils import signed_moves, moves, add_moves, back_moves, rr
from .strategy_engine_test import analyze_symbol_test


def _early_signal(command: str, strategy: str, direction: str, price: float, reason: str, mode: dict, watch_level: float | None = None, early_score: int = 0) -> dict:
    """Early warning only. It is designed to appear before SCALP NOW.
    It must not be treated as an entry signal by the UI rule.
    """
    entry = price
    # Wider stop and smaller target are display-only planning levels, not entry permission.
    if direction == "SELL":
        stop = back_moves(entry, 14, "SELL")
        target = add_moves(entry, 18, "SELL")
    elif direction == "BUY":
        stop = back_moves(entry, 14, "BUY")
        target = add_moves(entry, 18, "BUY")
    else:
        stop = target = None

    risk = reward = ratio = None
    if stop is not None and target is not None:
        risk, reward, ratio = rr(entry, stop, target, direction)

    return {
        "command": command,
        "strategy": strategy,
        "direction": direction,
        "entry": round(entry, 5),
        "stop": round(stop, 5) if stop is not None else None,
        "target": round(target, 5) if target is not None else None,
        "risk_moves": round(risk, 1) if risk is not None else None,
        "reward_moves": round(reward, 1) if reward is not None else None,
        "rr": round(ratio, 2) if ratio is not None else None,
        "price": round(price, 5),
        "reason": reason,
        "market_mode": mode,
        "quality": "EARLY-WATCH",
        "watch_level": round(watch_level, 5) if watch_level is not None else None,
        "early_score": early_score,
        "engine_variant": "testb",
    }


def analyze_symbol_testb(symbol: str, df: pd.DataFrame, spread_moves: float | None = None) -> dict:
    """TestB: earlier prediction / pressure warning layer.

    Priority:
    1) Keep /test confirmed SCALP NOW signals unchanged when they are ready.
    2) If /test says PLAN ONLY, detect earlier pressure and show EARLY BUY/SELL WATCH.
    3) Never convert early watch into trade permission. User still waits for SCALP NOW.
    """
    confirmed = analyze_symbol_test(symbol, df, spread_moves=spread_moves)
    if confirmed.get("command", "").startswith(("SCALP NOW", "TRADE NOW", "MOVE MISSED", "NO TRADE — DANGER")):
        confirmed["engine_variant"] = "testb"
        if confirmed.get("strategy") and "(Test)" in confirmed["strategy"]:
            confirmed["strategy"] = confirmed["strategy"].replace("(Test)", "(TestB)")
        return confirmed

    if len(df) < 80:
        confirmed["engine_variant"] = "testb"
        return confirmed

    x = add_indicators(df).dropna().reset_index(drop=True)
    if len(x) < 30:
        confirmed["engine_variant"] = "testb"
        return confirmed

    mode = detect_market_mode(df)
    last = x.iloc[-1]
    prev1 = x.iloc[-2]
    prev2 = x.iloc[-3]
    prev3 = x.iloc[-4]

    price = float(last["close"])
    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])
    body = float(last["body_moves"])
    atr = float(last["atr14_moves"]) if pd.notna(last["atr14_moves"]) else 0
    candle_dir = last["direction"]

    recent3_move = signed_moves(float(x.iloc[-3]["open"]), price)
    recent5_move = signed_moves(float(x.iloc[-5]["open"]), price)
    recent15_move = signed_moves(float(x.iloc[-15]["open"]), price)

    recent_high_12 = float(x["high"].shift(1).tail(12).max())
    recent_low_12 = float(x["low"].shift(1).tail(12).min())
    recent_high_20 = float(x["high"].shift(1).tail(20).max())
    recent_low_20 = float(x["low"].shift(1).tail(20).min())

    last3 = [prev2["direction"], prev1["direction"], last["direction"]]
    red_count = sum(1 for d in last3 if d == "SELL")
    green_count = sum(1 for d in last3 if d == "BUY")

    # Pressure score. This intentionally triggers before full breakout confirmation.
    sell_score = 0
    buy_score = 0

    if price < ema20: sell_score += 1
    if price < ema20 < ema50: sell_score += 2
    if recent3_move <= -6: sell_score += 1
    if recent5_move <= -10: sell_score += 1
    if recent15_move <= -18: sell_score += 1
    if red_count >= 2: sell_score += 1
    if candle_dir == "SELL" and body >= 3: sell_score += 1
    if float(last["high"]) >= ema20 and price < ema20: sell_score += 1  # failed EMA touch
    if moves(price, recent_low_12) <= 8 and price > recent_low_12: sell_score += 1  # near breakdown
    if float(last["high"]) > recent_high_20 and price < recent_high_20: sell_score += 2  # sweep rejection

    if price > ema20: buy_score += 1
    if price > ema20 > ema50: buy_score += 2
    if recent3_move >= 6: buy_score += 1
    if recent5_move >= 10: buy_score += 1
    if recent15_move >= 18: buy_score += 1
    if green_count >= 2: buy_score += 1
    if candle_dir == "BUY" and body >= 3: buy_score += 1
    if float(last["low"]) <= ema20 and price > ema20: buy_score += 1  # held EMA touch
    if moves(price, recent_high_12) <= 8 and price < recent_high_12: buy_score += 1  # near breakout
    if float(last["low"]) < recent_low_20 and price > recent_low_20: buy_score += 2  # sweep rejection

    # SELL bias is preferred during sell-pressure because previous testing showed BUY scalp was weak there.
    if mode.get("bias") == "SELL" or mode.get("mode") == "TREND SELL":
        sell_score += 1
        buy_score -= 1
    elif mode.get("bias") == "BUY" or mode.get("mode") == "TREND BUY":
        buy_score += 1
        sell_score -= 1

    # Avoid early signals during extreme danger/chop.
    if mode.get("mode") in ["DANGER", "CHOPPY", "NO DATA"] or atr >= 35:
        confirmed["engine_variant"] = "testb"
        return confirmed

    if sell_score >= 5 and sell_score >= buy_score + 2:
        return _early_signal(
            "EARLY SELL WATCH — WAIT",
            "Early Momentum Pressure Sell (TestB)",
            "SELL",
            price,
            "TestB early warning: sell pressure is building before full confirmation. Do not enter yet; prepare for SCALP NOW SELL only if breakdown/follow-through confirms.",
            mode,
            watch_level=recent_low_12,
            early_score=sell_score,
        )

    if buy_score >= 5 and buy_score >= sell_score + 2:
        return _early_signal(
            "EARLY BUY WATCH — WAIT",
            "Early Momentum Pressure Buy (TestB)",
            "BUY",
            price,
            "TestB early warning: buy pressure is building before full confirmation. Do not enter yet; prepare for SCALP NOW BUY only if breakout/follow-through confirms.",
            mode,
            watch_level=recent_high_12,
            early_score=buy_score,
        )

    confirmed["engine_variant"] = "testb"
    if confirmed.get("strategy") and "(Test)" in confirmed["strategy"]:
        confirmed["strategy"] = confirmed["strategy"].replace("(Test)", "(TestB)")
    return confirmed
