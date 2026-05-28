from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import V4SignalHistory
from app.services.v4_engine import signal
from app.services.market_data import active_assets, SUPPORTED_ASSETS

router = APIRouter(prefix="/api/v4", tags=["v4"])

@router.get("/health")
def health():
    return {
        "status": "ok",
        "version": "4.0.0",
        "live_market_key": bool(settings.TWELVEDATA_API_KEY),
        "news_key": bool(settings.NEWS_API_KEY),
        "active_assets": active_assets(),
        "dashboard_refresh_seconds": settings.DASHBOARD_REFRESH_SECONDS,
        "market_cache_seconds": settings.MARKET_CACHE_SECONDS,
    }

@router.get("/assets")
def assets():
    return {"active": active_assets(), "supported": SUPPORTED_ASSETS}

@router.get("/signal/{asset}")
def one(asset: str, db: Session = Depends(get_db)):
    r = signal(asset)
    if r.get("status") == "live":
        row = V4SignalHistory(
            asset=r["asset"], price=r["price"], action=r["action"], trade_type=r["trade_type"],
            confidence=r["confidence"], sb_score=r["sb_model"]["score"], news_bias=r["news"]["bias"],
            session_name=r["session"]["name"], entry_low=r["plan"]["entry"]["low"], entry_high=r["plan"]["entry"]["high"],
            stop_loss=r["plan"]["stop_loss"], take_profit_1=r["plan"]["take_profit_1"], take_profit_2=r["plan"]["take_profit_2"],
            invalidation=r["plan"]["invalidation"], warning=r["warning"], reason=" | ".join(r["reasons"])
        )
        db.add(row)
        db.commit()
    return r

@router.get("/signals")
def all_signals():
    return {"signals": [signal(a) for a in active_assets()]}

@router.get("/history")
def history(db: Session = Depends(get_db)):
    rows = db.query(V4SignalHistory).order_by(V4SignalHistory.id.desc()).limit(50).all()
    return [
        {"asset": r.asset, "price": r.price, "action": r.action, "confidence": r.confidence, "created_at": r.created_at.isoformat()}
        for r in rows
    ]
