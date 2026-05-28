import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    APP_NAME = "MarketMind AI V4 PRO LIVE"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-this")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
    DASHBOARD_REFRESH_SECONDS = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "15"))
    MARKET_CACHE_SECONDS = int(os.getenv("MARKET_CACHE_SECONDS", "180"))
    NEWS_CACHE_SECONDS = int(os.getenv("NEWS_CACHE_SECONDS", "600"))
    ACTIVE_ASSETS = [x.strip().upper() for x in os.getenv("ACTIVE_ASSETS", "EURUSD,GBPUSD,XAUUSD").split(",") if x.strip()]

settings = Settings()
