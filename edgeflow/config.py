from __future__ import annotations
import os

APP_NAME = "EdgeFlow Terminal Pro — Live Test V1"

SYMBOLS = ["EUR/USD", "GBP/USD"]

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "").strip()

REFRESH_SECONDS = int(os.getenv("EDGEFLOW_REFRESH_SECONDS", "30"))

MODE = os.getenv("EDGEFLOW_MODE", "live_test")

# "Moves" = last digit. For EUR/USD and GBP/USD, 1 move = 0.00001, 10 moves = 1 pip.
MOVE_SIZE = 0.00001

# Trading safety defaults
MAX_SPREAD_MOVES = float(os.getenv("EDGEFLOW_MAX_SPREAD_MOVES", "6"))
MIN_SCALP_RR = float(os.getenv("EDGEFLOW_MIN_SCALP_RR", "1.15"))
MIN_TRADE_RR = float(os.getenv("EDGEFLOW_MIN_TRADE_RR", "1.35"))
MAX_SCALP_RISK_MOVES = float(os.getenv("EDGEFLOW_MAX_SCALP_RISK_MOVES", "22"))
MAX_TRADE_RISK_MOVES = float(os.getenv("EDGEFLOW_MAX_TRADE_RISK_MOVES", "35"))
NO_CHASE_MOVES = float(os.getenv("EDGEFLOW_NO_CHASE_MOVES", "35"))

# Live test discipline
MAX_TRADES_PER_DAY = int(os.getenv("EDGEFLOW_MAX_TRADES_PER_DAY", "2"))
MAX_LOSSES_PER_DAY = int(os.getenv("EDGEFLOW_MAX_LOSSES_PER_DAY", "2"))
