from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import os
import traceback
import sqlite3
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

# Persistent Signal Journal
DB_PATH = BASE_DIR / "signals_journal.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            signal_type TEXT,
            price REAL,
            confidence INTEGER,
            reasons TEXT,
            expected_time TEXT,
            entry REAL,
            stop_loss REAL,
            take_profit REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

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

        # Save to persistent journal
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                INSERT INTO signals 
                (timestamp, symbol, signal_type, price, confidence, reasons, expected_time, entry, stop_loss, take_profit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal["signal_time_utc"],
                symbol,
                signal.get("signal", "NO TRADE"),
                current_price,
                signal.get("confidence", 0),
                " | ".join(signal.get("reasons", [])),
                signal.get("expected_move", "N/A"),
                signal.get("entry"),
                signal.get("stop_loss"),
                signal.get("take_profit")
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Journal save error: {e}")

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


@app.get("/review", response_class=HTMLResponse)
async def review_page(request: Request):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Show last 24 hours (from 12am to 12am next day)
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        twenty_four_hours_ago = (now - timedelta(hours=24)).isoformat()
        
        cursor.execute("""
            SELECT * FROM signals 
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """, (twenty_four_hours_ago,))
        history = cursor.fetchall()
        conn.close()
        
        return templates.TemplateResponse("review.html", {
            "request": request,
            "app_name": APP_NAME,
            "history": history
        })
    except Exception as e:
        return HTMLResponse(f"<h1>Error loading journal: {str(e)}</h1>")

@app.get("/api/journal")
async def api_journal():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signals ORDER BY timestamp DESC LIMIT 100")
        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"status": "ok", "history": history}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/debug")
async def debug():
    return {
        "app": APP_NAME,
        "symbols": SYMBOLS,
        "has_api_key": bool(os.getenv("TWELVEDATA_API_KEY")),
        "db_path": str(DB_PATH)
    }
