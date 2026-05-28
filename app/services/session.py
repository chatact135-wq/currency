from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
TZ = ZoneInfo("Asia/Dubai")

def now():
    return datetime.now(TZ)

def next_at(h, m=0):
    n = now()
    t = n.replace(hour=h, minute=m, second=0, microsecond=0)
    if t <= n:
        t += timedelta(days=1)
    return t

def secs(dt):
    return max(0, int((dt - now()).total_seconds()))

def info():
    n = now()
    minutes = n.hour * 60 + n.minute
    if 16*60+30 <= minutes <= 20*60:
        name, score = "London/New York Overlap", 10
    elif 11*60 <= minutes <= 20*60:
        name, score = "London Session", 6
    elif minutes >= 16*60+30 or minutes <= 60:
        name, score = "New York Session", 6
    elif 2*60 <= minutes <= 9*60:
        name, score = "Low Liquidity", -8
    else:
        name, score = "Normal Hours", 0
    return {
        "name": name,
        "score": score,
        "uae_time": n.strftime("%Y-%m-%d %H:%M:%S"),
        "london_countdown": secs(next_at(11,0)),
        "ny_countdown": secs(next_at(16,30)),
        "news_countdown": secs(next_at(16,30)),
    }
