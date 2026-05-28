from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.database import engine
from app.models import Base
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router
Base.metadata.create_all(bind=engine)
app=FastAPI(title='MarketMind AI V5 Sniper Pro',version='5.0.0')
app.include_router(api_router); app.include_router(pages_router)
@app.get('/')
def root(): return {'message':'MarketMind AI V5 Sniper Pro running','dashboard':'/dashboard','api':'/api/v5/signals'}
@app.get('/health')
def h(): return {'status':'ok','version':'5.0.0'}
@app.get('/go')
def go(): return RedirectResponse(url='/dashboard')
