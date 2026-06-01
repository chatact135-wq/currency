
from datetime import datetime, timedelta, timezone
import requests
from app.config import settings

WATCH_CURRENCIES=["USD","EUR","GBP"]
IMPORTANT=["CPI","INFLATION","NONFARM","NFP","PAYROLL","UNEMPLOYMENT","INTEREST RATE","RATE DECISION","FOMC","FED","POWELL","GDP","RETAIL SALES","PMI","ISM","PCE","CLAIMS","BOE","ECB"]

def now_utc(): return datetime.now(timezone.utc)

def parse_dt(v):
    if not v: return None
    s=str(v).replace("Z","+00:00")
    for fmt in [None,"%Y-%m-%d %H:%M:%S"]:
        try:
            dt=datetime.fromisoformat(s) if fmt is None else datetime.strptime(str(v)[:19],fmt).replace(tzinfo=timezone.utc)
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    return None

def text(seconds):
    if seconds is None: return "Unknown"
    if seconds < 0:
        seconds=abs(seconds)
        return f"released {round(seconds/60)} min ago" if seconds<3600 else f"released {round(seconds/3600,1)} h ago"
    if seconds<60: return "less than 1 min"
    return f"in {round(seconds/60)} min" if seconds<3600 else f"in {round(seconds/3600,1)} h"

def impact(e):
    title=(e.get("event") or e.get("title") or e.get("name") or e.get("indicator") or "").upper()
    imp=str(e.get("impact") or e.get("importance") or "").upper()
    if "HIGH" in imp: return "HIGH"
    if "MEDIUM" in imp: return "MEDIUM"
    return "HIGH" if any(k in title for k in IMPORTANT) else "LOW"

def normalize(e):
    title=e.get("event") or e.get("title") or e.get("name") or e.get("indicator") or "Economic event"
    cur=(e.get("currency") or e.get("country") or e.get("symbol") or "").upper()
    if "UNITED STATES" in cur or cur=="US": cur="USD"
    if "EURO" in cur or "EURO AREA" in cur: cur="EUR"
    if "UNITED KINGDOM" in cur or cur=="UK": cur="GBP"
    dt=parse_dt(e.get("date") or e.get("datetime") or e.get("time"))
    return {"title":title,"currency":cur[:3],"impact":impact(e),"date_utc":dt.isoformat() if dt else None,"timestamp":dt.timestamp() if dt else None,"actual":e.get("actual"),"forecast":e.get("forecast") or e.get("estimate") or e.get("consensus"),"previous":e.get("previous")}

def fetch_fmp():
    if not settings.FMP_API_KEY: return []
    n=now_utc()
    try:
        resp=requests.get("https://financialmodelingprep.com/api/v3/economic_calendar",params={"from":(n-timedelta(hours=6)).strftime("%Y-%m-%d"),"to":(n+timedelta(days=2)).strftime("%Y-%m-%d"),"apikey":settings.FMP_API_KEY},timeout=12)
        data=resp.json()
    except Exception:
        return []
    if not isinstance(data,list): return []
    return [normalize(x) for x in data]

def builtin():
    n=now_utc(); d=n.date()
    items=[("USD high-impact window / New York data risk","USD",12,30),("USD session news risk window","USD",14,0),("GBP London data risk","GBP",6,0),("EUR London/ECB data risk","EUR",8,0)]
    out=[]
    for title,cur,h,m in items:
        dt=datetime(d.year,d.month,d.day,h,m,tzinfo=timezone.utc)
        if dt<n-timedelta(hours=2): dt+=timedelta(days=1)
        out.append({"title":title,"currency":cur,"impact":"MEDIUM","date_utc":dt.isoformat(),"timestamp":dt.timestamp(),"actual":None,"forecast":None,"previous":None})
    return out

def relevant(asset,cur):
    a=asset.upper().replace("/","")
    if a=="EURUSD": return cur in ["EUR","USD"]
    if a=="GBPUSD": return cur in ["GBP","USD"]
    if a in ["XAUUSD","GOLD"]: return cur=="USD"
    return cur in WATCH_CURRENCIES

def news_state(asset=None):
    events=fetch_fmp(); source="FMP" if events else "built_in_risk_windows"
    if not events: events=builtin()
    n=now_utc(); filtered=[]
    for e in events:
        if e.get("timestamp") is None: continue
        if asset and not relevant(asset,e.get("currency","")): continue
        e=dict(e); e["seconds_to_event"]=int(e["timestamp"]-n.timestamp()); e["countdown"]=text(e["seconds_to_event"])
        filtered.append(e)
    filtered.sort(key=lambda x: abs(x["seconds_to_event"]))
    upcoming=[x for x in filtered if x["seconds_to_event"]>=-settings.NEWS_POST_WINDOW_MINUTES*60]
    nxt=upcoming[0] if upcoming else None
    risk="LOW"; mode="NORMAL"; reason="No important near-term news risk."
    if nxt:
        sec=nxt["seconds_to_event"]
        if nxt["impact"]=="HIGH" and -settings.NEWS_POST_WINDOW_MINUTES*60 <= sec <= settings.NEWS_PRE_WINDOW_MINUTES*60:
            risk="HIGH"; mode="NEWS_WAIT" if sec>=0 else "POST_NEWS_IMPULSE"; reason=f"{nxt['impact']} {nxt['currency']} event {nxt['countdown']}: {nxt['title']}"
        elif nxt["impact"] in ["HIGH","MEDIUM"] and sec<=3600:
            risk="MEDIUM"; mode="NEWS_SOON"; reason=f"{nxt['impact']} {nxt['currency']} event {nxt['countdown']}: {nxt['title']}"
    return {"source":source,"risk":risk,"mode":mode,"reason":reason,"next_event":nxt,"events":upcoming[:8],"pre_window_minutes":settings.NEWS_PRE_WINDOW_MINUTES,"post_window_minutes":settings.NEWS_POST_WINDOW_MINUTES}
