from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Dubai')
def now(): return datetime.now(TZ)
def nxt(h,m=0):
    n=now(); t=n.replace(hour=h,minute=m,second=0,microsecond=0)
    return t+timedelta(days=1) if t<=n else t
def secs(t): return max(0,int((t-now()).total_seconds()))
def session():
    n=now(); mins=n.hour*60+n.minute
    if 16*60+30<=mins<=20*60: name,score='London/New York Overlap',16
    elif 11*60<=mins<=20*60: name,score='London Session',10
    elif mins>=16*60+30 or mins<=60: name,score='New York Session',10
    elif 2*60<=mins<=9*60: name,score='Low Liquidity',-15
    else: name,score='Normal Hours',0
    return {'name':name,'score':score,'uae_time':n.strftime('%Y-%m-%d %H:%M:%S'),'london_open_countdown':secs(nxt(11,0)),'new_york_open_countdown':secs(nxt(16,30)),'overlap_countdown':secs(nxt(16,30)),'news_window_countdown':secs(nxt(16,30))}
