from __future__ import annotations

from pathlib import Path
from typing import Dict
import os
import traceback
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from edgeflow.config import APP_NAME, SYMBOLS, REFRESH_SECONDS
from edgeflow.data_provider import fetch_twelvedata_candles, fallback_demo_data, DataError
from edgeflow.strategy_engine import analyze_symbol
from edgeflow.strategy_engine_test import analyze_symbol_test
from edgeflow.journal import log_signal, get_journal, mark_entered, close_trade, get_open_trades, manage_trade
from edgeflow.signal_db import save_signal, list_signals, list_reviews, strategy_performance, init_db
from edgeflow.signal_reviewer import review_due_signals

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title=APP_NAME)
init_db()

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_LAST_SIGNALS: Dict[str, dict] = {}


async def analyze_all(variant: str = "live") -> dict:
    results = {}
    engine = analyze_symbol_test if variant == "test" else analyze_symbol
    variant_label = "TEST ENGINE /test" if variant == "test" else "LIVE ENGINE /"
    for symbol in SYMBOLS:
        try:
            df = await fetch_twelvedata_candles(symbol, "1min", 200)
            source = f"TwelveData live • {variant_label}"
            error = None
        except Exception as e:
            df = fallback_demo_data(symbol)
            source = f"DEMO FALLBACK — NOT FOR TRADING • {variant_label}"
            error = str(e)

        signal = engine(symbol, df)
        current = signal.get("price") or float(df["close"].iloc[-1])
        manager = manage_trade(symbol, current)

        signal["symbol"] = symbol
        signal["source"] = source
        signal["data_error"] = error
        signal["open_trade_manager"] = manager
        signal["engine_variant"] = variant
        results[symbol] = signal
        _LAST_SIGNALS[f"{variant}:{symbol}"] = signal
        signal["signal_time_utc"] = datetime.now(timezone.utc).isoformat()
        log_signal(symbol, signal)
        signal_db_id = save_signal(symbol, signal)
        signal["signal_db_id"] = signal_db_id
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
        "mode_name": "Current Live Version",
        "mode_badge": "LIVE VERSION",
        "api_path": "/api/signals",
        "return_to": "/dashboard",
        "alt_path": "/test",
        "alt_label": "Open Test Version",
    })


@app.get("/test", response_class=HTMLResponse)
async def test_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "app_name": APP_NAME + " / Test",
        "refresh_seconds": REFRESH_SECONDS,
        "symbols": SYMBOLS,
        "mode_name": "Experimental Test Version",
        "mode_badge": "TEST VERSION / COMPARE AGAINST LIVE",
        "api_path": "/api/signals-test",
        "return_to": "/test",
        "alt_path": "/dashboard",
        "alt_label": "Back to Current Live Version",
    })



@app.get("/testb", response_class=HTMLResponse)
async def testb_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "app_name": APP_NAME + " / TestB",
        "refresh_seconds": REFRESH_SECONDS,
        "symbols": SYMBOLS,
        "mode_name": "TestB — Local Time / Delay Tracking",
        "mode_badge": "TESTB VERSION / LOCAL TIME TRACKING",
        "api_path": "/api/signals-test",
        "return_to": "/testb",
        "alt_path": "/dashboard",
        "alt_label": "Back to Current Live Version",
    })


@app.get("/api/signals")
async def api_signals():
    try:
        results = await analyze_all("live")
        return {"status": "ok", "refresh_seconds": REFRESH_SECONDS, "signals": results, "variant": "live"}
    except Exception:
        return JSONResponse({"status": "error", "traceback": traceback.format_exc()}, status_code=500)


@app.get("/api/signals-test")
async def api_signals_test():
    try:
        results = await analyze_all("test")
        return {"status": "ok", "refresh_seconds": REFRESH_SECONDS, "signals": results, "variant": "test"}
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



@app.get("/api/signal-db")
async def api_signal_db(limit: int = 200):
    return {"signals": list_signals(limit=limit)}

@app.post("/api/review-signals")
async def api_review_signals():
    return await review_due_signals()

@app.get("/api/reviews")
async def api_reviews(limit: int = 300):
    return {"reviews": list_reviews(limit=limit)}

@app.get("/api/strategy-performance")
async def api_strategy_performance():
    return {"performance": strategy_performance()}

@app.get("/review", response_class=HTMLResponse)
async def review_page(request: Request):
    return templates.TemplateResponse("review.html", {"request": request, "app_name": APP_NAME})

@app.get("/debug")
async def debug():
    return {
        "app": APP_NAME,
        "symbols": SYMBOLS,
        "has_last_signals": bool(_LAST_SIGNALS),
        "port_env": os.environ.get("PORT"),
        "env_has_twelvedata_key": bool(os.environ.get("TWELVEDATA_API_KEY")),
    }
