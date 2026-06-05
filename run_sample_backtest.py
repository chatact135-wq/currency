from pathlib import Path
from backtest_engine import run_all

base = Path(__file__).resolve().parent
sample = base / "sample_data"
out = base / "sample_results"

bid_files = sorted(sample.glob("*_BID_*.csv"))
ask_files = sorted(sample.glob("*_ASK_*.csv"))

if not bid_files or not ask_files:
    print("No sample BID/ASK files found in sample_data.")
    raise SystemExit(1)

result = run_all(bid_files, ask_files, out)
print("Backtest complete")
print("Rows:", result["data_rows"])
print("Range:", result["start"], "to", result["end"])
print("Report:", result["report_path"])
print(result["summary"].to_string(index=False))
