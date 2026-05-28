from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json
from app.database import get_db
from app.models import SignalLog, MarketCandle
from app.config import settings
from app.services.market import active_assets, ASSETS, download_history
from app.services.engine import signal
from app.services.ml_engine import evaluate_old_signals, training_rows

router=APIRouter(prefix="/api/v12", tags=["v12"])

@router.get("/health")
def health(db: Session = Depends(get_db)):
    candle_counts={a:db.query(MarketCandle).filter(MarketCandle.asset==a).count() for a in active_assets()}
    return {"status":"ok","version":"12.0.0","provider":"TwelveData + Neon History + ML Memory","twelvedata_key":bool(settings.TWELVEDATA_API_KEY),"assets":active_assets(),"candle_counts":candle_counts}

@router.get("/signals")
def signals(db: Session = Depends(get_db)):
    return {"signals":[signal(db,a) for a in active_assets()]}

@router.get("/signal/{asset}")
def one(asset: str, db: Session = Depends(get_db)):
    r=signal(db,asset)
    if r.get("status")=="live":
        plan=r["plan"]
        row=SignalLog(asset=r["asset"],price=r["price"],final_action=r["final_action"],master_bias=r["master_bias"],stage=r["stage"],grade=r["grade"],confidence=r["confidence"],ml_probability=r["ml"].get("probability"),ml_status=r["ml"].get("status"),risk_level=r["risk_level"],probability_up=r["probabilities"]["up"],probability_sideways=r["probabilities"]["sideways"],probability_down=r["probabilities"]["down"],entry_display=plan.get("exact_entry") or plan.get("setup_zone"),stop_loss=plan.get("stop_loss"),tp1=plan.get("tp1_partial_close"),tp2=plan.get("tp2"),full_close=plan.get("full_close"),setup_score=r["master_engine"]["net"],trigger_score=r["execution_engine"]["net"],confirmation_score=r["confirmation_engine"]["modifier"],features_json=json.dumps(r["features"]),plan_json=json.dumps(plan),alerts_json=json.dumps(r["alerts"]))
        db.add(row); db.commit()
    return r

@router.get("/admin/download-history")
def admin_download_history(db: Session = Depends(get_db)):
    results=[]
    for a in active_assets():
        try:
            results.append(download_history(db,a,outputsize=settings.HISTORY_CANDLE_LIMIT))
        except Exception as exc:
            results.append({"asset":a,"error":str(exc)})
    return {"results":results}

@router.get("/admin/evaluate-signals")
def admin_evaluate(db: Session = Depends(get_db)):
    return evaluate_old_signals(db, settings.EVALUATION_MINUTES)

@router.get("/ml/stats")
def ml_stats(db: Session = Depends(get_db)):
    out={}
    for a in active_assets():
        X,y=training_rows(db,a)
        out[a]={"training_samples":len(y),"wins":sum(y),"losses":len(y)-sum(y)}
    return out

@router.get("/assets")
def assets():
    return {"active":active_assets(),"supported":ASSETS}
