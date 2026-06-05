from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MOVE = 0.00001


@dataclass
class BacktestPreset:
    name: str
    enabled: Tuple[str, ...]
    lookback_break: int = 20
    break_buffer_moves: float = 2
    recent_window: int = 4
    recent_impulse_moves: float = 22
    candle_body_moves: float = 8
    reversal_lookback: int = 10
    reversal_drop_moves: float = 22
    reversal_body_moves: float = 8
    pullback_lookback: int = 12
    pullback_impulse_moves: float = 35
    pullback_min_moves: float = 10
    pullback_max_moves: float = 35
    stop_moves: float = 18
    target_moves: float = 25
    max_hold_bars: int = 20
    cooldown_bars: int = 5
    max_spread_moves: float = 8


DEFAULT_PRESETS: List[BacktestPreset] = [
    BacktestPreset(
        name="A_raw_balanced_all",
        enabled=("breakout", "reversal", "pullback"),
        stop_moves=18,
        target_moves=25,
        max_spread_moves=8,
        cooldown_bars=5,
    ),
    BacktestPreset(
        name="B_stricter_all",
        enabled=("breakout", "reversal", "pullback"),
        break_buffer_moves=3,
        recent_impulse_moves=35,
        candle_body_moves=12,
        reversal_drop_moves=35,
        reversal_body_moves=12,
        pullback_impulse_moves=45,
        pullback_min_moves=12,
        pullback_max_moves=30,
        stop_moves=18,
        target_moves=30,
        max_spread_moves=6,
        cooldown_bars=10,
    ),
    BacktestPreset(
        name="C_breakout_only",
        enabled=("breakout",),
        break_buffer_moves=3,
        recent_impulse_moves=35,
        candle_body_moves=12,
        stop_moves=18,
        target_moves=30,
        max_spread_moves=6,
        cooldown_bars=10,
    ),
    BacktestPreset(
        name="D_reversal_only_strict",
        enabled=("reversal",),
        reversal_drop_moves=40,
        reversal_body_moves=12,
        stop_moves=18,
        target_moves=30,
        max_spread_moves=6,
        cooldown_bars=10,
    ),
    BacktestPreset(
        name="E_pullback_only",
        enabled=("pullback",),
        candle_body_moves=10,
        pullback_impulse_moves=45,
        pullback_min_moves=12,
        pullback_max_moves=30,
        stop_moves=18,
        target_moves=30,
        max_spread_moves=6,
        cooldown_bars=10,
    ),
]


def read_price_file(path: Path) -> pd.DataFrame:
    """Read Dukascopy-style OHLC CSV.

    Handles files where the first column is the timezone name, e.g. Asia/Riyadh.
    """
    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    time_col = None
    for c in df.columns:
        if c in {"time", "date", "datetime", "timestamp"} or "time" in c or "date" in c:
            time_col = c
            break
    if time_col is None:
        time_col = df.columns[0]

    df["time"] = pd.to_datetime(df[time_col], errors="coerce")

    for col in ["open", "high", "low", "close"]:
        if col not in df.columns:
            matches = [x for x in df.columns if col in x]
            if matches:
                df = df.rename(columns={matches[0]: col})
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["time", "open", "high", "low", "close"])
    return df[["time", "open", "high", "low", "close"]].sort_values("time").drop_duplicates("time")


def merge_bid_ask(bid_files: Iterable[Path], ask_files: Iterable[Path]) -> pd.DataFrame:
    bid_frames = [read_price_file(Path(f)) for f in bid_files]
    ask_frames = [read_price_file(Path(f)) for f in ask_files]

    if not bid_frames:
        raise ValueError("No BID files uploaded.")
    if not ask_frames:
        raise ValueError("No ASK files uploaded.")

    bid = pd.concat(bid_frames, ignore_index=True).drop_duplicates("time").sort_values("time")
    ask = pd.concat(ask_frames, ignore_index=True).drop_duplicates("time").sort_values("time")

    data = bid.merge(ask, on="time", suffixes=("_bid", "_ask"), how="inner").sort_values("time").reset_index(drop=True)

    if data.empty:
        raise ValueError("BID/ASK files did not share matching timestamps.")

    for c in ["open", "high", "low", "close"]:
        data[f"{c}_mid"] = (data[f"{c}_bid"] + data[f"{c}_ask"]) / 2

    data["spread_moves"] = (data["close_ask"] - data["close_bid"]) / MOVE
    data["date"] = data["time"].dt.date.astype(str)
    return data


