from __future__ import annotations
import pandas as pd
from .strategy_engine_test_common import analyze_symbol_controlled

def analyze_symbol(symbol: str, df: pd.DataFrame, spread_moves: float | None = None) -> dict:
    return analyze_symbol_controlled(symbol, df, allow_momentum=True, system_name="TEST-B Controlled Momentum", spread_moves=spread_moves)
