ASSET_WEIGHTS={
'EURUSD':{'smc':1.15,'sb':1.15,'profile':1.0,'raven':0.85,'trend':0.75,'news':1.0},
'GBPUSD':{'smc':1.1,'sb':1.0,'profile':0.95,'raven':0.9,'trend':0.7,'news':1.15},
'XAUUSD':{'smc':1.2,'sb':1.15,'profile':1.2,'raven':1.25,'trend':0.7,'news':1.25},
'WTI':{'smc':0.75,'sb':0.75,'profile':1.35,'raven':0.9,'trend':0.6,'news':1.5}}
def w(asset): return ASSET_WEIGHTS.get(asset,ASSET_WEIGHTS['EURUSD'])