def rolling_max_excl(a: np.ndarray, window: int) -> np.ndarray:
    return pd.Series(a).shift(1).rolling(window).max().to_numpy()


def rolling_min_excl(a: np.ndarray, window: int) -> np.ndarray:
    return pd.Series(a).shift(1).rolling(window).min().to_numpy()


def simulate_trade(arr: Dict[str, np.ndarray], idx: int, direction: str, stop_moves: float, target_moves: float, max_hold: int) -> Dict:
    if direction == "BUY":
        entry = arr["close_ask"][idx]
        stop = entry - stop_moves * MOVE
        target = entry + target_moves * MOVE
    else:
        entry = arr["close_bid"][idx]
        stop = entry + stop_moves * MOVE
        target = entry - target_moves * MOVE

    end = min(idx + max_hold, len(arr["time"]) - 1)
    outcome = "TIME_EXIT"
    exit_idx = end
    exit_price = None
    ambiguous = False

    for j in range(idx + 1, end + 1):
        if direction == "BUY":
            stop_hit = arr["low_bid"][j] <= stop
            target_hit = arr["high_bid"][j] >= target
            if stop_hit and target_hit:
                ambiguous = True
                outcome = "LOSS"
                exit_price = stop
                exit_idx = j
                break
            if stop_hit:
                outcome = "LOSS"
                exit_price = stop
                exit_idx = j
                break
            if target_hit:
                outcome = "WIN"
                exit_price = target
                exit_idx = j
                break
        else:
            stop_hit = arr["high_ask"][j] >= stop
            target_hit = arr["low_ask"][j] <= target
            if stop_hit and target_hit:
                ambiguous = True
                outcome = "LOSS"
                exit_price = stop
                exit_idx = j
                break
            if stop_hit:
                outcome = "LOSS"
                exit_price = stop
                exit_idx = j
                break
            if target_hit:
                outcome = "WIN"
                exit_price = target
                exit_idx = j
                break

    if exit_price is None:
        if direction == "BUY":
            exit_price = arr["close_bid"][end]
            pnl = (exit_price - entry) / MOVE
        else:
            exit_price = arr["close_ask"][end]
            pnl = (entry - exit_price) / MOVE
        outcome = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "FLAT"
    else:
        pnl = (exit_price - entry) / MOVE if direction == "BUY" else (entry - exit_price) / MOVE

    return {
        "entry": round(float(entry), 5),
        "stop": round(float(stop), 5),
        "target": round(float(target), 5),
        "exit_price": round(float(exit_price), 5),
        "exit_time": arr["time"][exit_idx],
        "outcome": outcome,
        "pnl_moves": round(float(pnl), 1),
        "hold_minutes": int(exit_idx - idx),
        "ambiguous_same_candle": ambiguous,
    }


