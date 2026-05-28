from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import SniperSignalHistory
from app.services.sniper_engine import signal
from app.services.market_data import active_assets, SUPPORTED_ASSETS
router=APIRouter(prefix='/api/v5',tags=['v5'])
@router.get('/health')
def health(): return {'status':'ok','version':'5.0.0','live_market_key':bool(settings.TWELVEDATA_API_KEY),'news_key':bool(settings.NEWS_API_KEY),'active_assets':active_assets(),'refresh':settings.DASHBOARD_REFRESH_SECONDS,'cache':settings.MARKET_CACHE_SECONDS}
@router.get('/assets')
def assets(): return {'active':active_assets(),'supported':SUPPORTED_ASSETS}
@router.get('/signal/{asset}')
def one(asset:str,db:Session=Depends(get_db)):
    r=signal(asset)
    if r.get('status')=='live':
        p=r['plan']; row=SniperSignalHistory(asset=r['asset'],price=r['price'],action=r['action'],quality=r['quality'],entry_low=p['entry']['low'],entry_high=p['entry']['high'],stop_loss=p['stop_loss'],tp1=p['take_profit_1'],tp2=p['take_profit_2'],full_close=p['full_close'],invalidation=p['invalidation'],reason=' | '.join(r['reasons']))
        db.add(row); db.commit()
    return r
@router.get('/signals')
def all_signals(): return {'signals':[signal(a) for a in active_assets()]}
