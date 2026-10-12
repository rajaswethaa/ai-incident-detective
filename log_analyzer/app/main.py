
"""FastAPI app serving the frontend and API endpoints for the Log Analyzer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
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


# FastAPI application
app = FastAPI(title="AI Incident Detective", version="0.1.0")


# Serve CSS and JavaScript files
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)

# Configure HTML templates
templates = Jinja2Templates(directory=str(FRONTEND_DIR))


# -------------------- API: List available logs --------------------

@app.get("/api/logs")
async def list_logs() -> List[str]:
    """Return the available JSONL log filenames."""
    if not LOG_DIR.exists():
        return []

    return sorted(
        path.name
        for path in LOG_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".jsonl"
    )


# -------------------- API: Analyze a log --------------------

@app.post("/api/analyze/{name}")
async def analyze_log(
    name: str,
    file: UploadFile | None = File(default=None),
):
    """
    Analyze an uploaded file or an existing JSONL log.

    Supported uploaded formats:
    - .json: one JSON object or a list of objects
    - .jsonl: one JSON object per line
    - .log: one JSON object per line
    """
    entries: list[dict] = []
    source_name = name
    bad_lines = 0

    if file is not None:
        # Read the uploaded file
        content = await file.read()
        text = content.decode("utf-8-sig", errors="replace")
        source_name = file.filename or "upload"
        extension = Path(source_name).suffix.lower()

        if extension not in {".json", ".jsonl", ".log"}:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Upload .json, .jsonl, or .log.",
            )

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        if extension == ".json":
            # Parse the entire JSON document
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid JSON file: {exc.msg} at line {exc.lineno}.",
                ) from exc

            if isinstance(data, dict):
                entries = [data]

            elif isinstance(data, list):
                entries = [
                    item for item in data
                    if isinstance(item, dict)
                ]
                bad_lines = len(data) - len(entries)

            else:
                raise HTTPException(
                    status_code=400,
                    detail="JSON must contain an object or a list of objects.",
                )

        else:
            # Parse JSONL or JSON-formatted log lines
            for line in text.splitlines():
                stripped = line.strip()

                if not stripped:
                    continue

                try:
                    entry = json.loads(stripped)
                except json.JSONDecodeError:
                    bad_lines += 1
                    continue

                if isinstance(entry, dict):
                    entries.append(entry)
                else:
                    bad_lines += 1

    else:
        # Analyze an existing log file.
        # Prevent paths outside LOG_DIR from being accessed.
        if Path(name).name != name:
            raise HTTPException(
                status_code=400,
                detail="Invalid log filename.",
            )

        filepath = LOG_DIR / name

        if not filepath.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"Log file {name} not found.",
            )

        entries, bad_lines = read_jsonl(filepath)

    if not entries:
        raise HTTPException(
            status_code=400,
            detail="No valid log-event objects were found in the file.",
        )

    # Validate that every entry is a dictionary before analysis
    if not all(isinstance(entry, dict) for entry in entries):
        raise HTTPException(
            status_code=400,
            detail="Log entries must be JSON objects.",
        )

    # Run the existing incident analyzer
    try:
        report = analyze(entries)
    except Exception as exc:
        # Log the full error in Render while returning a safe response
        print(f"Analysis failed for {source_name}: {exc!r}")
        raise HTTPException(
            status_code=500,
            detail="The log was parsed, but incident analysis failed. Check server logs.",
        ) from exc

    return {
        "report": report,
        "analyzed_file": source_name,
        "bad_lines": bad_lines,
    }


# -------------------- API: Get expected report --------------------

@app.get("/api/expected/{name}")
async def get_expected(name: str):
    """Return an expected report for comparison."""
    if Path(name).name != name:
        raise HTTPException(
            status_code=400,
            detail="Invalid report filename.",
        )

    filepath = EXPECTED_DIR / name

    if not filepath.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Expected report {name} not found.",
        )

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------- Frontend --------------------

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main webpage."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )


# -------------------- API: Evaluation --------------------

@app.get("/api/evaluate")
async def evaluate():
    """Run evaluation against the expected reports."""
    from scripts.evaluate import evaluate_all

    results = evaluate_all()
    return {"results": results}


# -------------------- Run application locally --------------------

if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
