from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone
from app.database import Base
class Signal(Base):
    __tablename__ = 'signals'
    id = Column(Integer, primary_key=True, index=True)
    asset = Column(String(30), index=True, nullable=False)
    signal = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    risk_level = Column(String(30), nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
class MarketSnapshot(Base):
    __tablename__ = 'market_snapshots'
    id = Column(Integer, primary_key=True, index=True)
    asset = Column(String(30), index=True, nullable=False)
    price = Column(Float, nullable=False)
    rsi = Column(Float, nullable=False)
    ema_fast = Column(Float, nullable=False)
    ema_slow = Column(Float, nullable=False)
    volatility = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
