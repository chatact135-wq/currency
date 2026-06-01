from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json
from app.database import get_db
from app.models import SignalLog, MarketCandle, BacktestTrade, AdaptiveWeight
from app.config import settings
from app.services.market import active_assets, ASSETS, download_history, backfill_months
from app.services.engine import signal
from app.services.backtest import run_backtest
from app.services.adaptive import recalc_weights
router=APIRouter(prefix="/api/v19",tags=["v14"])
@router.get("/health")
def health(db:Session=Depends(get_db)):
    return {"status":"ok","version":"19.0.0","provider":"TwelveData + Signal Lock Pro","twelvedata_key":bool(settings.TWELVEDATA_API_KEY),"assets":active_assets(),"candles":{a:db.query(MarketCandle).filter(MarketCandle.asset==a).count() for a in active_assets()},"backtest_trades":{a:db.query(BacktestTrade).filter(BacktestTrade.asset==a).count() for a in active_assets()}}
@router.get("/signals")
def signals(db:Session=Depends(get_db)): return {"signals":[signal(db,a) for a in active_assets()]}
@router.get("/signal/{asset}")
def one(asset:str,db:Session=Depends(get_db)):
    r=signal(db,asset)
    if r.get("status")=="live":
        p=r["plan"]; ad=r["adaptive"]
        db.add(SignalLog(asset=r["asset"],price=r["price"],final_action=r["final_action"],master_bias=r["master_bias"],stage=r["stage"],grade=r["grade"],confidence=r["confidence"],adaptive_probability=ad.get("probability"),expected_edge_r=ad.get("expected_edge_r"),risk_level=r["risk_level"],probability_up=r["probabilities"]["up"],probability_sideways=r["probabilities"]["sideways"],probability_down=r["probabilities"]["down"],entry_display=p.get("exact_entry") or p.get("setup_zone"),stop_loss=p.get("stop_loss"),tp1=p.get("tp1_partial_close"),tp2=p.get("tp2"),full_close=p.get("full_close"),setup_score=r["master_engine"]["net"],trigger_score=r["execution_engine"]["net"],features_json=json.dumps(r["features"]),plan_json=json.dumps(p),alerts_json=json.dumps(r["alerts"])))
        db.commit()
    return r
@router.get("/admin/download-history")
def admin_download_history(db:Session=Depends(get_db)):
    out=[]
    for a in active_assets():
        try: out.append(download_history(db,a))
        except Exception as exc: out.append({"asset":a,"error":str(exc)})
    return {"results":out}

@router.get("/admin/backfill-six-months")
def admin_backfill_six_months(db:Session=Depends(get_db)):
    out=[]
    for a in active_assets():
        try:
            out.append(backfill_months(db,a,settings.BACKFILL_MONTHS))
        except Exception as exc:
            out.append({"asset":a,"error":str(exc)})
    return {"results":out}

@router.get("/admin/run-backtest")
def admin_backtest(db:Session=Depends(get_db)):
    out=[]
    for a in active_assets():
        try: out.append(run_backtest(db,a))
        except Exception as exc: out.append({"asset":a,"error":str(exc)})
    return {"results":out}
@router.get("/admin/recalculate-weights")
def admin_recalc(db:Session=Depends(get_db)): return {"results":{a:recalc_weights(db,a) for a in active_assets()}}
@router.get("/ml/weights")
def ml_weights(db:Session=Depends(get_db)):
    return {"weights":[{"asset":r.asset,"strategy":r.strategy,"samples":r.samples,"win_rate":round(r.win_rate*100,1),"avg_r":round(r.avg_r,2),"learned_weight":round(r.learned_weight,2)} for r in db.query(AdaptiveWeight).all()]}
@router.get("/ml/performance")
def ml_perf(db:Session=Depends(get_db)):
    out={}
    for a in active_assets():
        rows=db.query(BacktestTrade).filter(BacktestTrade.asset==a).all(); wins=sum(1 for x in rows if x.outcome=="WIN"); avg=sum(float(x.r_multiple or 0) for x in rows)/len(rows) if rows else 0
        out[a]={"trades":len(rows),"wins":wins,"win_rate":round(wins/len(rows)*100,1) if rows else 0,"avg_r":round(avg,2)}
    return out

@router.get("/best-action")
def best_action(db:Session=Depends(get_db)):
    sigs=[signal(db,a) for a in active_assets()]
    live=[s for s in sigs if s.get("status")=="live"]
    if not live:
        return {"status":"no_live_signals","signals":sigs}
    ranked=sorted(live,key=lambda s:(s.get("best_action") or {}).get("score",0),reverse=True)
    return {"status":"ok","best":ranked[0],"ranking":[{"asset":s.get("asset"),"action":(s.get("best_action") or {}).get("label"),"score":(s.get("best_action") or {}).get("score"),"instruction":(s.get("best_action") or {}).get("instruction")} for s in ranked]}

@router.get("/assets")
def assets(): return {"active":active_assets(),"supported":ASSETS}