def run_backtest(data: pd.DataFrame, preset: BacktestPreset) -> pd.DataFrame:
    p = asdict(preset)
    enabled = set(p.pop("enabled"))

    arr = {c: data[c].to_numpy() for c in data.columns if c != "time"}
    arr["time"] = data["time"].to_numpy()

    n = len(data)
    open_mid = arr["open_mid"]
    high_mid = arr["high_mid"]
    low_mid = arr["low_mid"]
    close_mid = arr["close_mid"]

    prev_high = rolling_max_excl(high_mid, p["lookback_break"])
    prev_low = rolling_min_excl(low_mid, p["lookback_break"])
    rev_high = pd.Series(high_mid).rolling(p["reversal_lookback"]).max().to_numpy()
    rev_low = pd.Series(low_mid).rolling(p["reversal_lookback"]).min().to_numpy()
    prior_high = rolling_max_excl(high_mid, p["pullback_lookback"])
    prior_low = rolling_min_excl(low_mid, p["pullback_lookback"])

    rows = []
    last_signal = -99999
    start = max(p["lookback_break"], p["reversal_lookback"], p["pullback_lookback"], p["recent_window"]) + 2

    for i in range(start, n - p["max_hold_bars"] - 1):
        if i - last_signal < p["cooldown_bars"]:
            continue
        if arr["spread_moves"][i] > p["max_spread_moves"]:
            continue

        candle_body = abs(close_mid[i] - open_mid[i]) / MOVE
        candle_dir = "BUY" if close_mid[i] > open_mid[i] else "SELL" if close_mid[i] < open_mid[i] else "NEUTRAL"

        recent_move = (close_mid[i] - open_mid[i - p["recent_window"]]) / MOVE
        recent_dir = "BUY" if recent_move > 0 else "SELL"
        recent_abs = abs(recent_move)

        chosen = None

        if "breakout" in enabled:
            if close_mid[i] >= prev_high[i] + p["break_buffer_moves"] * MOVE and recent_dir == "BUY" and recent_abs >= p["recent_impulse_moves"] and candle_body >= p["candle_body_moves"]:
                chosen = ("Fast Impulse Breakout", "BUY", f"Break above {p['lookback_break']}m high + {recent_abs:.1f} moves impulse", prev_high[i])
            elif close_mid[i] <= prev_low[i] - p["break_buffer_moves"] * MOVE and recent_dir == "SELL" and recent_abs >= p["recent_impulse_moves"] and candle_body >= p["candle_body_moves"]:
                chosen = ("Fast Impulse Breakout", "SELL", f"Break below {p['lookback_break']}m low + {recent_abs:.1f} moves impulse", prev_low[i])

        if chosen is None and "reversal" in enabled:
            drop = (rev_high[i] - close_mid[i]) / MOVE
            rise = (close_mid[i] - rev_low[i]) / MOVE
            if drop >= p["reversal_drop_moves"] and candle_dir == "SELL" and candle_body >= p["reversal_body_moves"]:
                chosen = ("Fast Reversal", "SELL", f"Drop {drop:.1f} moves from recent high + red candle", rev_high[i])
            elif rise >= p["reversal_drop_moves"] and candle_dir == "BUY" and candle_body >= p["reversal_body_moves"]:
                chosen = ("Fast Reversal", "BUY", f"Rise {rise:.1f} moves from recent low + green candle", rev_low[i])

        if chosen is None and "pullback" in enabled:
            trend = (close_mid[i - 2] - open_mid[i - p["pullback_lookback"]]) / MOVE
            pull_from_high = (prior_high[i] - low_mid[i]) / MOVE
            pull_from_low = (high_mid[i] - prior_low[i]) / MOVE

            if trend >= p["pullback_impulse_moves"] and p["pullback_min_moves"] <= pull_from_high <= p["pullback_max_moves"] and candle_dir == "BUY" and candle_body >= p["candle_body_moves"]:
                chosen = ("Pullback Continuation", "BUY", f"Prior up {trend:.1f}, pullback {pull_from_high:.1f}, resume candle", prior_high[i])
            elif trend <= -p["pullback_impulse_moves"] and p["pullback_min_moves"] <= pull_from_low <= p["pullback_max_moves"] and candle_dir == "SELL" and candle_body >= p["candle_body_moves"]:
                chosen = ("Pullback Continuation", "SELL", f"Prior down {abs(trend):.1f}, pullback {pull_from_low:.1f}, resume candle", prior_low[i])

        if chosen is None:
            continue

        strat, direction, reason, level = chosen
        sim = simulate_trade(arr, i, direction, p["stop_moves"], p["target_moves"], p["max_hold_bars"])
        rows.append({
            "signal_idx": i,
            "entry_time": arr["time"][i],
            "date": str(pd.Timestamp(arr["time"][i]).date()),
            "preset": preset.name,
            "strategy": strat,
            "direction": direction,
            "reason": reason,
            "level": round(float(level), 5),
            "spread_moves": round(float(arr["spread_moves"][i]), 1),
            "body_moves": round(float(candle_body), 1),
            "recent_moves": round(float(recent_abs), 1),
            **sim
        })
        last_signal = i

    return pd.DataFrame(rows)


