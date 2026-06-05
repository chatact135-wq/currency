from __future__ import annotations

from pathlib import Path
from datetime import datetime
import zipfile
import shutil

from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import pandas as pd

from backtest_engine import run_all

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
RESULTS_DIR = BASE_DIR / "results"
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = "edgeflow-backtest-lab"
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB


def clean_folder(path: Path):
    path.mkdir(exist_ok=True)
    for item in path.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run_backtest():
    files = request.files.getlist("files")
    if not files:
        flash("Upload BID and ASK CSV files first.")
        return redirect(url_for("index"))

    clean_folder(UPLOAD_DIR)
    clean_folder(RESULTS_DIR)

    saved = []
    for f in files:
        if not f.filename.lower().endswith(".csv"):
            continue
        safe_name = Path(f.filename).name
        dest = UPLOAD_DIR / safe_name
        f.save(dest)
        saved.append(dest)

    bid_files = [p for p in saved if "_BID_" in p.name.upper()]
    ask_files = [p for p in saved if "_ASK_" in p.name.upper()]

    if not bid_files or not ask_files:
        flash("You must upload at least one BID CSV and one ASK CSV.")
        return redirect(url_for("index"))

    try:
        result = run_all(bid_files, ask_files, RESULTS_DIR)
    except Exception as e:
        flash(f"Backtest error: {e}")
        return redirect(url_for("index"))

    summary = result["summary"].copy()
    table_html = summary.to_html(index=False, classes="table", border=0)

    return render_template(
        "results.html",
        data_rows=result["data_rows"],
        start=result["start"],
        end=result["end"],
        avg_spread=result["avg_spread_moves"],
        max_spread=result["max_spread_moves"],
        table_html=table_html,
    )


@app.route("/download")
def download_zip():
    if not RESULTS_DIR.exists() or not any(RESULTS_DIR.iterdir()):
        flash("Run a backtest first.")
        return redirect(url_for("index"))

    zip_path = BASE_DIR / "EdgeFlow_Backtest_Results.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in RESULTS_DIR.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(RESULTS_DIR))

    return send_file(zip_path, as_attachment=True)


@app.route("/report")
def report():
    report_path = RESULTS_DIR / "Backtest_Report.html"
    if not report_path.exists():
        flash("Run a backtest first.")
        return redirect(url_for("index"))
    return send_file(report_path)


@app.route("/health")
def health():
    return {"status": "ok", "app": "EdgeFlow Terminal Pro Backtest Lab V1"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(__import__("os").environ.get("PORT", 8000)), debug=False)
