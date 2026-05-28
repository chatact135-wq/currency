from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json
from app.config import settings
from app.database import get_db
from app.models import SignalLog
from app.services.engine import signal
from app.services.market import active_assets, ASSETS

router=APIRouter(prefix="/api/v6", tags=["v6"])

@router.get("/health")
def health():
    return {"status":"ok","version":"6.0.0","assets":active_assets(),"refresh":settings.DASHBOARD_REFRESH_SECONDS,"cache":settings.MARKET_CACHE_SECONDS}

@router.get("/signals")
def signals():
    return {"signals":[signal(a) for a in active_assets()]}

@router.get("/signal/{asset}")
def one(asset:str, db:Session=Depends(get_db)):
    r=signal(asset)
    if r.get("status")=="live":
        row=SignalLog(asset=r["asset"],price=r["price"],action=r["action"],bias=r["bias"],quality=r["quality"],
            matched=" | ".join(r["matched"]),missing=" | ".join(r["missing"]),plan=json.dumps(r["plan"]))
        db.add(row); db.commit()
    return r

@router.get("/assets")
def assets():
    return {"active":active_assets(),"supported":ASSETS}
