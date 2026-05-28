from sqlalchemy import Column,Integer,String,Float,DateTime,Text,Boolean
from datetime import datetime, timezone
from app.database import Base
class SignalLog(Base):
    __tablename__='v10_signal_logs'
    id=Column(Integer,primary_key=True,index=True)
    asset=Column(String(30),index=True); price=Column(Float); final_action=Column(String(100))
    master_bias=Column(String(20)); stage=Column(String(80)); grade=Column(String(10)); confidence=Column(Float)
    risk_level=Column(String(40)); probability_up=Column(Float); probability_sideways=Column(Float); probability_down=Column(Float)
    entry_display=Column(String(120)); stop_loss=Column(Float,nullable=True); tp1=Column(Float,nullable=True); tp2=Column(Float,nullable=True); full_close=Column(Float,nullable=True)
    setup_score=Column(Float); trigger_score=Column(Float); confirmation_score=Column(Float)
    features_json=Column(Text); plan_json=Column(Text); alerts_json=Column(Text)
    outcome_checked=Column(Boolean,default=False); outcome_15m=Column(String(30),nullable=True); outcome_30m=Column(String(30),nullable=True); outcome_1h=Column(String(30),nullable=True)
    max_favorable_move=Column(Float,nullable=True); max_adverse_move=Column(Float,nullable=True)
    created_at=Column(DateTime,default=lambda: datetime.now(timezone.utc))
