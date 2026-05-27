from app.services.market_data import get_market_candles, normalize_asset
from app.services.indicators import build_indicators
from app.services.news_sentiment import analyze_news
from app.services.ml_engine import ml_probability
def generate_signal(asset: str):
    symbol=normalize_asset(asset)
    candles=get_market_candles(symbol)
    price=candles[-1]['close']
    indicators=build_indicators(candles)
    news=analyze_news(symbol)
    ml=ml_probability(indicators, news['score'])
    risk='High' if indicators['volatility']>0.35 else 'Medium' if indicators['volatility']>0.18 else 'Low'
    reasons=ml['reasons']+[f"RSI: {indicators['rsi']}", f"EMA20: {indicators['ema_fast']}", f"EMA50: {indicators['ema_slow']}", news['headline']]
    return {'asset':symbol,'price':price,'signal':ml['signal'],'confidence':ml['confidence'],'risk_level':risk,'trend':indicators['trend'],'news_sentiment':news['sentiment'],'reasons':reasons}
