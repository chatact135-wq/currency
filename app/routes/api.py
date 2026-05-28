from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json
from app.database import get_db
from app.models import SignalLog, PriceTick
from app.services.engine import signal
from app.services.market import active_assets, ASSETS, collect_all_ticks
from app.config import settings

router=APIRouter(prefix="/api/v11", tags=["v11"])

@router.get("/health")
def health(db: Session = Depends(get_db)):
    counts={}
    for a in active_assets():
        counts[a]=db.query(PriceTick).filter(PriceTick.asset==a).count()
    return {"status":"ok","version":"11.0.0","provider":"Finnhub quote + Neon tick candles","finnhub_key":bool(settings.FINNHUB_API_KEY),"assets":active_assets(),"tick_counts":counts}

@router.get("/collect-ticks")
def collect_ticks(db: Session = Depends(get_db)):
    return {"collected": collect_all_ticks(db)}

@router.get("/signals")
def signals(db: Session = Depends(get_db)):
    collect_all_ticks(db)
    return {"signals":[signal(db,a) for a in active_assets()]}

@router.get("/signal/{asset}")
def one(asset: str, db: Session = Depends(get_db)):
    collect_all_ticks(db)
    r=signal(db,asset)
    if r.get("status")=="live":
        plan=r["plan"]
        row=SignalLog(asset=r["asset"],price=r["price"],final_action=r["final_action"],master_bias=r["master_bias"],stage=r["stage"],grade=r["grade"],confidence=r["confidence"],risk_level=r["risk_level"],probability_up=r["probabilities"]["up"],probability_sideways=r["probabilities"]["sideways"],probability_down=r["probabilities"]["down"],entry_display=plan.get("exact_entry") or plan.get("setup_zone"),stop_loss=plan.get("stop_loss"),tp1=plan.get("tp1_partial_close"),tp2=plan.get("tp2"),full_close=plan.get("full_close"),features_json=json.dumps(r["features"]),plan_json=json.dumps(plan),alerts_json=json.dumps(r["alerts"]))
        db.add(row); db.commit()
    return r

@router.get("/assets")
def assets():
    return {"active":active_assets(),"supported":ASSETS}
