import pandas as pd
def calculate_rsi(closes, period:int=14)->float:
    series = pd.Series(closes, dtype='float64')
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 0.000001)
    rsi = 100 - (100/(1+rs))
    value = rsi.iloc[-1]
    return float(50 if pd.isna(value) else round(value,2))
def calculate_ema(closes, span:int)->float:
    return float(round(pd.Series(closes, dtype='float64').ewm(span=span, adjust=False).mean().iloc[-1],5))
def calculate_volatility(closes)->float:
    returns = pd.Series(closes, dtype='float64').pct_change().dropna()
    if len(returns)==0: return 0.0
    return float(round(returns.std()*100,4))
def build_indicators(candles):
    closes=[c['close'] for c in candles]
    rsi=calculate_rsi(closes); ema_fast=calculate_ema(closes,20); ema_slow=calculate_ema(closes,50); vol=calculate_volatility(closes)
    trend='bullish' if ema_fast>ema_slow else 'bearish' if ema_fast<ema_slow else 'neutral'
    return {'rsi':rsi,'ema_fast':ema_fast,'ema_slow':ema_slow,'volatility':vol,'trend':trend}
