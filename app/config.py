import os
from dotenv import load_dotenv
load_dotenv()
class Settings:
    DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///./test.db")
    SECRET_KEY=os.getenv("SECRET_KEY","dev-secret")
    TWELVEDATA_API_KEY=os.getenv("TWELVEDATA_API_KEY","")
    ACTIVE_ASSETS=[x.strip().upper() for x in os.getenv("ACTIVE_ASSETS","EURUSD,GBPUSD,XAUUSD").split(",") if x.strip()]
    DASHBOARD_REFRESH_SECONDS=int(os.getenv("DASHBOARD_REFRESH_SECONDS","30"))
    MARKET_CACHE_SECONDS=int(os.getenv("MARKET_CACHE_SECONDS","120"))
    HISTORY_CANDLE_LIMIT=int(os.getenv("HISTORY_CANDLE_LIMIT","500"))
    BACKTEST_LOOKAHEAD_CANDLES=int(os.getenv("BACKTEST_LOOKAHEAD_CANDLES","6"))
    BACKTEST_MIN_MOVE_ATR=float(os.getenv("BACKTEST_MIN_MOVE_ATR","0.55"))
    MIN_ADAPTIVE_TRADES=int(os.getenv("MIN_ADAPTIVE_TRADES","40"))
    MIN_ENTRY_PIPS=float(os.getenv("MIN_ENTRY_PIPS","3"))
    MAX_ENTRY_PIPS=float(os.getenv("MAX_ENTRY_PIPS","8"))
settings=Settings()
