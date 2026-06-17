from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

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
    if len(df) < 10:
        return False
    if direction == "bullish":
        for i in range(-7, -2):
            candle = df.iloc[i]
            if candle['close'] < candle['open']:
                next_candle = df.iloc[i+1]
                if next_candle['close'] > next_candle['open'] and next_candle['close'] > candle['high']:
                    return True
        return False
    else:
        for i in range(-7, -2):
            candle = df.iloc[i]
            if candle['close'] > candle['open']:
                next_candle = df.iloc[i+1]
                if next_candle['close'] < next_candle['open'] and next_candle['close'] < candle['low']:
                    return True
        return False

def detect_fvg(df: pd.DataFrame, direction: str) -> bool:
    if len(df) < 5:
        return False
    for i in range(-5, -2):
        c1 = df.iloc[i]
        c2 = df.iloc[i+1]
        c3 = df.iloc[i+2]
        if direction == "bullish":
            if c1['high'] < c3['low'] and c2['low'] > c1['high']:
                return True
        else:
            if c1['low'] > c3['high'] and c2['high'] < c1['low']:
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

def check_structure_break(df: pd.DataFrame, direction: str) -> bool:
    if len(df) < 12:
        return False
    current_price = float(df['close'].iloc[-1])
    if direction == "SELL":
        swing_high = df['high'].iloc[-8:-2].max()
        if current_price > swing_high + 0.0003:
            if df['close'].iloc[-2] > swing_high and df['close'].iloc[-1] > swing_high:
                return True
        return False
    else:
        swing_low = df['low'].iloc[-8:-2].min()
        if current_price < swing_low - 0.0003:
            if df['close'].iloc[-2] < swing_low and df['close'].iloc[-1] < swing_low:
                return True
        return False

def is_high_probability_session() -> bool:
    try:
        local_time = datetime.now(timezone.utc) + timedelta(hours=4)
        hour = local_time.hour
        return (8 <= hour < 12) or (13 <= hour < 17)
    except:
        return True

def analyze_symbol(symbol: str, df_m15: pd.DataFrame, df_h4: pd.DataFrame = None, df_daily: pd.DataFrame = None) -> Dict[str, Any]:
    if len(df_m15) < 60:
        return {"signal": "NO TRADE", "reason": "Insufficient data", "confidence": 0}

    if not is_high_probability_session():
        return {
            "signal": "NO TRADE",
            "reason": "Outside high probability trading hours",
            "confidence": 0,
            "price": float(df_m15['close'].iloc[-1])
        }

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

    # 1. Strong Trend
    m15_bullish = current_price > df['ema_50'].iloc[-1] > df['ema_200'].iloc[-1]
    m15_bearish = current_price < df['ema_50'].iloc[-1] < df['ema_200'].iloc[-1]
    
    if m15_bullish:
        score += 22
        reasons.append("Strong bullish trend (M15)")
    elif m15_bearish:
        score += 22
        reasons.append("Strong bearish trend (M15)")

    # 2. Market Structure
    if structure == "bullish_bos":
        score += 20
        reasons.append("Bullish Break of Structure")
    elif structure == "bearish_bos":
        score += 20
        reasons.append("Bearish Break of Structure")

    # 3. Order Block
    if m15_bullish and find_order_block(df, "bullish"):
        score += 15
        reasons.append("Bullish Order Block")
    elif m15_bearish and find_order_block(df, "bearish"):
        score += 15
        reasons.append("Bearish Order Block")

    # 4. Fair Value Gap
    if m15_bullish and detect_fvg(df, "bullish"):
        score += 12
        reasons.append("Bullish Fair Value Gap")
    elif m15_bearish and detect_fvg(df, "bearish"):
        score += 12
        reasons.append("Bearish Fair Value Gap")

    # 5. RSI
    rsi = df['rsi'].iloc[-1]
    if 48 < rsi < 62:
        score += 10
        reasons.append("Healthy momentum (RSI)")

    # 6. Volatility
    if atr > df['atr_ma'].iloc[-1] * 0.9:
        score += 8
        reasons.append("Good volatility")

    # 7. H4 + Daily Bias
    if df_h4 is not None and len(df_h4) >= 30:
        h4_ema50 = df_h4['close'].ewm(span=50).mean().iloc[-1]
        if (m15_bullish and current_price > h4_ema50) or (m15_bearish and current_price < h4_ema50):
            score += 10
            reasons.append("H4 bias aligned")

    if df_daily is not None and len(df_daily) >= 20:
        daily_ema200 = df_daily['close'].ewm(span=200).mean().iloc[-1]
        if (m15_bullish and current_price > daily_ema200) or (m15_bearish and current_price < daily_ema200):
            score += 8
            reasons.append("Daily bias aligned")

    # 8. Strong Candle
    if m15_bullish and detect_strong_candle(df, "bullish"):
        score += 18
        reasons.append("Strong bullish candle confirmation")
    elif m15_bearish and detect_strong_candle(df, "bearish"):
        score += 18
        reasons.append("Strong bearish candle confirmation")

    min_score = 78

    if score >= min_score and (m15_bullish or m15_bearish):
        
        if m15_bullish:
            direction = "BUY"
            entry = round(current_price, 5)
            stop_loss = round(current_price - (atr * 1.25), 5)
            take_profit = round(current_price + (atr * 2.1), 5)
            confidence = min(score + 5, 93)
        else:
            direction = "SELL"
            entry = round(current_price, 5)
            stop_loss = round(current_price + (atr * 1.25), 5)
            take_profit = round(current_price - (atr * 2.1), 5)
            confidence = min(score + 5, 93)
            
        structure_broken = check_structure_break(df, direction)
        
        if structure_broken:
            return {
                "signal": "NO TRADE",
                "reason": "Signal invalidated - Structure broken",
                "confidence": confidence,
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
            "expected_move_minutes": "20-50",
            "timeframe": "Advanced Professional (Structure + OB + FVG + Multi-TF)"
        }
    
    else:
        detailed_reason = f"Low confluence (score: {score}). "
        if structure == "ranging":
            detailed_reason += "Ranging market. "
            
        return {
            "signal": "NO TRADE",
            "reason": detailed_reason.strip(),
            "confidence": max(score, 0),
            "price": current_price
        }