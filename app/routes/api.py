from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import LiveSignalHistory
from app.services.signal_engine import generate_live_signal
from app.services.market_data import get_supported_assets
from app.config import settings
router=APIRouter(prefix='/api',tags=['api'])
@router.get('/health')
def health(): return {'status':'ok','version':'3.0.0','live_market_connected':bool(settings.TWELVEDATA_API_KEY),'news_connected':bool(settings.NEWS_API_KEY),'dashboard_refresh_seconds':settings.DASHBOARD_REFRESH_SECONDS,'market_cache_seconds':settings.MARKET_CACHE_SECONDS,'news_cache_seconds':settings.NEWS_CACHE_SECONDS}
@router.get('/assets')
def assets(): return get_supported_assets()
@router.get('/live-signal/{asset}')
def live_signal(asset:str, db:Session=Depends(get_db)):
    result=generate_live_signal(asset)
    if result.get('status')=='live':
        row=LiveSignalHistory(asset=result['asset'],current_price=result['current_price'],action=result['action'],confidence=result['confidence'],risk_level=result['risk_level'],market_session=result['market_session']['name'],news_bias=result['news']['bias'],warning=result['warning'],reason=' | '.join(result['reasons']))
        db.add(row); db.commit()
    return result
@router.get('/live-signals')
def live_signals(): return {'signals':[generate_live_signal(asset) for asset in get_supported_assets().keys()]}
@router.get('/smart-signal/{asset}')
def smart_signal_alias(asset:str): return generate_live_signal(asset)
@router.get('/smart-signals')
def smart_signals_alias(): return {'signals':[generate_live_signal(asset) for asset in get_supported_assets().keys()]}
@router.get('/history')
def history(db:Session=Depends(get_db)):
    rows=db.query(LiveSignalHistory).order_by(LiveSignalHistory.id.desc()).limit(50).all()
    return [{'id':r.id,'asset':r.asset,'current_price':r.current_price,'action':r.action,'confidence':r.confidence,'risk_level':r.risk_level,'market_session':r.market_session,'news_bias':r.news_bias,'warning':r.warning,'created_at':r.created_at.isoformat() if r.created_at else None} for r in rows]
