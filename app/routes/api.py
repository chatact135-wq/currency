from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Signal
from app.services.signal_engine import generate_signal
from app.services.market_data import get_supported_assets
router=APIRouter(prefix='/api', tags=['api'])
@router.get('/assets')
def assets(): return get_supported_assets()
@router.get('/signals/{asset}')
def get_signal(asset: str, db: Session = Depends(get_db)):
    result=generate_signal(asset)
    saved=Signal(asset=result['asset'], signal=result['signal'], confidence=result['confidence'], price=result['price'], risk_level=result['risk_level'], reason=' | '.join(result['reasons']))
    db.add(saved); db.commit()
    return result
@router.get('/signals')
def all_signals(): return {'signals':[generate_signal(a) for a in get_supported_assets().keys()]}
@router.get('/history')
def history(db: Session = Depends(get_db)):
    rows=db.query(Signal).order_by(Signal.id.desc()).limit(30).all()
    return [{'id':r.id,'asset':r.asset,'signal':r.signal,'confidence':r.confidence,'price':r.price,'risk_level':r.risk_level,'created_at':r.created_at.isoformat() if r.created_at else None} for r in rows]