def summarize(trades: pd.DataFrame) -> pd.Series:
    if trades is None or trades.empty:
        return pd.Series({
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_%": 0,
            "net_moves": 0,
            "avg_moves": 0,
            "profit_factor": 0,
            "avg_hold_min": 0,
            "max_loss_streak": 0,
            "ambiguous": 0,
        })

    wins = int((trades["pnl_moves"] > 0).sum())
    losses = int((trades["pnl_moves"] < 0).sum())
    gross_profit = trades.loc[trades["pnl_moves"] > 0, "pnl_moves"].sum()
    gross_loss = abs(trades.loc[trades["pnl_moves"] < 0, "pnl_moves"].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else np.inf

    cur = maxls = 0
    for x in trades["pnl_moves"]:
        if x < 0:
            cur += 1
            maxls = max(maxls, cur)
        else:
            cur = 0

    return pd.Series({
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate_%": round(wins / len(trades) * 100, 1),
        "net_moves": round(trades["pnl_moves"].sum(), 1),
        "avg_moves": round(trades["pnl_moves"].mean(), 2),
        "profit_factor": round(pf, 2) if np.isfinite(pf) else 999,
        "avg_hold_min": round(trades["hold_minutes"].mean(), 1),
        "max_loss_streak": maxls,
        "ambiguous": int(trades["ambiguous_same_candle"].sum()),
    })


def save_report(results_dir: Path, data: pd.DataFrame, trades_by_preset: Dict[str, pd.DataFrame], summary: pd.DataFrame) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)

    # Save summary and trades
    summary.to_csv(results_dir / "summary_by_preset.csv", index=False)

    all_trades = []
    for name, t in trades_by_preset.items():
        if not t.empty:
            t.to_csv(results_dir / f"trades_{name}.csv", index=False)
            all_trades.append(t)

    if all_trades:
        all_trades_df = pd.concat(all_trades, ignore_index=True)
        all_trades_df.to_csv(results_dir / "all_trades.csv", index=False)
    else:
        all_trades_df = pd.DataFrame()

    # Charts
    equity_path = results_dir / "equity_curve.png"
    plt.figure(figsize=(10, 5))
    for name, t in trades_by_preset.items():
        if not t.empty:
            eq = t["pnl_moves"].cumsum().reset_index(drop=True)
            plt.plot(eq.index, eq.values, label=name)
    plt.title("Backtest Equity Curve by Preset")
    plt.xlabel("Trade number")
    plt.ylabel("Cumulative moves")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(equity_path, dpi=140)
    plt.close()

    spread_path = results_dir / "spread_distribution.png"
    plt.figure(figsize=(8, 4))
    data["spread_moves"].hist(bins=40)
    plt.title("Spread Distribution")
    plt.xlabel("Spread in moves")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(spread_path, dpi=140)
    plt.close()

    def html_table(dfx: pd.DataFrame, rows: int = 50) -> str:
        return dfx.head(rows).to_html(index=False, classes="table", border=0)

    best = summary.sort_values(["profit_factor", "net_moves"], ascending=[False, False]).head(1)
    best_name = best["preset"].iloc[0] if not best.empty else "None"
    best_trades = trades_by_preset.get(best_name, pd.DataFrame())

    by_strategy = pd.DataFrame()
    by_date = pd.DataFrame()
    if not best_trades.empty:
        by_strategy = best_trades.groupby("strategy", group_keys=False).apply(summarize).reset_index()
        by_date = best_trades.groupby("date", group_keys=False).apply(summarize).reset_index()
        by_strategy.to_csv(results_dir / "best_summary_by_strategy.csv", index=False)
        by_date.to_csv(results_dir / "best_summary_by_date.csv", index=False)

    report = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>EdgeFlow Terminal Pro — Backtest Report</title>
