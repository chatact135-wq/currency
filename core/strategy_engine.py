from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Any

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def detect_market_structure(df: pd.DataFrame) -> str:
    if len(df) < 20:
        return "neutral"
    
    recent_high = df['high'].iloc[-6:].max()
    recent_low = df['low'].iloc[-6:].min()
    prev_high = df['high'].iloc[-15:-6].max()
    prev_low = df['low'].iloc[-15:-6].min()
    
    if recent_high > prev_high and recent_low > prev_low:
        return "bullish"
    elif recent_high < prev_high and recent_low < prev_low:
        return "bearish"
    return "ranging"

def analyze_symbol(symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
    """
    EdgeFlow Pro v2 - High Confluence Strategy Engine
    Focused on EUR/USD and GBP/USD
    """
    if len(df) < 60:
        return {"signal": "NO TRADE", "reason": "Insufficient data", "confidence": 0}

    df = df.copy()
    
    # Indicators
    df['ema_50'] = df['close'].ewm(span=50).mean()
    df['ema_200'] = df['close'].ewm(span=200).mean()
    df['rsi'] = 100 - (100 / (1 + (df['close'].diff().clip(lower=0).rolling(14).mean() / 
                                   df['close'].diff().clip(upper=0).abs().rolling(14).mean())))
    df['atr'] = calculate_atr(df, 14)
    df['atr_ma'] = df['atr'].rolling(50).mean()

    current_price = float(df['close'].iloc[-1])
    atr = float(df['atr'].iloc[-1])
    structure = detect_market_structure(df)
    
    score = 0
    reasons = []

    # === Trend Alignment ===
    if current_price > df['ema_50'].iloc[-1] > df['ema_200'].iloc[-1]:
        score += 30
        reasons.append("Strong bullish trend")
    elif current_price < df['ema_50'].iloc[-1] < df['ema_200'].iloc[-1]:
        score += 30
        reasons.append("Strong bearish trend")

    # === Market Structure ===
    if structure == "bullish":
        score += 25
        reasons.append("Bullish market structure")
    elif structure == "bearish":
        score += 25
        reasons.append("Bearish market structure")

    # === RSI Filter ===
    rsi = df['rsi'].iloc[-1]
    if 45 < rsi < 65:
        score += 15
        reasons.append("Healthy momentum (RSI)")
    elif rsi < 35:
        score += 10
        reasons.append("Oversold - possible reversal")

    # === Volatility Filter ===
    if atr > df['atr_ma'].iloc[-1] * 0.85:
        score += 15
        reasons.append("Sufficient volatility")

    # === Final Decision (Balanced High-Quality Mode) ===
    if score >= 72:
        direction = "BUY"
        entry = round(current_price, 5)
        stop_loss = round(current_price - (atr * 1.2), 5)
        take_profit = round(current_price + (atr * 2.0), 5)
        confidence = min(score + 3, 93)
    elif score <= 28:
        direction = "SELL"
        entry = round(current_price, 5)
        stop_loss = round(current_price + (atr * 1.2), 5)
        take_profit = round(current_price - (atr * 2.0), 5)
        confidence = min(100 - score + 3, 93)
    else:
        return {
            "signal": "NO TRADE",
            "reason": "Low confluence - Waiting for better setup",
            "confidence": score,
            "price": current_price
        }

    return {
        "signal": f"TRADE NOW {direction}",
        "direction": direction,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": confidence,
        "reasons": reasons,
        "atr": round(atr, 5),
        "price": current_price,
        "expected_move_minutes": "25-70",
        "timeframe": "M15 + H4 Balanced Confluence"
    }
