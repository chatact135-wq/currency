from __future__ import annotations

from pathlib import Path
from typing import Dict
import os
import traceback

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from edgeflow.config import APP_NAME, SYMBOLS, REFRESH_SECONDS
from edgeflow.data_provider import fetch_twelvedata_candles, fallback_demo_data, DataError
from edgeflow.strategy_engine import analyze_symbol
from edgeflow.journal import log_signal, get_journal, mark_entered, close_trade, get_open_trades, manage_trade

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title=APP_NAME)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_LAST_SIGNALS: Dict[str, dict] = {}


async def analyze_all() -> dict:
    results = {}
    for symbol in SYMBOLS:
        try:
            df = await fetch_twelvedata_candles(symbol, "1min", 200)
            source = "TwelveData live"
            error = None
        except Exception as e:
            df = fallback_demo_data(symbol)
            source = "DEMO FALLBACK — NOT FOR TRADING"
            error = str(e)

        signal = analyze_symbol(symbol, df)
        current = signal.get("price") or float(df["close"].iloc[-1])
        manager = manage_trade(symbol, current)

        signal["symbol"] = symbol
        signal["source"] = source
        signal["data_error"] = error
        signal["open_trade_manager"] = manager
        results[symbol] = signal
        _LAST_SIGNALS[symbol] = signal
        log_signal(symbol, signal)
    return results


@app.get("/health")
async def health():
    return {"status": "ok", "app": APP_NAME, "mode": "LIVE TEST", "port_env": os.environ.get("PORT")}


@app.get("/ping")
async def ping():
    return "pong"


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "app_name": APP_NAME,
        "refresh_seconds": REFRESH_SECONDS,
        "symbols": SYMBOLS,
    })


@app.get("/api/signals")
async def api_signals():
    try:
        results = await analyze_all()
        return {"status": "ok", "refresh_seconds": REFRESH_SECONDS, "signals": results}
    except Exception:
        return JSONResponse({"status": "error", "traceback": traceback.format_exc()}, status_code=500)


@app.get("/api/journal")
async def api_journal():
    return {"journal": get_journal()[-200:]}


@app.get("/api/open-trades")
async def api_open_trades():
    return {"open_trades": get_open_trades()}


@app.post("/entered")
async def entered(symbol: str = Form(...), direction: str = Form(...), entry: float = Form(...), stop: float = Form(...), target: float = Form(...)):
    mark_entered(symbol, direction, entry, stop, target)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/close")
async def close(symbol: str = Form(...)):
    close_trade(symbol)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/debug")
async def debug():
    return {
        "app": APP_NAME,
        "symbols": SYMBOLS,
        "has_last_signals": bool(_LAST_SIGNALS),
        "port_env": os.environ.get("PORT"),
        "env_has_twelvedata_key": bool(os.environ.get("TWELVEDATA_API_KEY")),
    }
