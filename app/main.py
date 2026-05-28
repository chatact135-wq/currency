from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.database import engine
from app.models import Base
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router
Base.metadata.create_all(bind=engine)
app=FastAPI(title='MarketMind AI V3 LIVE',description='Live market + real news smart trading zone assistant',version='3.0.0')
app.include_router(api_router); app.include_router(pages_router)
@app.get('/')
def root(): return {'message':'MarketMind AI V3 LIVE running','dashboard':'/dashboard','health':'/api/health','live_signals':'/api/live-signals','example':'/api/live-signal/EURUSD'}
@app.get('/health')
def simple_health(): return {'status':'ok','version':'3.0.0'}
@app.get('/go')
def go_dashboard(): return RedirectResponse(url='/dashboard')
