def ml_probability(indicators: dict, sentiment_score: float) -> dict:
    score=0.0; reasons=[]
    trend=indicators['trend']; rsi=indicators['rsi']; vol=indicators['volatility']
    if trend=='bullish': score+=0.28; reasons.append('EMA trend is bullish')
    elif trend=='bearish': score-=0.28; reasons.append('EMA trend is bearish')
    if rsi<30: score+=0.22; reasons.append('RSI indicates oversold recovery possibility')
    elif rsi>70: score-=0.22; reasons.append('RSI indicates overbought pullback risk')
    else: reasons.append('RSI is in a normal range')
    if sentiment_score>0.1: score+=0.18; reasons.append('News sentiment is supportive')
    elif sentiment_score<-0.1: score-=0.18; reasons.append('News sentiment is negative')
    else: reasons.append('News sentiment is neutral')
    if vol>0.35: score*=0.75; reasons.append('Volatility is elevated, confidence reduced')
    signal='BUY' if score>0.18 else 'SELL' if score<-0.18 else 'WAIT'
    confidence=min(92, max(55, 55+abs(score)*100))
    return {'signal':signal,'confidence':round(confidence,2),'reasons':reasons,'score':round(score,4)}
