
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Add the log_analyzer directory to Python's import path
log_analyzer_path = str(PROJECT_ROOT / "log_analyzer")
if log_analyzer_path not in sys.path:
    sys.path.insert(0, log_analyzer_path)

# Add the frontend directory to Python's import path
frontend_dir = str(PROJECT_ROOT / "frontend")
if frontend_dir not in sys.path:
    sys.path.insert(0, frontend_dir)

from app.main import app

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
