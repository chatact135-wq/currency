import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
    DASHBOARD_REFRESH_SECONDS = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "15"))
    TICK_CACHE_SECONDS = int(os.getenv("TICK_CACHE_SECONDS", "8"))
    NEWS_CACHE_SECONDS = int(os.getenv("NEWS_CACHE_SECONDS", "600"))
    ACTIVE_SCORE = float(os.getenv("ACTIVE_SCORE", "48"))
    SETUP_SCORE = float(os.getenv("SETUP_SCORE", "22"))
    WATCH_SCORE = float(os.getenv("WATCH_SCORE", "20"))
    MIN_ENTRY_PIPS = float(os.getenv("MIN_ENTRY_PIPS", "3"))
    MAX_ENTRY_PIPS = float(os.getenv("MAX_ENTRY_PIPS", "8"))
    ACTIVE_ASSETS = [x.strip().upper() for x in os.getenv("ACTIVE_ASSETS", "EURUSD,GBPUSD,XAUUSD").split(",") if x.strip()]
settings = Settings()
