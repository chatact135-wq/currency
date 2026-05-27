from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SmartSignal
from app.services.smart_zone_engine import generate_smart_signal
from app.services.market_data import get_supported_assets

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/assets")
def assets():
    return get_supported_assets()

@router.get("/smart-signal/{asset}")
def smart_signal(asset: str, db: Session = Depends(get_db)):
    result = generate_smart_signal(asset)
    row = SmartSignal(asset=result["asset"], current_price=result["current_price"], action=result["action"], confidence=result["confidence"], risk_level=result["risk_level"], trend=result["trend"], buy_zone_low=result["buy_zone"]["low"], buy_zone_high=result["buy_zone"]["high"], sell_zone_low=result["sell_zone"]["low"], sell_zone_high=result["sell_zone"]["high"], do_not_buy_above=result["do_not_buy_above"], do_not_sell_below=result["do_not_sell_below"], stop_loss=result["stop_loss"], take_profit_1=result["take_profit_1"], take_profit_2=result["take_profit_2"], expected_move_time=result["expected_move_time"], warning=result["warning"], reason=" | ".join(result["reasons"]), data_source=result["data_source"])
    db.add(row)
    db.commit()
    return result

@router.get("/smart-signals")
def smart_signals():
    return {"signals": [generate_smart_signal(asset) for asset in get_supported_assets().keys()]}

@router.get("/history")
def history(db: Session = Depends(get_db)):
    rows = db.query(SmartSignal).order_by(SmartSignal.id.desc()).limit(50).all()
    return [{"id": r.id, "asset": r.asset, "current_price": r.current_price, "action": r.action, "confidence": r.confidence, "risk_level": r.risk_level, "trend": r.trend, "buy_zone": [r.buy_zone_low, r.buy_zone_high], "sell_zone": [r.sell_zone_low, r.sell_zone_high], "warning": r.warning, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]

@router.get("/signals/{asset}")
def old_signal_alias(asset: str):
    return generate_smart_signal(asset)

@router.get("/signals")
def old_signals_alias():
    return {"signals": [generate_smart_signal(asset) for asset in get_supported_assets().keys()]}
