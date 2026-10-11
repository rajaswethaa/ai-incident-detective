"""FastAPI app serving the frontend + API endpoints for the Log Analyzer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.parser import read_jsonl
from app.analyzer import analyze

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "log_generation" / "logs"
EXPECTED_DIR = PROJECT_ROOT / "log_generation" / "expected_reports"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = FastAPI(title="Log Analyzer", version="0.1.0")

# Mount static files (CSS, JS) at /static
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory=str(FRONTEND_DIR))


# ---- API Endpoints ----

@app.get("/api/logs")
async def list_logs() -> List[str]:
    """List available log files in ../log_generation/logs."""
    if LOG_DIR.exists():
        return sorted(f.name for f in LOG_DIR.iterdir() if f.suffix == ".jsonl")
    return []


@app.post("/api/analyze/{name}")
async def analyze_log(name: str, file: UploadFile = File(None)):
    """Analyze one of the existing logs or an uploaded .jsonl file.

    If `file` is provided, analyze the uploaded file instead of the named log.
    """
    entries: list = []
    source_name = name
    bad_lines = 0

    if file is not None:
        # Analyze uploaded file
        content = await file.read()
        text = content.decode("utf-8", errors="replace")
        lines = text.splitlines()
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entry = json.loads(stripped)
                entries.append(entry)
            except json.JSONDecodeError:
                bad_lines += 1
        source_name = getattr(file, "filename", "upload") or "upload"
    else:
        # Read from the existing log file
        filepath = LOG_DIR / name
        if not filepath.exists():
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Log file {name} not found")
        entries, bad_lines = read_jsonl(filepath)

    # Analyze the entries
    report = analyze(entries)

    return {
        "report": report,
        "analyzed_file": source_name,
        "bad_lines": bad_lines,
    }


@app.get("/api/expected/{name}")
async def get_expected(name: str):
    """Return the expected report for comparison."""
    filepath = EXPECTED_DIR / name
    if not filepath.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Expected report {name} not found")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the frontend HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})


# ---- Evaluation helper ----
@app.get("/api/evaluate")
async def evaluate():
    """Run evaluation against expected reports and return results."""
    from .scripts.evaluate import evaluate_all
    results = evaluate_all()
    return {"results": results}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)