from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.signal_engine import generate_signal
from app.services.market_data import get_supported_assets
router=APIRouter(tags=['pages'])
templates=Jinja2Templates(directory='app/templates')
@router.get('/dashboard', response_class=HTMLResponse)
def dashboard(request: Request):
    signals=[generate_signal(a) for a in get_supported_assets().keys()]
    return templates.TemplateResponse('dashboard.html', {'request':request, 'signals':signals})
