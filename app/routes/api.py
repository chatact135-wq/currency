from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json
from app.config import settings
from app.database import get_db
from app.models import SignalLog
from app.services.engine import signal
from app.services.market import active_assets, ASSETS
router=APIRouter(prefix='/api/v10',tags=['v10'])
@router.get('/health')
def health(): return {'status':'ok','version':'10.0.0','provider':'Finnhub','finnhub_key':bool(settings.FINNHUB_API_KEY),'assets':active_assets(),'refresh':settings.DASHBOARD_REFRESH_SECONDS,'cache':settings.MARKET_CACHE_SECONDS}
@router.get('/signals')
def signals(): return {'signals':[signal(a) for a in active_assets()]}
@router.get('/signal/{asset}')
def one(asset:str, db:Session=Depends(get_db)):
    r=signal(asset)
    if r.get('status')=='live':
        p=r['plan']; row=SignalLog(asset=r['asset'],price=r['price'],final_action=r['final_action'],master_bias=r['master_bias'],stage=r['stage'],grade=r['grade'],confidence=r['confidence'],risk_level=r['risk_level'],probability_up=r['probabilities']['up'],probability_sideways=r['probabilities']['sideways'],probability_down=r['probabilities']['down'],entry_display=p.get('exact_entry') or p.get('setup_zone'),stop_loss=p.get('stop_loss'),tp1=p.get('tp1_partial_close'),tp2=p.get('tp2'),full_close=p.get('full_close'),setup_score=r['master_engine']['net'],trigger_score=r['execution_engine']['net'],confirmation_score=r['confirmation_engine']['modifier'],features_json=json.dumps(r['features']),plan_json=json.dumps(p),alerts_json=json.dumps(r['alerts']))
        db.add(row); db.commit()
    return r
@router.get('/assets')
def assets(): return {'active':active_assets(),'supported':ASSETS}
