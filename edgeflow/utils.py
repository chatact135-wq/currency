from __future__ import annotations
from .config import MOVE_SIZE

def moves(a: float, b: float) -> float:
    return abs(float(a) - float(b)) / MOVE_SIZE

def signed_moves(a: float, b: float) -> float:
    return (float(b) - float(a)) / MOVE_SIZE

def add_moves(price: float, mv: float, direction: str) -> float:
    return round(price + mv * MOVE_SIZE, 5) if direction == "BUY" else round(price - mv * MOVE_SIZE, 5)

def back_moves(price: float, mv: float, direction: str) -> float:
    return round(price - mv * MOVE_SIZE, 5) if direction == "BUY" else round(price + mv * MOVE_SIZE, 5)

def rr(entry: float | None, stop: float | None, target: float | None, direction: str) -> tuple[float | None, float | None, float | None]:
    if entry is None or stop is None or target is None:
        return None, None, None
    risk = moves(entry, stop)
    reward = moves(entry, target)
    if risk <= 0:
        return risk, reward, None
    return risk, reward, reward / risk
