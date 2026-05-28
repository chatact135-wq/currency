import os
from dotenv import load_dotenv
load_dotenv()
class Settings:
    APP_NAME='MarketMind AI V3 LIVE'
    SECRET_KEY=os.getenv('SECRET_KEY','dev-secret-change-this')
    DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./test.db')
    TWELVEDATA_API_KEY=os.getenv('TWELVEDATA_API_KEY','')
    NEWS_API_KEY=os.getenv('NEWS_API_KEY','')
    FINNHUB_API_KEY=os.getenv('FINNHUB_API_KEY','')
    MARKET_CACHE_SECONDS=int(os.getenv('MARKET_CACHE_SECONDS','60'))
    NEWS_CACHE_SECONDS=int(os.getenv('NEWS_CACHE_SECONDS','300'))
    DASHBOARD_REFRESH_SECONDS=int(os.getenv('DASHBOARD_REFRESH_SECONDS','10'))
settings=Settings()
