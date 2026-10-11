import sys
import os

# The log_analyzer package is inside the project directory
log_analyzer_path = os.path.join(os.getcwd(), "log_analyzer")
if log_analyzer_path not in sys.path:
    sys.path.insert(0, log_analyzer_path)

# The frontend directory is at the project root level
frontend_dir = os.path.join(os.getcwd(), "frontend")
if frontend_dir not in sys.path:
    sys.path.insert(0, frontend_dir)

from app.main import app

import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)