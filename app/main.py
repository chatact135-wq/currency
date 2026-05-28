from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.database import engine
from app.models import Base
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router
Base.metadata.create_all(bind=engine)
app=FastAPI(title="MarketMind AI V11 Tick Memory Pro", version="11.0.0")
app.include_router(api_router); app.include_router(pages_router)
@app.get("/")
def root(): return {"message":"MarketMind AI V11 Tick Memory Pro running","dashboard":"/dashboard","api":"/api/v11/signals"}
@app.get("/health")
def health(): return {"status":"ok","version":"11.0.0"}
@app.get("/go")
def go(): return RedirectResponse("/dashboard")
