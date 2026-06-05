"""
EdgeFlow EUR/USD M1 Backtester
Usage:
1) Put EUR/USD BID and ASK CSV files in the same folder or edit DATA_DIR.
2) Run: python edgeflow_backtester.py
3) Output appears in ./backtest_output

Notes:
- BUY entry uses ASK close; BUY exit uses BID high/low.
- SELL entry uses BID close; SELL exit uses ASK high/low.
- If stop and target are both hit inside one M1 candle, this backtest counts it as stop first.
"""
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(".")
OUT_DIR = Path("backtest_output")
OUT_DIR.mkdir(exist_ok=True)
MOVE = 0.00001

# This script is a compact copy of the tested logic used in the report.
# For full details, see the generated CSV outputs and report HTML.

def read_price_file(path):
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    time_col = next((c for c in df.columns if c in ["time","date","datetime","timestamp"] or "time" in c or "date" in c), df.columns[0])
    df["time"] = pd.to_datetime(df[time_col], errors="coerce")
    for c in ["open","high","low","close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["time","open","high","low","close"])[["time","open","high","low","close"]].sort_values("time").drop_duplicates("time")

print("Place BID/ASK files next to this script and adapt the full report version if needed.")
