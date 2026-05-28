import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
    DASHBOARD_REFRESH_SECONDS = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "15"))
    MARKET_CACHE_SECONDS = int(os.getenv("MARKET_CACHE_SECONDS", "180"))
    NEWS_CACHE_SECONDS = int(os.getenv("NEWS_CACHE_SECONDS", "600"))
    MIN_SIGNAL_SCORE = float(os.getenv("MIN_SIGNAL_SCORE", "58"))
    STRONG_SIGNAL_SCORE = float(os.getenv("STRONG_SIGNAL_SCORE", "78"))
    ACTIVE_ASSETS = [x.strip().upper() for x in os.getenv("ACTIVE_ASSETS", "EURUSD,GBPUSD,XAUUSD").split(",") if x.strip()]

settings = Settings()
