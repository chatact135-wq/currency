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

# =========================
# TEST-A and TEST-B COMPARISON SYSTEMS
# /test-a = Conservative trend-aligned system
# /test-b = Controlled momentum system
# Each system has its own dashboard, review page, API endpoints, and SQLite database.
# =========================
from edgeflow.strategy_engine_test_a import analyze_symbol as analyze_symbol_test_a
from edgeflow.strategy_engine_test_b import analyze_symbol as analyze_symbol_test_b
from edgeflow.signal_db_test_a import save_signal as save_signal_test_a, list_signals as list_signals_test_a, list_reviews as list_reviews_test_a, strategy_performance as strategy_performance_test_a, init_db as init_db_test_a
from edgeflow.signal_db_test_b import save_signal as save_signal_test_b, list_signals as list_signals_test_b, list_reviews as list_reviews_test_b, strategy_performance as strategy_performance_test_b, init_db as init_db_test_b
from edgeflow.signal_reviewer_test_a import review_due_signals as review_due_signals_test_a
from edgeflow.signal_reviewer_test_b import review_due_signals as review_due_signals_test_b

init_db_test_a()
init_db_test_b()
_LAST_TEST_A_SIGNALS: Dict[str, dict] = {}
_LAST_TEST_B_SIGNALS: Dict[str, dict] = {}

async def analyze_all_test_variant(analyzer, saver, last_store: Dict[str, dict], system_version: str) -> dict:
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

        signal = analyzer(symbol, df)
        current = signal.get("price") or float(df["close"].iloc[-1])
        manager = manage_trade(symbol, current)
        signal["symbol"] = symbol
        signal["source"] = source
        signal["data_error"] = error
        signal["open_trade_manager"] = manager
        signal["system_version"] = system_version
        results[symbol] = signal
        last_store[symbol] = signal
        saver(symbol, signal)
    return results

# ---------- TEST-A: Conservative ----------
@app.get("/test-a/health")
async def test_a_health():
    return {"status": "ok", "app": APP_NAME, "mode": "TEST-A Conservative", "database": "runtime_data/edgeflow_signals_test_a.db"}

@app.get("/test-a", response_class=HTMLResponse)
@app.get("/test-a/dashboard", response_class=HTMLResponse)
async def test_a_dashboard(request: Request):
    return templates.TemplateResponse("dashboard_test_a.html", {
        "request": request,
        "app_name": APP_NAME + " — TEST-A Conservative",
        "subtitle": "/test-a — Conservative trend-aligned logic. Pullback + Break/Retest only. No momentum upgrade.",
        "refresh_seconds": REFRESH_SECONDS,
        "health_url": "/test-a/health",
        "api_signals_url": "/test-a/api/signals",
        "review_url": "/test-a/review",
        "entered_url": "/test-a/entered",
        "close_url": "/test-a/close",
    })

@app.get("/test-a/api/signals")
async def test_a_api_signals():
    try:
        results = await analyze_all_test_variant(analyze_symbol_test_a, save_signal_test_a, _LAST_TEST_A_SIGNALS, "TEST-A Conservative")
        return {"status": "ok", "refresh_seconds": REFRESH_SECONDS, "signals": results, "system_version": "TEST-A Conservative"}
    except Exception:
        return JSONResponse({"status": "error", "traceback": traceback.format_exc()}, status_code=500)

@app.get("/test-a/api/signal-db")
async def test_a_api_signal_db(limit: int = 200):
    return {"signals": list_signals_test_a(limit=limit)}

@app.post("/test-a/api/review-signals")
async def test_a_api_review_signals():
    return await review_due_signals_test_a()

@app.get("/test-a/api/reviews")
async def test_a_api_reviews(limit: int = 300):
    return {"reviews": list_reviews_test_a(limit=limit)}

@app.get("/test-a/api/strategy-performance")
async def test_a_api_strategy_performance():
    return {"performance": strategy_performance_test_a()}

@app.get("/test-a/review", response_class=HTMLResponse)
async def test_a_review_page(request: Request):
    return templates.TemplateResponse("review_test_a.html", {"request": request, "app_name": APP_NAME + " — TEST-A Conservative", "api_base": "/test-a/api", "dashboard_url": "/test-a"})

@app.post("/test-a/entered")
async def test_a_entered(symbol: str = Form(...), direction: str = Form(...), entry: float = Form(...), stop: float = Form(...), target: float = Form(...)):
    mark_entered(symbol, direction, entry, stop, target)
    return RedirectResponse(url="/test-a/dashboard", status_code=303)

@app.post("/test-a/close")
async def test_a_close(symbol: str = Form(...)):
    close_trade(symbol)
    return RedirectResponse(url="/test-a/dashboard", status_code=303)

# ---------- TEST-B: Controlled Momentum ----------
@app.get("/test-b/health")
async def test_b_health():
    return {"status": "ok", "app": APP_NAME, "mode": "TEST-B Controlled Momentum", "database": "runtime_data/edgeflow_signals_test_b.db"}

@app.get("/test-b", response_class=HTMLResponse)
@app.get("/test-b/dashboard", response_class=HTMLResponse)
async def test_b_dashboard(request: Request):
    return templates.TemplateResponse("dashboard_test_b.html", {
        "request": request,
        "app_name": APP_NAME + " — TEST-B Controlled Momentum",
        "subtitle": "/test-b — Trend-aligned Pullback + Break/Retest + controlled Momentum Confirmation upgrade.",
        "refresh_seconds": REFRESH_SECONDS,
        "health_url": "/test-b/health",
        "api_signals_url": "/test-b/api/signals",
        "review_url": "/test-b/review",
        "entered_url": "/test-b/entered",
        "close_url": "/test-b/close",
    })

@app.get("/test-b/api/signals")
async def test_b_api_signals():
    try:
        results = await analyze_all_test_variant(analyze_symbol_test_b, save_signal_test_b, _LAST_TEST_B_SIGNALS, "TEST-B Controlled Momentum")
        return {"status": "ok", "refresh_seconds": REFRESH_SECONDS, "signals": results, "system_version": "TEST-B Controlled Momentum"}
    except Exception:
        return JSONResponse({"status": "error", "traceback": traceback.format_exc()}, status_code=500)

@app.get("/test-b/api/signal-db")
async def test_b_api_signal_db(limit: int = 200):
    return {"signals": list_signals_test_b(limit=limit)}

@app.post("/test-b/api/review-signals")
async def test_b_api_review_signals():
    return await review_due_signals_test_b()

@app.get("/test-b/api/reviews")
async def test_b_api_reviews(limit: int = 300):
    return {"reviews": list_reviews_test_b(limit=limit)}

@app.get("/test-b/api/strategy-performance")
async def test_b_api_strategy_performance():
    return {"performance": strategy_performance_test_b()}

@app.get("/test-b/review", response_class=HTMLResponse)
async def test_b_review_page(request: Request):
    return templates.TemplateResponse("review_test_b.html", {"request": request, "app_name": APP_NAME + " — TEST-B Controlled Momentum", "api_base": "/test-b/api", "dashboard_url": "/test-b"})

@app.post("/test-b/entered")
async def test_b_entered(symbol: str = Form(...), direction: str = Form(...), entry: float = Form(...), stop: float = Form(...), target: float = Form(...)):
    mark_entered(symbol, direction, entry, stop, target)
    return RedirectResponse(url="/test-b/dashboard", status_code=303)

@app.post("/test-b/close")
async def test_b_close(symbol: str = Form(...)):
    close_trade(symbol)
    return RedirectResponse(url="/test-b/dashboard", status_code=303)
