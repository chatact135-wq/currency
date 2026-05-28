from sqlalchemy import Column,Integer,String,Float,DateTime,Text
from datetime import datetime,timezone
from app.database import Base
class SniperSignalHistory(Base):
    __tablename__='sniper_signal_history'
    id=Column(Integer,primary_key=True,index=True)
    asset=Column(String(30),index=True,nullable=False)
    price=Column(Float,nullable=False)
    action=Column(String(100),nullable=False)
    quality=Column(Float,nullable=False)
    entry_low=Column(Float,nullable=False)
    entry_high=Column(Float,nullable=False)
    stop_loss=Column(Float,nullable=False)
    tp1=Column(Float,nullable=False)
    tp2=Column(Float,nullable=False)
    full_close=Column(Float,nullable=False)
    invalidation=Column(Float,nullable=False)
    reason=Column(Text,nullable=False)
    created_at=Column(DateTime,default=lambda: datetime.now(timezone.utc))
