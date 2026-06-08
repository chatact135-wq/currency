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
from edgeflow.signal_db import save_signal, list_signals, list_reviews, strategy_performance, init_db
from edgeflow.signal_reviewer import review_due_signals

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title=APP_NAME)
init_db()

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
        save_signal(symbol, signal)
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

# =========================
# TEST V2 SYSTEM (/test)
# Keeps original dashboard/review unchanged while testing the upgraded logic.
# =========================
from edgeflow.strategy_engine_test import analyze_symbol as analyze_symbol_test
from edgeflow.signal_db_test import save_signal as save_signal_test, list_signals as list_signals_test, list_reviews as list_reviews_test, strategy_performance as strategy_performance_test, init_db as init_db_test
from edgeflow.signal_reviewer_test import review_due_signals as review_due_signals_test

init_db_test()
_LAST_TEST_SIGNALS: Dict[str, dict] = {}

async def analyze_all_test() -> dict:
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

        signal = analyze_symbol_test(symbol, df)
        current = signal.get("price") or float(df["close"].iloc[-1])
        manager = manage_trade(symbol, current)

        signal["symbol"] = symbol
        signal["source"] = source
        signal["data_error"] = error
        signal["open_trade_manager"] = manager
        signal["system_version"] = "TEST V2 — Momentum Confirmation + Breakout Filter"
        results[symbol] = signal
        _LAST_TEST_SIGNALS[symbol] = signal
        save_signal_test(symbol, signal)
    return results

@app.get("/test/health")
async def test_health():
    return {"status": "ok", "app": APP_NAME, "mode": "TEST V2", "database": "runtime_data/edgeflow_signals_test.db"}

@app.get("/test", response_class=HTMLResponse)
@app.get("/test/dashboard", response_class=HTMLResponse)
async def test_dashboard(request: Request):
    return templates.TemplateResponse("dashboard_test.html", {
        "request": request,
        "app_name": APP_NAME + " — TEST V2",
        "refresh_seconds": REFRESH_SECONDS,
        "symbols": SYMBOLS,
    })

@app.get("/test/api/signals")
async def test_api_signals():
    try:
        results = await analyze_all_test()
        return {"status": "ok", "refresh_seconds": REFRESH_SECONDS, "signals": results, "system_version": "TEST V2"}
    except Exception:
        return JSONResponse({"status": "error", "traceback": traceback.format_exc()}, status_code=500)

@app.get("/test/api/signal-db")
async def test_api_signal_db(limit: int = 200):
    return {"signals": list_signals_test(limit=limit)}

@app.post("/test/api/review-signals")
async def test_api_review_signals():
    return await review_due_signals_test()

@app.get("/test/api/reviews")
async def test_api_reviews(limit: int = 300):
    return {"reviews": list_reviews_test(limit=limit)}

@app.get("/test/api/strategy-performance")
async def test_api_strategy_performance():
    return {"performance": strategy_performance_test()}

@app.get("/test/review", response_class=HTMLResponse)
async def test_review_page(request: Request):
    return templates.TemplateResponse("review_test.html", {"request": request, "app_name": APP_NAME + " — TEST V2"})

@app.post("/test/entered")
async def test_entered(symbol: str = Form(...), direction: str = Form(...), entry: float = Form(...), stop: float = Form(...), target: float = Form(...)):
    mark_entered(symbol, direction, entry, stop, target)
    return RedirectResponse(url="/test/dashboard", status_code=303)

@app.post("/test/close")
async def test_close(symbol: str = Form(...)):
    close_trade(symbol)
    return RedirectResponse(url="/test/dashboard", status_code=303)
