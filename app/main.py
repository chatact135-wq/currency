from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.database import engine
from app.models import Base
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router

Base.metadata.create_all(bind=engine)
app = FastAPI(title="MarketMind AI V2", description="Smart price-zone market signal assistant", version="2.0.0")
app.include_router(api_router)
app.include_router(pages_router)

@app.get("/")
def root():
    return {"message": "MarketMind AI V2 running", "dashboard": "/dashboard", "health": "/health", "smart_signals": "/api/smart-signals", "example": "/api/smart-signal/EURUSD"}

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}

@app.get("/go")
def go_dashboard():
    return RedirectResponse(url="/dashboard")
