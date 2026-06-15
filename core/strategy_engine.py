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

def analyze_symbol(symbol: str, df_m15: pd.DataFrame, df_h4: pd.DataFrame = None) -> Dict[str, Any]:
    """
    EdgeFlow Pro v2 - High Confluence Strategy Engine with H4 Filter
    Focused on EUR/USD and GBP/USD
    """
    if len(df_m15) < 60:
        return {"signal": "NO TRADE", "reason": "Insufficient data", "confidence": 0}

    df = df_m15.copy()
    
    # M15 Indicators
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

    # === M15 Trend Alignment ===
    if current_price > df['ema_50'].iloc[-1] > df['ema_200'].iloc[-1]:
        score += 30
        reasons.append("Strong bullish trend (M15)")
    elif current_price < df['ema_50'].iloc[-1] < df['ema_200'].iloc[-1]:
        score += 30
        reasons.append("Strong bearish trend (M15)")

    # === M15 Market Structure ===
    if structure == "bullish":
        score += 25
        reasons.append("Bullish market structure (M15)")
    elif structure == "bearish":
        score += 25
        reasons.append("Bearish market structure (M15)")

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

    # === H4 Filter (Less Strict Version) ===
    h4_aligned = True
    if df_h4 is not None and len(df_h4) >= 30:
        h4_ema50 = df_h4['close'].ewm(span=50).mean().iloc[-1]
        h4_structure = detect_market_structure(df_h4)
        
        if current_price > h4_ema50 and h4_structure == "bullish":
            score += 15
            reasons.append("H4 trend aligned (bullish)")
        elif current_price < h4_ema50 and h4_structure == "bearish":
            score += 15
            reasons.append("H4 trend aligned (bearish)")
        else:
            h4_aligned = False
            score -= 8   # Much smaller penalty
            reasons.append("H4 not fully aligned (minor reduction)")

    # === Final Decision (same threshold regardless of H4) ===
    min_score = 68

    if score >= min_score:
        direction = "BUY"
        entry = round(current_price, 5)
        stop_loss = round(current_price - (atr * 1.2), 5)
        take_profit = round(current_price + (atr * 2.0), 5)
        confidence = min(score + 3, 93)
    elif score <= (100 - min_score):
        direction = "SELL"
        entry = round(current_price, 5)
        stop_loss = round(current_price + (atr * 1.2), 5)
        take_profit = round(current_price - (atr * 2.0), 5)
        confidence = min(100 - score + 3, 93)
    else:
        detailed_reason = f"Low confluence (score: {score}). "
        if not h4_aligned:
            detailed_reason += "H4 not fully aligned. "
        if structure == "ranging":
            detailed_reason += "Ranging on M15. "
        
        return {
            "signal": "NO TRADE",
            "reason": detailed_reason.strip(),
            "confidence": max(score, 0),
            "price": current_price,
            "reasons": reasons
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
        "timeframe": "M15 + H4 Filtered Confluence"
    }