<style>
body{{font-family:Arial, sans-serif; margin:28px; color:#111827; line-height:1.45}}
h1,h2{{color:#0f172a}}
.box{{padding:12px; border-radius:10px; margin:12px 0}}
.warn{{background:#fff7ed; border-left:5px solid #f97316}}
.danger{{background:#fef2f2; border-left:5px solid #ef4444}}
.ok{{background:#ecfdf5; border-left:5px solid #10b981}}
.table{{border-collapse:collapse; width:100%; font-size:13px}}
.table th{{background:#e5e7eb}}
.table td,.table th{{border:1px solid #d1d5db; padding:6px}}
img{{max-width:100%; border:1px solid #e5e7eb; border-radius:8px}}
code{{background:#f3f4f6; padding:2px 4px; border-radius:4px}}
</style>
</head>
<body>
<h1>EdgeFlow Terminal Pro — Backtest Lab V1 Report</h1>

<p><b>Data range:</b> {data["time"].min()} to {data["time"].max()}<br>
<b>Merged candles:</b> {len(data)}<br>
<b>Average spread:</b> {data["spread_moves"].mean():.2f} moves<br>
<b>Max spread:</b> {data["spread_moves"].max():.1f} moves</p>

<div class="warn box">
<b>Purpose:</b> This lab tests strategy rules on real historical BID/ASK data before allowing them in a live terminal.
</div>

<h2>Preset Summary</h2>
{html_table(summary, 20)}

<h2>Best Preset by Profit Factor</h2>
<p><b>{best_name}</b></p>

<h2>Best Preset by Strategy</h2>
{html_table(by_strategy, 20) if not by_strategy.empty else "<p>No trades.</p>"}

<h2>Best Preset by Date</h2>
{html_table(by_date, 20) if not by_date.empty else "<p>No trades.</p>"}

<h2>Charts</h2>
<p><img src="equity_curve.png" alt="Equity curve"></p>
<p><img src="spread_distribution.png" alt="Spread distribution"></p>

<h2>First 50 Trades from Best Preset</h2>
{html_table(best_trades[["entry_time","strategy","direction","entry","stop","target","exit_time","exit_price","outcome","pnl_moves","hold_minutes","reason"]] if not best_trades.empty else pd.DataFrame(), 50)}

<h2>Assumptions</h2>
<ul>
<li>BUY entry uses ASK close; BUY exit uses BID high/low.</li>
<li>SELL entry uses BID close; SELL exit uses ASK high/low.</li>
<li>If stop and target hit inside the same M1 candle, stop is counted first.</li>
<li>M1 data is useful, but tick data is better for fast scalping.</li>
</ul>

<h2>Professional Rule</h2>
<div class="danger box">
A strategy should not be used live until it shows acceptable results across enough days, different sessions, and ideally tick data.
</div>

</body>
</html>
"""
    report_path = results_dir / "Backtest_Report.html"
    report_path.write_text(report, encoding="utf-8")
    return report_path


def run_all(bid_files: Iterable[Path], ask_files: Iterable[Path], output_dir: Path, presets: List[BacktestPreset] | None = None) -> Dict:
    presets = presets or DEFAULT_PRESETS
    data = merge_bid_ask(bid_files, ask_files)
    output_dir.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_dir / "merged_bid_ask_data.csv", index=False)

    trades_by_preset: Dict[str, pd.DataFrame] = {}
    rows = []

    for preset in presets:
        trades = run_backtest(data, preset)
        trades_by_preset[preset.name] = trades
        s = summarize(trades).to_dict()
        s["preset"] = preset.name
        rows.append(s)

    summary = pd.DataFrame(rows).sort_values(["profit_factor", "net_moves"], ascending=[False, False])
    report_path = save_report(output_dir, data, trades_by_preset, summary)

    return {
        "data_rows": len(data),
        "start": str(data["time"].min()),
        "end": str(data["time"].max()),
        "avg_spread_moves": round(float(data["spread_moves"].mean()), 2),
        "max_spread_moves": round(float(data["spread_moves"].max()), 1),
        "summary": summary,
        "report_path": report_path,
        "output_dir": output_dir,
    }
