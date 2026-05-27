from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.database import engine
from app.models import Base
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router
Base.metadata.create_all(bind=engine)
app=FastAPI(title='MarketMind AI', description='AI-style financial market signal dashboard', version='1.0.0')
app.include_router(api_router)
app.include_router(pages_router)
@app.get('/')
def root(): return {'message':'MarketMind AI running','dashboard':'/dashboard','health':'/health','api_signals':'/api/signals'}
@app.get('/health')
def health(): return {'status':'ok'}
@app.get('/go')
def go_dashboard(): return RedirectResponse(url='/dashboard')
