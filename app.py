from __future__ import annotations
from pathlib import Path
from typing import Dict
import os
import traceback
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import APP_NAME, SYMBOLS, REFRESH_SECONDS
from core.data_provider import fetch_twelvedata_candles, fallback_demo_data
from core.strategy_engine import analyze_symbol

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title=APP_NAME)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_LAST_SIGNALS: Dict[str, dict] = {}

async def analyze_all() -> dict:
    results = {}
    for symbol in SYMBOLS:
        try:
            df = await fetch_twelvedata_candles(symbol, "15min", 200)
            source = "TwelveData Live"
            error = None
        except Exception as e:
            df = fallback_demo_data(symbol)
            source = "DEMO MODE (No API Key)"
            error = str(e)

        signal = analyze_symbol(symbol, df)
        current_price = signal.get("price") or float(df["close"].iloc[-1])

        signal["symbol"] = symbol
        signal["source"] = source
        signal["data_error"] = error
        signal["signal_time_utc"] = datetime.now(timezone.utc).isoformat()
        results[symbol] = signal
        _LAST_SIGNALS[symbol] = signal

    return results


@app.get("/health")
async def health():
    return {"status": "ok", "app": APP_NAME, "symbols": SYMBOLS}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "app_name": APP_NAME,
        "symbols": SYMBOLS,
        "refresh_seconds": REFRESH_SECONDS,
    })


@app.get("/api/signals")
async def api_signals():
    try:
        results = await analyze_all()
        return {"status": "ok", "signals": results, "refresh_seconds": REFRESH_SECONDS}
    except Exception:
        return JSONResponse(
            {"status": "error", "traceback": traceback.format_exc()},
            status_code=500
        )


@app.get("/debug")
async def debug():
    return {
        "app": APP_NAME,
        "symbols": SYMBOLS,
        "has_api_key": bool(os.getenv("TWELVEDATA_API_KEY")),
    }
