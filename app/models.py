from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone
from app.database import Base

class SignalLog(Base):
    __tablename__ = "v6_signal_logs"
    id = Column(Integer, primary_key=True, index=True)
    asset = Column(String(30), index=True)
    price = Column(Float)
    action = Column(String(80))
    bias = Column(String(40))
    quality = Column(Float)
    matched = Column(Text)
    missing = Column(Text)
    plan = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
