from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone
from app.database import Base

class SmartSignal(Base):
    __tablename__ = "smart_signals"
    id = Column(Integer, primary_key=True, index=True)
    asset = Column(String(30), index=True, nullable=False)
    current_price = Column(Float, nullable=False)
    action = Column(String(80), nullable=False)
    confidence = Column(Float, nullable=False)
    risk_level = Column(String(30), nullable=False)
    trend = Column(String(30), nullable=False)
    buy_zone_low = Column(Float, nullable=False)
    buy_zone_high = Column(Float, nullable=False)
    sell_zone_low = Column(Float, nullable=False)
    sell_zone_high = Column(Float, nullable=False)
    do_not_buy_above = Column(Float, nullable=False)
    do_not_sell_below = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)
    expected_move_time = Column(String(120), nullable=False)
    warning = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    data_source = Column(String(80), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
