from sqlalchemy import Column,Integer,String,Float,DateTime,Text,UniqueConstraint
from datetime import datetime, timezone
from app.database import Base
class MarketCandle(Base):
    __tablename__="v13_market_candles"
    id=Column(Integer,primary_key=True,index=True)
    asset=Column(String(30),index=True,nullable=False)
    timeframe=Column(String(20),index=True,default="5min")
    candle_time=Column(String(60),index=True,nullable=False)
    open=Column(Float,nullable=False); high=Column(Float,nullable=False); low=Column(Float,nullable=False); close=Column(Float,nullable=False)
    provider=Column(String(40),default="twelvedata")
    created_at=Column(DateTime,default=lambda:datetime.now(timezone.utc))
    __table_args__=(UniqueConstraint("asset","timeframe","candle_time",name="uq_v13_candle"),)
class BacktestTrade(Base):
    __tablename__="v13_backtest_trades"
    id=Column(Integer,primary_key=True,index=True)
    asset=Column(String(30),index=True); candle_time=Column(String(60),index=True); direction=Column(String(10))
    entry_price=Column(Float); exit_price=Column(Float); outcome=Column(String(30)); r_multiple=Column(Float)
    max_favorable=Column(Float); max_adverse=Column(Float); features_json=Column(Text); active_strategies=Column(Text)
    created_at=Column(DateTime,default=lambda:datetime.now(timezone.utc))
    __table_args__=(UniqueConstraint("asset","candle_time","direction",name="uq_v13_bt"),)
class AdaptiveWeight(Base):
    __tablename__="v13_adaptive_weights"
    id=Column(Integer,primary_key=True,index=True)
    asset=Column(String(30),index=True); strategy=Column(String(80),index=True); direction=Column(String(10),default="ANY")
    samples=Column(Integer,default=0); wins=Column(Integer,default=0); losses=Column(Integer,default=0)
    win_rate=Column(Float,default=0.5); avg_r=Column(Float,default=0.0); learned_weight=Column(Float,default=10.0)
    updated_at=Column(DateTime,default=lambda:datetime.now(timezone.utc))
    __table_args__=(UniqueConstraint("asset","strategy","direction",name="uq_v13_weight"),)
class SignalLog(Base):
    __tablename__="v13_signal_logs"
    id=Column(Integer,primary_key=True,index=True)
    asset=Column(String(30),index=True); price=Column(Float); final_action=Column(String(100)); master_bias=Column(String(20))
    stage=Column(String(80)); grade=Column(String(10)); confidence=Column(Float); adaptive_probability=Column(Float); expected_edge_r=Column(Float)
    risk_level=Column(String(40)); probability_up=Column(Float); probability_sideways=Column(Float); probability_down=Column(Float)
    entry_display=Column(String(120)); stop_loss=Column(Float); tp1=Column(Float); tp2=Column(Float); full_close=Column(Float)
    setup_score=Column(Float); trigger_score=Column(Float); features_json=Column(Text); plan_json=Column(Text); alerts_json=Column(Text)
    created_at=Column(DateTime,default=lambda:datetime.now(timezone.utc),index=True)
