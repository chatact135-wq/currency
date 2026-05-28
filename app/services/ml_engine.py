import json
import numpy as np
from sqlalchemy.orm import Session
from app.config import settings
from app.models import SignalLog, MarketCandle
from app.services.market import normalize

FEATURE_KEYS = ["rsi","atr","momentum","pressure","setup_score","trigger_score","confirmation_score","probability_up","probability_down"]

def _features_from_signal(row):
    try:
        f = json.loads(row.features_json or "{}")
    except Exception:
        f = {}
    return [
        float(f.get("rsi", 50)),
        float(f.get("atr", 0)),
        float(f.get("momentum", 0)),
        float(f.get("pressure", 0)),
        float(row.setup_score or 0),
        float(row.trigger_score or 0),
        float(row.confirmation_score or 0),
        float(row.probability_up or 0),
        float(row.probability_down or 0),
    ]

def training_rows(db: Session, asset: str):
    symbol = normalize(asset)
    rows = (db.query(SignalLog)
              .filter(SignalLog.asset == symbol)
              .filter(SignalLog.outcome_checked == True)
              .filter(SignalLog.outcome != None)
              .all())
    X, y = [], []
    for r in rows:
        if r.outcome in ["WIN", "LOSS"]:
            X.append(_features_from_signal(r))
            y.append(1 if r.outcome == "WIN" else 0)
    return X, y

def simple_ml_probability(db: Session, asset: str, live_features):
    # Lightweight ML-style learner: historical nearest-neighbor + global win rate.
    # It works on Neon-stored outcomes and improves as signal history grows.
    X, y = training_rows(db, asset)
    if len(y) < settings.MIN_ML_SAMPLES:
        return {"status": "collecting_training_data", "samples": len(y), "probability": None}

    x = np.array([float(live_features.get(k, 0)) for k in FEATURE_KEYS], dtype=float)
    Xn = np.array(X, dtype=float)
    yn = np.array(y, dtype=float)

    # Normalize safely
    mean = Xn.mean(axis=0)
    std = Xn.std(axis=0)
    std[std == 0] = 1
    Xs = (Xn - mean) / std
    xs = (x - mean) / std

    distances = np.linalg.norm(Xs - xs, axis=1)
    k = min(25, len(distances))
    idx = np.argsort(distances)[:k]
    local_prob = float(yn[idx].mean())
    global_prob = float(yn.mean())
    probability = 0.7 * local_prob + 0.3 * global_prob
    return {"status": "trained_memory", "samples": len(y), "probability": round(probability * 100, 1)}

def evaluate_old_signals(db: Session, minutes_after: int):
    # Uses stored candle history to label old signals as WIN/LOSS/PARTIAL/UNKNOWN.
    pending = (db.query(SignalLog)
                 .filter(SignalLog.outcome_checked == False)
                 .limit(100)
                 .all())
    checked = 0
    for sig in pending:
        # only evaluate signals with concrete TP/SL
        if not sig.tp1 or not sig.stop_loss:
            continue
        later = (db.query(MarketCandle)
                   .filter(MarketCandle.asset == sig.asset)
                   .filter(MarketCandle.created_at > sig.created_at)
                   .order_by(MarketCandle.id.asc())
                   .limit(50)
                   .all())
        if not later:
            continue
        highs = [x.high for x in later]
        lows = [x.low for x in later]
        if "BUY" in (sig.final_action or ""):
            hit_tp = max(highs) >= sig.tp1
            hit_sl = min(lows) <= sig.stop_loss
            sig.max_favorable_move = max(highs) - sig.price
            sig.max_adverse_move = sig.price - min(lows)
        elif "SELL" in (sig.final_action or ""):
            hit_tp = min(lows) <= sig.tp1
            hit_sl = max(highs) >= sig.stop_loss
            sig.max_favorable_move = sig.price - min(lows)
            sig.max_adverse_move = max(highs) - sig.price
        else:
            continue

        if hit_tp and not hit_sl:
            sig.outcome = "WIN"
        elif hit_sl and not hit_tp:
            sig.outcome = "LOSS"
        elif hit_tp and hit_sl:
            sig.outcome = "PARTIAL"
        else:
            sig.outcome = "UNKNOWN"
        sig.outcome_checked = True
        checked += 1
    db.commit()
    return {"checked": checked}
