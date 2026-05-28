from sqlalchemy import Column,Integer,String,Float,DateTime,Text
from datetime import datetime, timezone
from app.database import Base
class SignalLog(Base):
    __tablename__='v9_signal_logs'
    id=Column(Integer,primary_key=True,index=True)
    asset=Column(String(30),index=True); price=Column(Float); stage=Column(String(80)); direction=Column(String(20))
    setup_score=Column(Float); trigger_score=Column(Float); plan_json=Column(Text)
    created_at=Column(DateTime,default=lambda: datetime.now(timezone.utc))
