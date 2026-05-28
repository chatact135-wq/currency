from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json
from app.database import get_db
from app.models import SignalLog
from app.services.engine import signal
from app.services.market import active_assets, ASSETS
router=APIRouter(prefix='/api/v7',tags=['v7'])
@router.get('/signals')
def signals(): return {'signals':[signal(a) for a in active_assets()]}
@router.get('/signal/{asset}')
def one(asset:str, db:Session=Depends(get_db)):
    r=signal(asset)
    if r.get('status')=='live':
        db.add(SignalLog(asset=r['asset'],price=r['price'],action=r['action'],bias=r['bias'],score=r['score'],strategy_alerts=json.dumps(r['strategy_alerts']),plan=json.dumps(r['plan']))); db.commit()
    return r
@router.get('/health')
def health(): return {'status':'ok','version':'7.0.0','active_assets':active_assets(),'supported':list(ASSETS.keys())}
