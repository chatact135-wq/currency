from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone
from app.database import Base

class V4SignalHistory(Base):
    __tablename__ = "v4_signal_history"
    id = Column(Integer, primary_key=True, index=True)
    asset = Column(String(30), index=True, nullable=False)
    price = Column(Float, nullable=False)
    action = Column(String(100), nullable=False)
    trade_type = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    sb_score = Column(Float, nullable=False)
    news_bias = Column(String(40), nullable=False)
    session_name = Column(String(80), nullable=False)
    entry_low = Column(Float, nullable=False)
    entry_high = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)
    invalidation = Column(Float, nullable=False)
    warning = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
