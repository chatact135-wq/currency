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
    """Improved Market Structure detection (BOS style)"""
    if len(df) < 25:
        return "neutral"
    
    recent_high = df['high'].iloc[-5:].max()
    recent_low = df['low'].iloc[-5:].min()
    prev_high = df['high'].iloc[-15:-5].max()
    prev_low = df['low'].iloc[-15:-5].min()
    
    if recent_high > prev_high and recent_low > prev_low:
        return "bullish_bos"
    elif recent_high < prev_high and recent_low < prev_low:
        return "bearish_bos"
    return "ranging"

def find_order_block(df: pd.DataFrame, direction: str) -> bool:
    """Simple Order Block detection"""
    if len(df) < 10:
        return False
    
    if direction == "bullish":
        for i in range(-6, -2):
            candle = df.iloc[i]
            if candle['close'] < candle['open']:
                next_candle = df.iloc[i+1]
                if next_candle['close'] > next_candle['open'] and next_candle['close'] > candle['high']:
                    return True
        return False
    else:
        for i in range(-6, -2):
            candle = df.iloc[i]
            if candle['close'] > candle['open']:
                next_candle = df.iloc[i+1]
                if next_candle['close'] < next_candle['open'] and next_candle['close'] < candle['low']:
                    return True
        return False

def detect_strong_candle(df: pd.DataFrame, direction: str) -> bool:
    if len(df) < 2:
        return False
    last = df.iloc[-1]
    body = abs(last['close'] - last['open'])
    candle_range = last['high'] - last['low']
    if candle_range == 0:
        return False
    strong_body = body > (candle_range * 0.6)
    if direction == "bullish":
        return last['close'] > last['open'] and strong_body
    else:
        return last['close'] < last['open'] and strong_body

def analyze_symbol(symbol: str, df_m15: pd.DataFrame, df_h4: pd.DataFrame = None) -> Dict[str, Any]:
    """
    EdgeFlow Pro - Professional Version
    Best combination of Trend, Structure, Order Block, Candle & Confluence
    """
    if len(df_m15) < 60:
        return {"signal": "NO TRADE", "reason": "Insufficient data", "confidence": 0}

    df = df_m15.copy()
    
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

    # === 1. Strong Trend ===
    m15_bullish = current_price > df['ema_50'].iloc[-1] > df['ema_200'].iloc[-1]
    m15_bearish = current_price < df['ema_50'].iloc[-1] < df['ema_200'].iloc[-1]
    
    if m15_bullish:
        score += 25
        reasons.append("Strong bullish trend (M15)")
    elif m15_bearish:
        score += 25
        reasons.append("Strong bearish trend (M15)")

    # === 2. Market Structure (BOS) ===
    if structure == "bullish_bos":
        score += 22
        reasons.append("Bullish Break of Structure")
    elif structure == "bearish_bos":
        score += 22
        reasons.append("Bearish Break of Structure")

    # === 3. Order Block ===
    if m15_bullish and find_order_block(df, "bullish"):
        score += 15
        reasons.append("Bullish Order Block present")
    elif m15_bearish and find_order_block(df, "bearish"):
        score += 15
        reasons.append("Bearish Order Block present")

    # === 4. RSI Momentum ===
    rsi = df['rsi'].iloc[-1]
    if 48 < rsi < 62:
        score += 12
        reasons.append("Healthy momentum (RSI)")

    # === 5. Volatility ===
    if atr > df['atr_ma'].iloc[-1] * 0.9:
        score += 10
        reasons.append("Good volatility")

    # === 6. H4 Light Bias ===
    if df_h4 is not None and len(df_h4) >= 30:
        h4_ema50 = df_h4['close'].ewm(span=50).mean().iloc[-1]
        h4_structure = detect_market_structure(df_h4)
        if (m15_bullish and current_price > h4_ema50) or (m15_bearish and current_price < h4_ema50):
            score += 8
            reasons.append("H4 bias aligned")

    # === 7. Strong Candle Confirmation ===
    if m15_bullish and detect_strong_candle(df, "bullish"):
        score += 20
        reasons.append("Strong bullish candle confirmation")
    elif m15_bearish and detect_strong_candle(df, "bearish"):
        score += 20
        reasons.append("Strong bearish candle confirmation")

    # === Final Decision ===
    min_score = 72

    if score >= min_score and (m15_bullish or m15_bearish):
        
        if m15_bullish:
            direction = "BUY"
            entry = round(current_price, 5)
            stop_loss = round(current_price - (atr * 1.2), 5)
            take_profit = round(current_price + (atr * 2.0), 5)
            confidence = min(score + 5, 92)
        else:
            direction = "SELL"
            entry = round(current_price, 5)
            stop_loss = round(current_price + (atr * 1.2), 5)
            take_profit = round(current_price - (atr * 2.0), 5)
            confidence = min(score + 5, 92)
            
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
            "expected_move_minutes": "20-50",
            "timeframe": "Professional (Structure + OB + Candle)"
        }
    
    else:
        detailed_reason = f"Low confluence (score: {score}). "
        if structure == "ranging":
            detailed_reason += "Ranging / No clear structure. "
            
        return {
            "signal": "NO TRADE",
            "reason": detailed_reason.strip(),
            "confidence": max(score, 0),
            "price": current_price,
            "reasons": reasons
        }