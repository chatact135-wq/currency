from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Dubai")

def now_uae():
    return datetime.now(TZ)

def next_time(hour, minute=0):
    now = now_uae()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target

def seconds_until(dt):
    return max(0, int((dt - now_uae()).total_seconds()))

def session_info():
    now = now_uae()
    mins = now.hour * 60 + now.minute
    if (16 * 60 + 30) <= mins <= (20 * 60):
        name, score = "London/New York Overlap", 0.18
    elif (11 * 60) <= mins <= (20 * 60):
        name, score = "London Session", 0.10
    elif mins >= (16 * 60 + 30) or mins <= 60:
        name, score = "New York Session", 0.10
    elif (2 * 60) <= mins <= (9 * 60):
        name, score = "Low Liquidity", -0.12
    else:
        name, score = "Normal Hours", 0.0
    return {
        "name": name,
        "score": score,
        "uae_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "london_open_countdown": seconds_until(next_time(11, 0)),
        "new_york_open_countdown": seconds_until(next_time(16, 30)),
        "overlap_countdown": seconds_until(next_time(16, 30)),
    }

def default_news_countdown():
    return {
        "event": "Next common high-impact US/London news window",
        "countdown_seconds": seconds_until(next_time(16, 30)),
        "warning_window_minutes": 30,
    }
