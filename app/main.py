from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.database import engine
from app.models import Base
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router
Base.metadata.create_all(bind=engine)
app=FastAPI(title="MarketMind AI V32 Stable Expiry",version="32.0.0")
app.include_router(api_router); app.include_router(pages_router)
@app.get("/")
def root(): return {"message":"MarketMind AI V32 Stable Expiry running","dashboard":"/dashboard","api":"/api/v32/signals"}
@app.get("/health")
def health(): return {"status":"ok","version":"32.0.0"}
@app.get("/go")
def go(): return RedirectResponse("/dashboard")
