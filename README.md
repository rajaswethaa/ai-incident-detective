<<<<<<< HEAD
# Log Analyzer

A simple FastAPI-based Log Analyzer that reads JSONL log files, detects incident types,
and generates reports matching the expected schema from `log_generation/expected_reports/`.

## Project Structure

```
log_analyzer/
├── app/
│   ├── main.py          # FastAPI app, serves API + static frontend
│   ├── parser.py        # robust JSONL reader (skip bad lines, count them)
│   ├── analyzer.py      # core analysis logic
│   └── models.py        # pydantic models matching the expected report schema
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── scripts/
│   └── evaluate.py      # compares generated reports vs expected_reports
├── requirements.txt
└── README.md

`log_generation/` is the data directory (do not modify):
- `logs/*.jsonl` — input logs (one JSON entry per line)
- `expected_reports/*.json` — expected output reports
```

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the server:
   ```bash
   python start_server.py
   ```

3. Open your browser at `http://127.0.0.1:8000`

## Usage

### API Endpoints

- **GET /api/logs** — List available log files in `log_generation/logs`
- **POST /api/analyze/{name}** — Analyze one of the existing logs by filename
- **POST /api/analyze/upload** — Analyze an uploaded `.jsonl` file
- **GET /api/expected/{name}** — Return the expected report for the given log
- **GET /api/evaluate** — Run evaluation against all expected reports
- **GET /** — Serve the frontend UI

### Frontend

1. Visit `http://127.0.0.1:8000`
2. Select a log file from the dropdown, or upload a `.jsonl` file
3. Click **Analyze**
4. View summary cards, charts, root cause, recommended actions, and timeline
5. Enable "Compare with expected" to see generated vs expected reports side-by-side

### Evaluation

Run the evaluation script to compare generated reports against expected reports:

```bash
python scripts/evaluate.py
```

This will analyze each of the 7 log files and print a table with per-field match
percentage and an overall score. The analyzer currently achieves ~97% match across
all 7 incident categories with correct detection of:
- api_rate_limiting
- application_exception
- authentication_failure
- database_connection_failure
- http_500_error
- request_timeout
- resource_exhaustion

## Incident Types Detected

The analyzer detects these 7 incident types using rule-based logic:

| Incident Type | Key Indicators |
|---|---|
| `api_rate_limiting` | "rate limit", "429", "throttl" in messages or status_code 429 |
| `application_exception` | "TypeError", "Unexpected data type" in messages |
| `authentication_failure` | "invalid password", "authentication rejected", "login attempt" |
| `database_connection_failure` | "Database connection timeout", "connection pool", DB_TIMEOUT error codes |
| `http_500_error` | "InternalServerError", status_code 500, traceback with "upstream returned 503" |
| `request_timeout` | "timed out", "timeout", "waited_ms", dependency latency exceeding timeout |
| `resource_exhaustion` | "Disk usage", "memory pressure", "ENOSPC", disk_percent/memory_percent fields |
=======
# ai-incident-detective
>>>>>>> 06d3e9b0c486c55f7197316478bccd4ea5d94b35
