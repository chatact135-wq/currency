from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import sqlite3, json

DB_DIR = Path("runtime_data")
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "edgeflow_signals.db"

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            symbol TEXT NOT NULL,
            command TEXT,
            strategy TEXT,
            direction TEXT,
            market_mode TEXT,
            market_bias TEXT,
            quality TEXT,
            price REAL,
            entry REAL,
            stop REAL,
            target REAL,
            risk_moves REAL,
            reward_moves REAL,
            rr REAL,
            reason TEXT,
            source TEXT,
            data_error TEXT,
            payload_json TEXT,
            unique_key TEXT UNIQUE
        )
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS signal_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER NOT NULL,
            review_horizon TEXT NOT NULL,
            reviewed_at TEXT NOT NULL,
            price_after REAL,
            max_favorable_moves REAL,
            max_adverse_moves REAL,
            tp_hit INTEGER,
            sl_hit INTEGER,
            outcome TEXT,
            notes TEXT,
            payload_json TEXT,
            UNIQUE(signal_id, review_horizon)
        )
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS price_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price REAL,
            source TEXT,
            command TEXT,
            strategy TEXT,
            market_mode TEXT,
            payload_json TEXT
        )
        """)
        con.commit()

def save_price_snapshot(symbol, signal):
    init_db()
    market = signal.get("market_mode") or {}
    with connect() as con:
        con.execute("""
        INSERT INTO price_snapshots (created_at, symbol, price, source, command, strategy, market_mode, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (now_iso(), symbol, signal.get("price"), signal.get("source"), signal.get("command"), signal.get("strategy"), market.get("mode"), json.dumps(signal, default=str, ensure_ascii=False)))
        con.commit()

def list_price_snapshots(symbol=None, start_time=None, end_time=None, limit=2000):
    init_db(); q="SELECT * FROM price_snapshots WHERE 1=1"; args=[]
    if symbol: q += " AND symbol = ?"; args.append(symbol)
    if start_time: q += " AND created_at > ?"; args.append(start_time)
    if end_time: q += " AND created_at <= ?"; args.append(end_time)
    q += " ORDER BY created_at ASC LIMIT ?"; args.append(limit)
    with connect() as con: rows=con.execute(q,args).fetchall()
    return [dict(r) for r in rows]

def save_signal(symbol, signal):
    init_db()
    market = signal.get("market_mode") or {}
    created = now_iso()
    bucket = created[:15]
    unique_key = f"{bucket}|{symbol}|{signal.get('command')}|{signal.get('strategy')}|{signal.get('direction')}|{signal.get('entry')}|{signal.get('stop')}|{signal.get('target')}"
    try:
        with connect() as con:
            cur = con.execute("""
            INSERT INTO signals (
                created_at, symbol, command, strategy, direction, market_mode, market_bias, quality,
                price, entry, stop, target, risk_moves, reward_moves, rr, reason, source, data_error,
                payload_json, unique_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                created, symbol, signal.get("command"), signal.get("strategy"), signal.get("direction"),
                market.get("mode"), market.get("bias"), signal.get("quality"),
                signal.get("price"), signal.get("entry"), signal.get("stop"), signal.get("target"),
                signal.get("risk_moves"), signal.get("reward_moves"), signal.get("rr"),
                signal.get("reason"), signal.get("source"), signal.get("data_error"),
                json.dumps(signal, default=str, ensure_ascii=False), unique_key
            ))
            con.commit()
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None

def list_signals(limit=200):
    init_db()
    with connect() as con:
        rows = con.execute("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

def save_review(signal_id, horizon, review):
    init_db()
    with connect() as con:
        con.execute("""
        INSERT OR REPLACE INTO signal_reviews (
            signal_id, review_horizon, reviewed_at, price_after, max_favorable_moves, max_adverse_moves,
            tp_hit, sl_hit, outcome, notes, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal_id, horizon, now_iso(), review.get("price_after"), review.get("max_favorable_moves"),
            review.get("max_adverse_moves"), int(bool(review.get("tp_hit"))), int(bool(review.get("sl_hit"))),
            review.get("outcome"), review.get("notes"), json.dumps(review, default=str, ensure_ascii=False)
        ))
        con.commit()

def list_reviews(limit=300):
    init_db()
    with connect() as con:
        rows = con.execute("""
        SELECT r.*, s.symbol, s.command, s.strategy, s.direction, s.entry, s.stop, s.target, s.created_at AS signal_time
        FROM signal_reviews r
        JOIN signals s ON s.id = r.signal_id
        ORDER BY r.id DESC
        LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]

def strategy_performance():
    init_db()
    with connect() as con:
        rows = con.execute("""
        SELECT s.strategy, s.command, s.direction, r.review_horizon,
               COUNT(*) AS total,
               SUM(CASE WHEN r.outcome IN ('TP HIT','GOOD DIRECTION','GOOD BLOCK / NO CLEAR MOVE') THEN 1 ELSE 0 END) AS good,
               SUM(CASE WHEN r.outcome IN ('SL HIT','WRONG DIRECTION','MISSED BUY MOVE','MISSED SELL MOVE') THEN 1 ELSE 0 END) AS bad,
               AVG(r.max_favorable_moves) AS avg_favorable,
               AVG(r.max_adverse_moves) AS avg_adverse
        FROM signal_reviews r JOIN signals s ON s.id = r.signal_id
        GROUP BY s.strategy, s.command, s.direction, r.review_horizon
        ORDER BY total DESC
        """).fetchall()
    out=[]
    for r in rows:
        d=dict(r)
        total=d.get("total") or 0
        good=d.get("good") or 0
        d["good_rate_%"]=round(good/total*100,1) if total else 0
        d["avg_favorable"]=round(d["avg_favorable"],1) if d["avg_favorable"] is not None else None
        d["avg_adverse"]=round(d["avg_adverse"],1) if d["avg_adverse"] is not None else None
        out.append(d)
    return out
