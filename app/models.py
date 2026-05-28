from sqlalchemy import Column,Integer,String,Float,DateTime,Text
from datetime import datetime, timezone
from app.database import Base
class LiveSignalHistory(Base):
    __tablename__='live_signal_history'
    id=Column(Integer,primary_key=True,index=True)
    asset=Column(String(30),index=True,nullable=False)
    current_price=Column(Float,nullable=False)
    action=Column(String(80),nullable=False)
    confidence=Column(Float,nullable=False)
    risk_level=Column(String(30),nullable=False)
    market_session=Column(String(80),nullable=False)
    news_bias=Column(String(40),nullable=False)
    warning=Column(Text,nullable=False)
    reason=Column(Text,nullable=False)
    created_at=Column(DateTime,default=lambda: datetime.now(timezone.utc))
