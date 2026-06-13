from __future__ import annotations
from datetime import datetime, timezone, timedelta
import json
import pandas as pd
from .signal_db import list_signals, save_review
from .data_provider import fetch_twelvedata_candles, fallback_demo_data

HORIZONS = {"15m": 15, "1h": 60, "4h": 240}


def _parse_time(s):
    if not s:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def _as_float(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _pip_size(symbol: str) -> float:
    """Return the small move unit used by the app.
    Forex majors use 0.00001. JPY pairs and metals are handled more safely too.
    """
    s = (symbol or "").upper()
    if "JPY" in s:
        return 0.001
    if "XAU" in s or "GOLD" in s:
        return 0.01
    if "WTI" in s or "OIL" in s:
        return 0.01
    return 0.00001


def _get_entry(signal):
    # Some PLAN ONLY signals have entry=None but price is available. For review,
    # use the screen price at signal time as the reference point.
    for k in ("entry", "price"):
        v = _as_float(signal.get(k))
        if v is not None:
            return v
    try:
        payload = json.loads(signal.get("payload_json") or "{}")
        for k in ("entry", "price", "current", "close"):
            v = _as_float(payload.get(k))
            if v is not None:
                return v
    except Exception:
        pass
    return None


def _prepare_times(df):
    df = df.copy()
    times = pd.to_datetime(df["time"], errors="coerce", utc=True)
    df["time2"] = times
    return df.dropna(subset=["time2", "open", "high", "low", "close"])


def _future_window(df, created, mins):
    """Get candles after the signal.
    First try the exact UTC review window. If the provider's timezone/history window
    does not cover it, fall back to the latest available candles so the review still
    updates good/bad instead of staying empty forever.
    """
    end_time = created + timedelta(minutes=mins)
    future = df[(df["time2"] > created) & (df["time2"] <= end_time)]
    if not future.empty:
        return future, "exact_window"

    after = df[df["time2"] > created]
    if not after.empty:
        return after.head(max(1, mins)), "after_signal_fallback"

    # If the signal is older than the available candle history, use the latest
    # candles as a final-price fallback. This is less perfect than exact history,
    # but it prevents all rows from staying NO DATA/null.
    return df.tail(max(1, min(len(df), mins))), "latest_price_fallback"


def _classify(signal, future, window_source="exact_window"):
    symbol = signal.get("symbol") or ""
    unit = _pip_size(symbol)
    command = (signal.get("command") or "").upper()
    direction = (signal.get("direction") or "").upper()
    entry = _get_entry(signal)
    stop = _as_float(signal.get("stop"))
    target = _as_float(signal.get("target"))

    if future is None or future.empty:
        return {"outcome": "NO DATA", "notes": "No candles available for review."}
    if entry is None:
        return {"outcome": "NO ENTRY PRICE", "notes": "Signal had no entry/price reference saved."}

    entry = float(entry)
    price_after = float(future["close"].iloc[-1])
    high = float(future["high"].max())
    low = float(future["low"].min())

    if direction == "BUY":
        max_fav = (high - entry) / unit
        max_adv = (entry - low) / unit
        tp_hit = bool(target is not None and high >= target)
        sl_hit = bool(stop is not None and low <= stop)
        final_dir = (price_after - entry) / unit
    elif direction == "SELL":
        max_fav = (entry - low) / unit
        max_adv = (high - entry) / unit
        tp_hit = bool(target is not None and low <= target)
        sl_hit = bool(stop is not None and high >= stop)
        final_dir = (entry - price_after) / unit
    else:
        # Neutral / block signals are judged as good unless a large move happened
        # in either direction after the system blocked trading.
        up_move = (high - entry) / unit
        down_move = (entry - low) / unit
        max_fav = max(up_move, down_move)
        max_adv = 0
        tp_hit = False
        sl_hit = False
        final_dir = 0

    # Guard against tiny negative values from spread/noise.
    max_fav = max(0.0, float(max_fav)) if max_fav is not None else None
    max_adv = max(0.0, float(max_adv)) if max_adv is not None else None

    if "SCALP NOW" in command or "TRADE NOW" in command:
        if tp_hit and not sl_hit:
            outcome = "TP HIT"; notes = "Target was reached."
        elif sl_hit and not tp_hit:
            outcome = "SL HIT"; notes = "Stop was hit."
        elif tp_hit and sl_hit:
            # Without tick order, mark by final direction instead of leaving useless.
            outcome = "GOOD DIRECTION" if final_dir >= 0 else "WRONG DIRECTION"
            notes = "Both TP and SL touched; candle order unknown, judged by final direction."
        elif final_dir >= 10:
            outcome = "GOOD DIRECTION"; notes = "Moved in correct direction but did not hit target."
        elif final_dir <= -10:
            outcome = "WRONG DIRECTION"; notes = "Moved against signal."
        else:
            outcome = "FLAT / NO FOLLOW THROUGH"; notes = "No meaningful movement."
    elif "NO TRADE" in command or "PLAN ONLY" in command or "MISSED" in command:
        if direction == "BUY" and max_fav is not None and max_fav >= 30:
            outcome = "MISSED BUY MOVE"; notes = "No entry, but price moved up strongly."
        elif direction == "SELL" and max_fav is not None and max_fav >= 30:
            outcome = "MISSED SELL MOVE"; notes = "No entry, but price moved down strongly."
        else:
            outcome = "GOOD BLOCK / NO CLEAR MOVE"; notes = "No major missed move detected."
    elif direction in ("BUY", "SELL"):
        if final_dir >= 10:
            outcome = "GOOD DIRECTION"; notes = "Directional setup moved correctly."
        elif final_dir <= -10:
            outcome = "WRONG DIRECTION"; notes = "Directional setup moved against the bias."
        else:
            outcome = "FLAT / NO FOLLOW THROUGH"; notes = "No meaningful movement."
    else:
        outcome = "GOOD BLOCK / NO CLEAR MOVE"; notes = "Neutral/block signal reviewed."

    if window_source != "exact_window":
        notes += f" Review used {window_source} because exact future candles were unavailable."

    return {
        "price_after": round(price_after, 5),
        "max_favorable_moves": round(max_fav, 1) if max_fav is not None else None,
        "max_adverse_moves": round(max_adv, 1) if max_adv is not None else None,
        "tp_hit": tp_hit,
        "sl_hit": sl_hit,
        "outcome": outcome,
        "notes": notes,
        "window_source": window_source,
    }


async def review_due_signals():
    reviewed = []
    skipped_not_due = 0
    signals = list_signals(limit=1000)
    now = datetime.now(timezone.utc)
    data_by_symbol = {}

    for s in signals:
        sym = s["symbol"]
        if sym not in data_by_symbol:
            try:
                # More candles gives enough history for 4h review and delayed clicks.
                data_by_symbol[sym] = await fetch_twelvedata_candles(sym, "1min", 5000)
            except Exception:
                data_by_symbol[sym] = fallback_demo_data(sym)
            data_by_symbol[sym] = _prepare_times(data_by_symbol[sym])

    for s in signals:
        created = _parse_time(s["created_at"])
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_min = (now - created).total_seconds() / 60
        df = data_by_symbol.get(s["symbol"])
        if df is None or df.empty:
            continue

        for label, mins in HORIZONS.items():
            if age_min < mins:
                skipped_not_due += 1
                continue
            future, window_source = _future_window(df, created, mins)
            review = _classify(s, future, window_source)
            save_review(int(s["id"]), label, review)
            reviewed.append({
                "signal_id": s["id"],
                "symbol": s.get("symbol"),
                "horizon": label,
                "outcome": review.get("outcome"),
                "price_after": review.get("price_after"),
                "fav": review.get("max_favorable_moves"),
                "adv": review.get("max_adverse_moves"),
                "window_source": window_source,
            })

    return {"reviewed_count": len(reviewed), "skipped_not_due": skipped_not_due, "reviewed": reviewed[:200]}
