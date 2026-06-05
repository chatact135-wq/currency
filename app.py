from __future__ import annotations

from pathlib import Path
import shutil
import zipfile
import os

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backtest_engine import run_all

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
RESULTS_DIR = BASE_DIR / "results"
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="EdgeFlow Terminal Pro Backtest Lab V1")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def clean_folder(path: Path):
    path.mkdir(exist_ok=True)
    for item in path.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


@app.get("/health")
async def health():
    return {"status": "ok", "app": "EdgeFlow Terminal Pro Backtest Lab V1", "framework": "FastAPI"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "message": None})


@app.post("/run", response_class=HTMLResponse)
async def run_backtest(request: Request, files: list[UploadFile] = File(...)):
    if not files:
        return templates.TemplateResponse("index.html", {"request": request, "message": "Upload BID and ASK CSV files first."})

    clean_folder(UPLOAD_DIR)
    clean_folder(RESULTS_DIR)

    saved = []
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".csv"):
            continue
        safe_name = Path(f.filename).name
        dest = UPLOAD_DIR / safe_name
        content = await f.read()
        dest.write_bytes(content)
        saved.append(dest)

    bid_files = [p for p in saved if "_BID_" in p.name.upper()]
    ask_files = [p for p in saved if "_ASK_" in p.name.upper()]

    if not bid_files or not ask_files:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "message": "You must upload at least one BID CSV and one ASK CSV."},
        )

    try:
        result = run_all(bid_files, ask_files, RESULTS_DIR)
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "message": f"Backtest error: {e}"},
        )

    summary = result["summary"].copy()
    table_html = summary.to_html(index=False, classes="table", border=0)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "data_rows": result["data_rows"],
            "start": result["start"],
            "end": result["end"],
            "avg_spread": result["avg_spread_moves"],
            "max_spread": result["max_spread_moves"],
            "table_html": table_html,
        },
    )


@app.get("/download")
async def download_zip():
    if not RESULTS_DIR.exists() or not any(RESULTS_DIR.iterdir()):
        return RedirectResponse(url="/", status_code=302)

    zip_path = BASE_DIR / "EdgeFlow_Backtest_Results.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in RESULTS_DIR.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(RESULTS_DIR))

    return FileResponse(zip_path, filename="EdgeFlow_Backtest_Results.zip", media_type="application/zip")


@app.get("/report")
async def report():
    report_path = RESULTS_DIR / "Backtest_Report.html"
    if not report_path.exists():
        return RedirectResponse(url="/", status_code=302)
    return FileResponse(report_path, media_type="text/html")


@app.get("/debug")
async def debug():
    return {
        "base_dir": str(BASE_DIR),
        "uploads_exists": UPLOAD_DIR.exists(),
        "results_exists": RESULTS_DIR.exists(),
        "templates_exists": (BASE_DIR / "templates").exists(),
        "static_exists": (BASE_DIR / "static").exists(),
        "port_env": os.environ.get("PORT"),
    }
