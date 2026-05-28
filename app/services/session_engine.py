from datetime import datetime
from zoneinfo import ZoneInfo
def get_market_session():
    now=datetime.now(ZoneInfo('Asia/Dubai')); m=now.hour*60+now.minute
    if 16*60+30 <= m <= 20*60: return {'name':'London + New York Overlap','quality':'best','score':0.18,'message':'Best liquidity window for EURUSD, GBPUSD, gold, and oil.'}
    if 11*60 <= m <= 20*60: return {'name':'London Session','quality':'good','score':0.10,'message':'Good liquidity, especially for EURUSD and GBPUSD.'}
    if m >= 16*60+30 or m <= 60: return {'name':'New York Session','quality':'good','score':0.10,'message':'Good movement for USD pairs, gold, and oil.'}
    if 2*60 <= m <= 9*60: return {'name':'Low Liquidity Hours','quality':'weak','score':-0.12,'message':'Lower liquidity. Avoid forcing trades unless signal is very strong.'}
    return {'name':'Normal Market Hours','quality':'normal','score':0.0,'message':'Normal liquidity. Wait for clean price zones.'}
