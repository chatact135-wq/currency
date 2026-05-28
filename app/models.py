from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, UniqueConstraint
from datetime import datetime, timezone
from app.database import Base

class MarketCandle(Base):
    __tablename__ = "v12_market_candles"
    id = Column(Integer, primary_key=True, index=True)
    asset = Column(String(30), index=True, nullable=False)
    timeframe = Column(String(20), index=True, default="5min")
    candle_time = Column(String(60), index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    provider = Column(String(40), default="twelvedata")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("asset", "timeframe", "candle_time", name="uq_v12_asset_timeframe_candle"),)

class SignalLog(Base):
    __tablename__ = "v12_signal_logs"
    id = Column(Integer, primary_key=True, index=True)
    asset = Column(String(30), index=True)
    price = Column(Float)
    final_action = Column(String(100))
    master_bias = Column(String(20))
    stage = Column(String(80))
    grade = Column(String(10))
    confidence = Column(Float)
    ml_probability = Column(Float, nullable=True)
    ml_status = Column(String(80), default="not_enough_data")
    risk_level = Column(String(40))
    probability_up = Column(Float)
    probability_sideways = Column(Float)
    probability_down = Column(Float)

    entry_display = Column(String(120))
    stop_loss = Column(Float, nullable=True)
    tp1 = Column(Float, nullable=True)
    tp2 = Column(Float, nullable=True)
    full_close = Column(Float, nullable=True)

    setup_score = Column(Float)
    trigger_score = Column(Float)
    confirmation_score = Column(Float)

    features_json = Column(Text)
    plan_json = Column(Text)
    alerts_json = Column(Text)

    outcome_checked = Column(Boolean, default=False)
    outcome = Column(String(30), nullable=True)
    outcome_price = Column(Float, nullable=True)
    max_favorable_move = Column(Float, nullable=True)
    max_adverse_move = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
