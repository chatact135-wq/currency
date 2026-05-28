import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

    ACTIVE_ASSETS = [x.strip().upper() for x in os.getenv("ACTIVE_ASSETS", "EURUSD,GBPUSD,XAUUSD").split(",") if x.strip()]
    DASHBOARD_REFRESH_SECONDS = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "30"))
    MARKET_CACHE_SECONDS = int(os.getenv("MARKET_CACHE_SECONDS", "120"))
    HISTORY_CANDLE_LIMIT = int(os.getenv("HISTORY_CANDLE_LIMIT", "500"))

    EVALUATION_MINUTES = int(os.getenv("EVALUATION_MINUTES", "30"))
    MIN_ML_SAMPLES = int(os.getenv("MIN_ML_SAMPLES", "30"))

    ACTIVE_SCORE = float(os.getenv("ACTIVE_SCORE", "50"))
    SETUP_SCORE = float(os.getenv("SETUP_SCORE", "22"))
    WATCH_SCORE = float(os.getenv("WATCH_SCORE", "20"))

    MIN_ENTRY_PIPS = float(os.getenv("MIN_ENTRY_PIPS", "3"))
    MAX_ENTRY_PIPS = float(os.getenv("MAX_ENTRY_PIPS", "8"))

settings = Settings()
