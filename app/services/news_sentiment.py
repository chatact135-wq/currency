def analyze_news(asset: str):
    asset=asset.upper()
    if asset in ['XAUUSD','GOLD']:
        return {'sentiment':'neutral','score':0.05,'headline':'Gold sentiment mixed while traders wait for macroeconomic data.'}
    if asset in ['WTI','OIL']:
        return {'sentiment':'positive','score':0.18,'headline':'Oil sentiment slightly positive due to supply-side concerns.'}
    return {'sentiment':'neutral','score':0.0,'headline':'Forex sentiment neutral until fresh central bank or inflation news.'}
