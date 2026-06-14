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

<<<<<<< HEAD
from config import APP_NAME, SYMBOLS, REFRESH_SECONDS
from core.data_provider import fetch_twelvedata_candles, fallback_demo_data
from core.strategy_engine import analyze_symbol
=======
from edgeflow.config import APP_NAME, SYMBOLS, REFRESH_SECONDS
from edgeflow.data_provider import fetch_twelvedata_candles, fallback_demo_data, DataError
from edgeflow.strategy_engine import analyze_symbol
from edgeflow.strategy_engine_test import analyze_symbol_test
from edgeflow.strategy_engine_testb import analyze_symbol_testb
from edgeflow.journal import log_signal, get_journal, mark_entered, close_trade, get_open_trades, manage_trade
from edgeflow.signal_db import save_signal, list_signals, list_reviews, strategy_performance, init_db
from edgeflow.signal_reviewer import review_due_signals
>>>>>>> ae64b9fd8d4a6d0dd9fe41501a18f8a97a3f7edc

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title=APP_NAME)
init_db()

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_LAST_SIGNALS: Dict[str, dict] = {}

<<<<<<< HEAD
async def analyze_all() -> dict:
=======

async def analyze_all(variant: str = "live") -> dict:
>>>>>>> ae64b9fd8d4a6d0dd9fe41501a18f8a97a3f7edc
    results = {}
    if variant == "testb":
        engine = analyze_symbol_testb
        variant_label = "TESTB EARLY PRESSURE ENGINE /testb"
    elif variant == "test":
        engine = analyze_symbol_test
        variant_label = "TEST ENGINE /test"
    else:
        engine = analyze_symbol
        variant_label = "LIVE ENGINE /"
    for symbol in SYMBOLS:
        try:
<<<<<<< HEAD
            df = await fetch_twelvedata_candles(symbol, "15min", 200)
            source = "TwelveData Live"
            error = None
        except Exception as e:
            df = fallback_demo_data(symbol)
            source = "DEMO MODE (No API Key)"
            error = str(e)

        signal = analyze_symbol(symbol, df)
        current_price = signal.get("price") or float(df["close"].iloc[-1])
=======
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
>>>>>>> ae64b9fd8d4a6d0dd9fe41501a18f8a97a3f7edc

        signal["symbol"] = symbol
        signal["source"] = source
        signal["data_error"] = error
<<<<<<< HEAD
        signal["signal_time_utc"] = datetime.now(timezone.utc).isoformat()
        results[symbol] = signal
        _LAST_SIGNALS[symbol] = signal

=======
        signal["open_trade_manager"] = manager
        signal["engine_variant"] = variant
        results[symbol] = signal
        _LAST_SIGNALS[f"{variant}:{symbol}"] = signal
        signal["signal_time_utc"] = datetime.now(timezone.utc).isoformat()
        log_signal(symbol, signal)
        signal_db_id = save_signal(symbol, signal)
        signal["signal_db_id"] = signal_db_id
>>>>>>> ae64b9fd8d4a6d0dd9fe41501a18f8a97a3f7edc
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
<<<<<<< HEAD
        "refresh_seconds": REFRESH_SECONDS,
=======
        "mode_name": "Current Live Version",
        "mode_badge": "LIVE VERSION",
        "api_path": "/api/signals",
        "return_to": "/dashboard",
        "alt_path": "/test",
        "alt_label": "Open Test Version",
        "review_path": "/review",
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
        "review_path": "/test/review",
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
        "api_path": "/api/signals-testb",
        "return_to": "/testb",
        "alt_path": "/dashboard",
        "alt_label": "Back to Current Live Version",
        "review_path": "/testb/review",
>>>>>>> ae64b9fd8d4a6d0dd9fe41501a18f8a97a3f7edc
    })


@app.get("/api/signals")
async def api_signals():
    try:
<<<<<<< HEAD
        results = await analyze_all()
        return {"status": "ok", "signals": results, "refresh_seconds": REFRESH_SECONDS}
=======
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

@app.get("/api/signals-testb")
async def api_signals_testb():
    try:
        results = await analyze_all("testb")
        return {"status": "ok", "refresh_seconds": REFRESH_SECONDS, "signals": results, "variant": "testb"}
>>>>>>> ae64b9fd8d4a6d0dd9fe41501a18f8a97a3f7edc
    except Exception:
        return JSONResponse(
            {"status": "error", "traceback": traceback.format_exc()},
            status_code=500
        )



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
    return templates.TemplateResponse("review.html", {
        "request": request,
        "app_name": APP_NAME,
        "mode_name": "Live Signal Review",
        "mode_badge": "REVIEW MODE",
        "back_path": "/dashboard",
    })

@app.get("/test/review", response_class=HTMLResponse)
async def test_review_page(request: Request):
    return templates.TemplateResponse("review.html", {
        "request": request,
        "app_name": APP_NAME + " / Test Review",
        "mode_name": "Test Signal Review",
        "mode_badge": "TEST REVIEW MODE",
        "back_path": "/test",
    })

@app.get("/testb/review", response_class=HTMLResponse)
async def testb_review_page(request: Request):
    return templates.TemplateResponse("review.html", {
        "request": request,
        "app_name": APP_NAME + " / TestB Review",
        "mode_name": "TestB Local-Time / Delay Tracking Review",
        "mode_badge": "TESTB REVIEW MODE",
        "back_path": "/testb",
    })

@app.get("/debug")
async def debug():
    return {
        "app": APP_NAME,
        "symbols": SYMBOLS,
        "has_api_key": bool(os.getenv("TWELVEDATA_API_KEY")),
    }
