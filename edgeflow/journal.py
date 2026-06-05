from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json

BASE = Path("runtime_data")
BASE.mkdir(exist_ok=True)
JOURNAL = BASE / "journal.json"
OPEN_TRADES = BASE / "open_trades.json"

def _read(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _write(path: Path, data):
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

def log_signal(symbol: str, signal: dict):
    data = _read(JOURNAL, [])
    item = {
        "time": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "signal": signal,
    }
    data.append(item)
    data = data[-1000:]
    _write(JOURNAL, data)

def get_journal():
    return _read(JOURNAL, [])

def mark_entered(symbol: str, direction: str, entry: float, stop: float, target: float):
    trades = _read(OPEN_TRADES, {})
    trades[symbol] = {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "stop": stop,
        "target": target,
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "status": "OPEN",
    }
    _write(OPEN_TRADES, trades)
    return trades[symbol]

def close_trade(symbol: str):
    trades = _read(OPEN_TRADES, {})
    trade = trades.pop(symbol, None)
    _write(OPEN_TRADES, trades)
    return trade

def get_open_trades():
    return _read(OPEN_TRADES, {})

def manage_trade(symbol: str, current_price: float):
    trades = get_open_trades()
    trade = trades.get(symbol)
    if not trade:
        return None
    direction = trade["direction"]
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    target = float(trade["target"])
    if direction == "BUY":
        pnl_moves = (current_price - entry) / 0.00001
        danger = current_price <= stop
        target_hit = current_price >= target
    else:
        pnl_moves = (entry - current_price) / 0.00001
        danger = current_price >= stop
        target_hit = current_price <= target

    if target_hit:
        action = "TAKE PROFIT / PROTECT PROFIT"
    elif danger:
        action = "STOP INVALIDATED — EXIT"
    elif pnl_moves >= 20:
        action = "PROTECT PROFIT — MOVE STOP NEAR ENTRY"
    elif pnl_moves >= 10:
        action = "HOLD BUT WATCH — SMALL PROFIT"
    elif pnl_moves <= -10:
        action = "WARNING — TRADE GOING AGAINST ENTRY"
    else:
        action = "HOLD — NO ACTION"

    return {
        "trade": trade,
        "current_price": round(current_price, 5),
        "pnl_moves": round(pnl_moves, 1),
        "action": action,
    }
