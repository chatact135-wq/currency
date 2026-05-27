import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    APP_NAME = "MarketMind AI V2"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-this")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

settings = Settings()
