from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from datetime import datetime, timezone
from app.database import Base

class PriceTick(Base):
    __tablename__ = "v11_price_ticks"
    id = Column(Integer, primary_key=True, index=True)
    asset = Column(String(30), index=True, nullable=False)
    price = Column(Float, nullable=False)
    provider = Column(String(40), default="finnhub")
    provider_symbol = Column(String(80), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class SignalLog(Base):
    __tablename__ = "v11_signal_logs"
    id = Column(Integer, primary_key=True, index=True)
    asset = Column(String(30), index=True)
    price = Column(Float)
    final_action = Column(String(100))
    master_bias = Column(String(20))
    stage = Column(String(80))
    grade = Column(String(10))
    confidence = Column(Float)
    risk_level = Column(String(40))
    probability_up = Column(Float)
    probability_sideways = Column(Float)
    probability_down = Column(Float)
    entry_display = Column(String(120))
    stop_loss = Column(Float, nullable=True)
    tp1 = Column(Float, nullable=True)
    tp2 = Column(Float, nullable=True)
    full_close = Column(Float, nullable=True)
    features_json = Column(Text)
    plan_json = Column(Text)
    alerts_json = Column(Text)
    outcome_checked = Column(Boolean, default=False)
    outcome_15m = Column(String(30), nullable=True)
    outcome_30m = Column(String(30), nullable=True)
    outcome_1h = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
