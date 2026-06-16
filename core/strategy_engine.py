from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Any
from datetime import datetime, timezone

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

def detect_candlestick_confirmation(df: pd.DataFrame, direction: str) -> bool:
    """
    Simple but effective candlestick confirmation
    """
    if len(df) < 3:
        return False
    
    last_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]
    
    body = abs(last_candle['close'] - last_candle['open'])
    candle_range = last_candle['high'] - last_candle['low']
    
    if candle_range == 0:
        return False
    
    # Strong momentum candle (body > 60% of range)
    strong_body = body > (candle_range * 0.6)
    
    if direction == "bullish":
        # Bullish confirmation: strong green candle closing near high
        is_bullish = last_candle['close'] > last_candle['open']
        closes_strong = last_candle['close'] > (last_candle['high'] - body * 0.3)
        return is_bullish and strong_body and closes_strong
    
    elif direction == "bearish":
        # Bearish confirmation: strong red candle closing near low
        is_bearish = last_candle['close'] < last_candle['open']
        closes_strong = last_candle['close'] < (last_candle['low'] + body * 0.3)
        return is_bearish and strong_body and closes_strong
    
    return False

def get_swing_stop_loss(df: pd.DataFrame, direction: str, atr: float) -> float:
    """
    Use recent swing for more logical stop loss
    """
    if len(df) < 10:
        current_price = float(df['close'].iloc[-1])
        if direction == "BUY":
            return round(current_price - (atr * 1.3), 5)
        else:
            return round(current_price + (atr * 1.3), 5)
    
    if direction == "BUY":
        # For BUY, stop below recent swing low
        swing_low = df['low'].iloc[-8:].min()
        current_price = float(df['close'].iloc[-1])
        # Use the better (tighter but logical) of swing or ATR
        atr_sl = current_price - (atr * 1.3)
        return round(max(swing_low - 0.0001, atr_sl), 5)
    else:
        # For SELL, stop above recent swing high
        swing_high = df['high'].iloc[-8:].max()
        current_price = float(df['close'].iloc[-1])
        atr_sl = current_price + (atr * 1.3)
        return round(min(swing_high + 0.0001, atr_sl), 5)

def analyze_symbol(symbol: str, df_m15: pd.DataFrame, df_h4: pd.DataFrame = None) -> Dict[str, Any]:
    """
    EdgeFlow Pro - Smart Confluence Version
    Professional-grade logic with H4 direction filter + Candle confirmation
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
    h4_direction = None

    # === 1. H4 Direction Filter (Mandatory) ===
    h4_bullish = False
    h4_bearish = False
    
    if df_h4 is not None and len(df_h4) >= 30:
        h4_ema50 = df_h4['close'].ewm(span=50).mean().iloc[-1]
        h4_structure = detect_market_structure(df_h4)
        
        if current_price > h4_ema50 and h4_structure == "bullish":
            h4_bullish = True
            h4_direction = "bullish"
            score += 25
            reasons.append("H4 strongly bullish")
        elif current_price < h4_ema50 and h4_structure == "bearish":
            h4_bearish = True
            h4_direction = "bearish"
            score += 25
            reasons.append("H4 strongly bearish")
        else:
            # H4 not clearly aligned - we will be stricter later
            reasons.append("H4 direction unclear")

    # === 2. M15 Trend Alignment ===
    m15_bullish = current_price > df['ema_50'].iloc[-1] > df['ema_200'].iloc[-1]
    m15_bearish = current_price < df['ema_50'].iloc[-1] < df['ema_200'].iloc[-1]
    
    if m15_bullish:
        score += 25
        reasons.append("Strong bullish trend (M15)")
    elif m15_bearish:
        score += 25
        reasons.append("Strong bearish trend (M15)")

    # === 3. Market Structure ===
    if structure == "bullish":
        score += 20
        reasons.append("Bullish market structure (M15)")
    elif structure == "bearish":
        score += 20
        reasons.append("Bearish market structure (M15)")

    # === 4. RSI Momentum ===
    rsi = df['rsi'].iloc[-1]
    if 48 < rsi < 62:
        score += 12
        reasons.append("Healthy momentum (RSI)")
    elif rsi < 38:
        score += 8
        reasons.append("Oversold - possible reversal")

    # === 5. Volatility ===
    if atr > df['atr_ma'].iloc[-1] * 0.9:
        score += 10
        reasons.append("Good volatility")

    # === 6. Candlestick Confirmation (Important) ===
    candle_confirmed = False
    if m15_bullish or (h4_bullish and not m15_bearish):
        if detect_candlestick_confirmation(df, "bullish"):
            score += 15
            reasons.append("Strong bullish candle confirmation")
            candle_confirmed = True
    elif m15_bearish or (h4_bearish and not m15_bullish):
        if detect_candlestick_confirmation(df, "bearish"):
            score += 15
            reasons.append("Strong bearish candle confirmation")
            candle_confirmed = True

    # === Final Decision Logic (H4 is now STRICTLY MANDATORY) ===
    
    has_trend = m15_bullish or m15_bearish
    has_h4_support = (m15_bullish and h4_bullish) or (m15_bearish and h4_bearish)
    
    min_score = 70

    # If we have trend but H4 does not support it → NO TRADE
    if has_trend and not has_h4_support:
        return {
            "signal": "NO TRADE",
            "reason": "H4 direction does not support M15 move",
            "confidence": score,
            "price": current_price,
            "reasons": reasons
        }
    
    if score >= min_score and has_h4_support:
        
        if m15_bullish:
            direction = "BUY"
            entry = round(current_price, 5)
            stop_loss = get_swing_stop_loss(df, direction, atr)
            take_profit = round(current_price + (atr * 2.2), 5)
            confidence = min(score + 5, 92)
        else:
            direction = "SELL"
            entry = round(current_price, 5)
            stop_loss = get_swing_stop_loss(df, direction, atr)
            take_profit = round(current_price - (atr * 2.2), 5)
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
            "expected_move_minutes": "30-80",
            "timeframe": "H4 Mandatory + Candle Confirmation"
        }
    
    else:
        detailed_reason = f"Low confluence (score: {score}). "
        if structure == "ranging":
            detailed_reason += "Ranging on M15. "
            
        return {
            "signal": "NO TRADE",
            "reason": detailed_reason.strip(),
            "confidence": max(score, 0),
            "price": current_price,
            "reasons": reasons
        }