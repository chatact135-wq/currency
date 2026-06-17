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

def detect_strong_candle(df: pd.DataFrame, direction: str) -> bool:
    """Require a strong momentum candle for entry"""
    if len(df) < 2:
        return False
    
    last = df.iloc[-1]
    body = abs(last['close'] - last['open'])
    candle_range = last['high'] - last['low']
    
    if candle_range == 0:
        return False
    
    strong_body = body > (candle_range * 0.55)  # Strong body
    
    if direction == "bullish":
        return last['close'] > last['open'] and strong_body
    else:
        return last['close'] < last['open'] and strong_body

def analyze_symbol(symbol: str, df_m15: pd.DataFrame, df_h4: pd.DataFrame = None) -> Dict[str, Any]:
    """
    EdgeFlow Pro - Balanced Accurate Short-Term Version
    Focus: Good quality signals + Reasonable frequency + Short-term moves
    """
    if len(df_m15) < 60:
        return {"signal": "NO TRADE", "reason": "Insufficient data", "confidence": 0}

    df = df_m15.copy()
    
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

    # === 1. M15 Trend (Core) ===
    m15_bullish = current_price > df['ema_50'].iloc[-1] > df['ema_200'].iloc[-1]
    m15_bearish = current_price < df['ema_50'].iloc[-1] < df['ema_200'].iloc[-1]
    
    if m15_bullish:
        score += 28
        reasons.append("Strong bullish trend (M15)")
    elif m15_bearish:
        score += 28
        reasons.append("Strong bearish trend (M15)")

    # === 2. Market Structure ===
    if structure == "bullish":
        score += 22
        reasons.append("Bullish market structure (M15)")
    elif structure == "bearish":
        score += 22
        reasons.append("Bearish market structure (M15)")

    # === 3. RSI Momentum ===
    rsi = df['rsi'].iloc[-1]
    if 47 < rsi < 63:
        score += 14
        reasons.append("Healthy momentum (RSI)")

    # === 4. Volatility ===
    if atr > df['atr_ma'].iloc[-1] * 0.88:
        score += 12
        reasons.append("Good volatility")

    # === 5. H4 Bias (Very light - almost neutral) ===
    if df_h4 is not None and len(df_h4) >= 30:
        h4_ema50 = df_h4['close'].ewm(span=50).mean().iloc[-1]
        h4_structure = detect_market_structure(df_h4)
        
        if (m15_bullish and current_price > h4_ema50 and h4_structure == "bullish") or \
           (m15_bearish and current_price < h4_ema50 and h4_structure == "bearish"):
            score += 10
            reasons.append("H4 aligned with M15")

    # === 6. Strong Candle Confirmation (Important for short-term) ===
    if m15_bullish and detect_strong_candle(df, "bullish"):
        score += 20
        reasons.append("Strong bullish candle")
    elif m15_bearish and detect_strong_candle(df, "bearish"):
        score += 20
        reasons.append("Strong bearish candle")

    # === Final Decision ===
    min_score = 70   # Slightly stricter for better quality

    if score >= min_score and (m15_bullish or m15_bearish):
        
        if m15_bullish:
            direction = "BUY"
            entry = round(current_price, 5)
            stop_loss = round(current_price - (atr * 1.15), 5)
            take_profit = round(current_price + (atr * 1.9), 5)
            confidence = min(score + 4, 91)
        else:
            direction = "SELL"
            entry = round(current_price, 5)
            stop_loss = round(current_price + (atr * 1.15), 5)
            take_profit = round(current_price - (atr * 1.9), 5)
            confidence = min(score + 4, 91)
            
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
            "expected_move_minutes": "15-45",
            "timeframe": "Balanced Short-Term (M15 + Candle)"
        }
    
    else:
        detailed_reason = f"Low confluence (score: {score}). "
        if structure == "ranging":
            detailed_reason += "Ranging market. "
        if not (m15_bullish or m15_bearish):
            detailed_reason += "No clear M15 trend. "
            
        return {
            "signal": "NO TRADE",
            "reason": detailed_reason.strip(),
            "confidence": max(score, 0),
            "price": current_price,
            "reasons": reasons
        }