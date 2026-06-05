from app.services.trigger_lock import trigger_lock_report
from app.services.move_completion import move_completion_report
from app.services.master_validator import master_decision_report
from app.services.price_position import price_position_report
from app.services.fast_start import fast_start_report
from app.services.early_risk import early_risk_report
from app.services.early_trigger import early_trigger_report
from app.services.strong_move import strong_move_report
from app.services.direction_lock import direction_lock_report
from app.services.usage_meter import begin_refresh, track_refresh, report
from app.services.alert_engine import all_alerts
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json
from app.database import get_db
from app.models import SignalLog, MarketCandle, BacktestTrade, AdaptiveWeight
from app.config import settings
from app.services.market import active_assets, ASSETS, download_history, fetch_twelve_live_price, backfill_months, fetch_twelve_live_price
from app.services.engine import signal
from app.services.signal_memory import memory_report
from app.services.news_engine import news_state
from app.services.backtest import run_backtest
from app.services.adaptive import recalc_weights
router=APIRouter(prefix="/api/v45",tags=["v32"])
@router.get("/health")
def health(db:Session=Depends(get_db)):
    return {"status":"ok","version":"45.0.0","provider":"TwelveData + Trigger Lock Engine","twelvedata_key":bool(settings.TWELVEDATA_API_KEY),"assets":active_assets(),"candles":{a:db.query(MarketCandle).filter(MarketCandle.asset==a).count() for a in active_assets()},"backtest_trades":{a:db.query(BacktestTrade).filter(BacktestTrade.asset==a).count() for a in active_assets()}}
@router.get("/signals")
def signals(db:Session=Depends(get_db)):
    begin_refresh("signals")
    track_refresh("internal_signals_endpoint", 1)
    return {"signals":[signal(db,a) for a in active_assets()]}
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


@router.get("/news")
def news():
    return news_state()


@router.get("/market-map")
def market_map(db:Session=Depends(get_db)):
    begin_refresh("market_map")
    track_refresh("internal_market_map_endpoint", 1)
    items=[signal(db,a) for a in active_assets()]
    return {"maps":[{"asset":x.get("asset"),"display":x.get("display"),"final_action":x.get("final_action"),"market_map":x.get("market_map")} for x in items]}


@router.get("/price-check")
def price_check():
    begin_refresh("price_check")
    track_refresh("internal_price_check_endpoint", 1)
    out=[]
    for a in active_assets():
        try:
            q=fetch_twelve_live_price(a)
            out.append({"asset":a,"live_price":q["price"],"source":q["source"],"cache_age":q["cache_age"]})
        except Exception as exc:
            out.append({"asset":a,"error":str(exc)})
    return {"prices":out}


@router.get("/alerts")
def alerts():
    track_refresh("internal_alerts_endpoint", 1)
    return {"alerts": all_alerts()}


@router.get("/usage")
def usage(refresh_seconds:int=10):
    return report(refresh_seconds)


@router.get("/signal-memory")
def signal_memory():
    return memory_report()


@router.get("/direction-lock")
def direction_lock():
    return direction_lock_report()


@router.get("/strong-move")
def strong_move():
    return strong_move_report()


@router.get("/early-trigger")
def early_trigger():
    return early_trigger_report()


@router.get("/early-risk")
def early_risk():
    return early_risk_report()


@router.get("/fast-start")
def fast_start():
    return fast_start_report()


@router.get("/price-position")
def price_position():
    return price_position_report()


@router.get("/master-decision")
def master_decision():
    return master_decision_report()


@router.get("/move-completion")
def move_completion():
    return move_completion_report()


@router.get("/trigger-lock")
def trigger_lock():
    return trigger_lock_report()
