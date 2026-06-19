import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    if len(df) < period:
        return 0.001
    high = df['high']
    low = df['low']
    close = df['close']
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean().iloc[-1]
    return round(atr, 5)

def detect_market_structure(df: pd.DataFrame) -> str:
    if len(df) < 10:
        return "neutral"
    recent_high = df['high'].iloc[-5:].max()
    recent_low = df['low'].iloc[-5:].min()
    current_price = float(df['close'].iloc[-1])
    
    if current_price > recent_high:
        return "bullish"
    elif current_price < recent_low:
        return "bearish"
    return "neutral"

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> float:
    if len(df) < period + 1:
        return 50.0
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1)

def get_signal(df_m15: pd.DataFrame, df_h4: pd.DataFrame = None) -> dict:
    if len(df_m15) < 20:
        return {"signal": "NO TRADE", "confidence": 0, "reasons": ["Not enough data"]}
    
    reasons = []
    current_price = float(df_m15['close'].iloc[-1])
    atr = calculate_atr(df_m15)
    
    # Market Structure
    structure = detect_market_structure(df_m15)
    if structure == "bullish":
        reasons.append("Bullish market structure (M15)")
    elif structure == "bearish":
        reasons.append("Bearish market structure (M15)")
    
    # RSI
    rsi = calculate_rsi(df_m15)
    if rsi < 35:
        reasons.append("Oversold - possible reversal")
    elif rsi > 65:
        reasons.append("Overbought - possible reversal")
    else:
        reasons.append("Healthy momentum (RSI)")
    
    # Volatility
    if atr > 0.0008:
        reasons.append("Sufficient volatility")
    
    # H4 Bias (if available)
    h4_bias = "neutral"
    if df_h4 is not None and len(df_h4) > 5:
        h4_structure = detect_market_structure(df_h4)
        if h4_structure == "bullish":
            h4_bias = "bullish"
            reasons.append("H4 bias bullish")
        elif h4_structure == "bearish":
            h4_bias = "bearish"
            reasons.append("H4 bias bearish")
    
    # Final Direction Decision
    direction = "NO TRADE"
    confidence = 55
    
    if structure == "bullish" and rsi < 70:
        direction = "BUY"
        confidence = 75
    elif structure == "bearish" and rsi > 30:
        direction = "SELL"
        confidence = 75
    
    # === Fix Contradictory Reasons Bug ===
    if direction == "BUY":
        reasons = [r for r in reasons if not any(word in r.lower() for word in ["bearish", "sell", "down"])]
    elif direction == "SELL":
        reasons = [r for r in reasons if not any(word in r.lower() for word in ["bullish", "buy", "up"])]
    
    if direction == "NO TRADE":
        reasons = ["Waiting for stronger alignment"]
    
    return {
        "signal": f"TRADE NOW {direction}" if direction != "NO TRADE" else "NO TRADE",
        "confidence": confidence,
        "reasons": reasons,
        "entry": round(current_price, 5),
        "atr": atr
    }