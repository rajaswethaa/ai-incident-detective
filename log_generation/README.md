# AI Incident Detective — Log Generation Module

## 1. Project Overview

**AI Incident Detective** is a Python project that generates realistic application
incident logs and uses them as a test dataset for a backend AI system. The AI
system analyzes JSONL log files, identifies incidents, infers probable root
causes, and produces incident reports that can be compared against ground truth.

This module is **deterministic and reproducible**: log generation uses a fixed
random seed (`random.Random(42)`), so every run produces byte-identical output.

**Requirements:** Python 3.9 or newer (developed and tested with Python 3.15).
Only the Python standard library is used (`json`, `random`, `re`, `datetime`,
`pathlib`) — no third-party dependencies.

## 2. My Responsibility: Log Generation (Task 1)

The responsibility covered by this module is **Task 1: Log Generation**:

- Generate seven types of realistic application incident logs as JSONL files.
- Include realistic timestamps and a mix of `INFO`, `WARNING`, and `ERROR` events.
- Provide enough context (metrics, thresholds, error codes, trace IDs, hosts)
  for an AI system to identify possible root causes.
- Validate the generated logs and maintain ground-truth reports for backend testing.

## 3. Seven Incident Scenarios

Each scenario is stored as one JSONL file in `logs/`. Every incident follows a
realistic narrative arc: normal `INFO` events → `WARNING` early-warning signs →
the `ERROR` failure → follow-up events (failover, retry, throttling, recovery).

| # | Log file | Incident type | Affected service(s) | Severity | Root cause (as evidenced in the logs) | Entries |
|---|----------|---------------|---------------------|----------|----------------------------------------|---------|
| 1 | `database_failure.jsonl` | Database connection failure | order-service | high | Connection pool exhaustion on `orders_db` primary (`db-primary-01`): pool hits 50/50 with 7 waiting requests, then 30 s timeouts (`DB_TIMEOUT_30000`) | 7 |
| 2 | `http_500_error.jsonl` | HTTP 500 error | api-service | high | Payment gateway unreachable (upstream 503) at `order_views.py` line 88, causing `POST /api/orders` to return 500 | 5 |
| 3 | `api_rate_limit.jsonl` | API rate limiting | gateway | medium | `client-A` exceeds its 100 requests/minute quota (reaches 120 rpm), correctly throttled with HTTP 429 | 5 |
| 4 | `application_exception.jsonl` | Application exception | report-service | medium | `TypeError` during report aggregation: `total_amount` contains the string `"N/A"` where a float is expected | 5 |
| 5 | `request_timeout.jsonl` | Request timeout | search-service | medium | Downstream `catalog-service` latency (4200 ms → 5100 ms) consumes the entire 5-second timeout budget | 5 |
| 6 | `authentication_failure.jsonl` | Authentication failure | auth-service | low | Three invalid passwords for `test-user-01` from `198.51.100.23` exhaust the lockout threshold of 3 | 5 |
| 7 | `resource_exhaustion.jsonl` | Resource exhaustion | system-monitor, file-service | high | Disk on `/var/data` climbs 74% → 88% → 96% (412 MB free) until temp-file writes fail with `ENOSPC` | 6 |

All seven incidents take place on the same morning (2026-10-11, UTC),
spread from 06:05 to 11:34, for a total of **38 log entries**.

## 4. Project Folder Structure

```
AI-Incident-Detective/
├── README.md                        # this file
├── generate_logs.py                 # generates the 7 JSONL log files
├── validate_logs.py                 # validates logs/
├── validate_reports.py              # validates expected_reports/
├── logs/                            # generated JSONL incident logs
│   ├── api_rate_limit.jsonl
│   ├── application_exception.jsonl
│   ├── authentication_failure.jsonl
│   ├── database_failure.jsonl
│   ├── http_500_error.jsonl
│   ├── request_timeout.jsonl
│   └── resource_exhaustion.jsonl
└── expected_reports/                # ground-truth reports for backend testing
    ├── api_rate_limit.json
    ├── application_exception.json
    ├── authentication_failure.json
    ├── database_failure.json
    ├── http_500_error.json
    ├── request_timeout.json
    └── resource_exhaustion.json
```

## 5. Description of `generate_logs.py`

Generates the seven JSONL incident log files into `logs/`.

- **`SCENARIOS`** maps each filename to `(start_after_minutes, trace_id, events)`.
  Each event is a tuple `(offset_seconds, level, service, message, details)`.
- **`BASE_TIME`** is fixed at `2026-10-11T06:00:00Z` (UTC). Each scenario starts
  at `BASE_TIME + start_after_minutes`, and each event adds its `offset_seconds`.
- **Timestamps** are ISO 8601 UTC with millisecond precision
  (e.g. `2026-10-11T06:05:09.025Z`). The millisecond component comes from the
  seeded RNG, keeping output reproducible.
- **`HOSTS`** maps each service to a stable host name (e.g. `order-service` →
  `ord-svc-01`), and each scenario carries a unique `trace_id` shared by all of
  its events so an AI system can correlate them.
- **`incident_id`** is derived from the filename stem, keeping logs and reports
  in sync.
- Each entry is written as one JSON object per line (`json.dumps(entry) + "\n"`).

## 6. Description of `validate_logs.py`

Validates everything in `logs/`. It exits with a descriptive error (non-zero
exit code) on the first problem found, and prints one `PASS` line per file on
success. Checks performed:

- The `logs/` directory exists and contains exactly 7 `*.jsonl` files.
- Every line is valid JSON and a JSON object.
- All required fields are present: `timestamp`, `level`, `service`,
  `incident_id`, `message`, `details`.
- `level` is one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- `details` is a JSON object.
- `incident_id` matches the filename stem.
- `timestamp` matches the ISO 8601 pattern and entries are in chronological
  order within each file.
- No file is empty.

## 7. Description of `validate_reports.py`

Validates the ground-truth reports in `expected_reports/` and cross-checks them
against the source logs so the reports cannot drift from the data. Checks
performed:

- The `expected_reports/` directory exists and contains exactly 7 `.json` files
  with the expected incident IDs.
- All 8 required report fields are present: `incident_id`, `incident_type`,
  `severity`, `affected_service`, `probable_root_cause`, `evidence`,
  `troubleshooting_steps`, `expected_resolution`.
- String fields are non-empty; `severity` is one of `low`, `medium`, `high`,
  `critical`.
- `evidence` and `troubleshooting_steps` are non-empty lists, and each evidence
  item is an object containing `timestamp`, `level`, `service`, and `message`.
- **Ground-truth cross-check:** every evidence item's `timestamp`, `level`,
  `message`, and `trace_id` must match a real entry in the corresponding
  `logs/*.jsonl` file.

## 8. Commands to Generate and Validate Logs

Run all commands from the project root (`AI-Incident-Detective/`):

```bash
# Generate the seven JSONL log files into logs/
python generate_logs.py

# Validate the generated logs
python validate_logs.py

# Validate the ground-truth reports against the logs
python validate_reports.py
```

> On Windows the output shows backslash paths (`logs\...`); on Linux/macOS it
> shows forward slashes (`logs/...`).

## 9. JSONL Log Format and Field Descriptions

Each line in a `logs/*.jsonl` file is one JSON object with eight fields:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 UTC with millisecond precision, e.g. `2026-10-11T06:05:09.025Z` |
| `level` | string | Log level: `INFO`, `WARNING`, or `ERROR` in the generated data |
| `service` | string | Service that emitted the entry (e.g. `order-service`, `gateway`) |
| `incident_id` | string | Incident identifier; matches the log filename stem (e.g. `database_failure`) |
| `trace_id` | string | Correlation ID shared by all events of one incident (e.g. `trc-7f3a91c2`) |
| `host` | string | Machine that emitted the entry (e.g. `ord-svc-01`) |
| `message` | string | Human-readable event description |
| `details` | object | Scenario-specific context: metrics, thresholds, error codes, retry counts, offending values |

The `details` object is where the root-cause clues live — for example
`pool_active`/`pool_max` for pool exhaustion, `requests_per_minute`/`limit`
for rate limiting, `waited_ms`/`timeout_seconds` for timeouts, and `errno`
for resource exhaustion.

## 10. How the Backend Developer Can Use the Logs and Expected Reports

1. **Input dataset:** feed the seven `logs/*.jsonl` files to the AI incident
   detection pipeline (LLM) as input.
2. **Ground truth:** compare the pipeline's output against the matching
   `expected_reports/*.json` files. Suggested comparison points:
   - `incident_id` / `incident_type` — did the AI detect the right incident?
   - `severity` — does the AI's severity match the fixed vocabulary
     (`low`/`medium`/`high`/`critical`)?
   - `affected_service` — did the AI name the right service(s)?
   - `probable_root_cause` — semantic comparison against the ground-truth cause.
   - **Evidence recall:** how many of the 37 grounded evidence items (across all
     reports) did the AI surface?
   - `troubleshooting_steps` / `expected_resolution` — quality of the proposed
     remediation.
3. **Correlation:** use `trace_id` to group all events of a single incident and
   `host` to localize where an incident occurred.
4. **Reproducibility:** because generation is seeded, the same logs are produced
   on every run, so backend test results are directly comparable across machines
   and CI runs. After regenerating logs, re-run `validate_reports.py` to confirm
   the reports still match the data.

## 11. Example Log Entry

Real entry from `logs/database_failure.jsonl` (line 4), shown pretty-printed:

```json
{
  "timestamp": "2026-10-11T06:05:12.759Z",
  "level": "WARNING",
  "service": "order-service",
  "incident_id": "database_failure",
  "trace_id": "trc-7f3a91c2",
  "host": "ord-svc-01",
  "message": "Connection pool nearing exhaustion",
  "details": {
    "database": "orders_db",
    "pool_active": 50,
    "pool_max": 50,
    "waiting_requests": 7
  }
}
```

## 12. Expected Output and Troubleshooting

### `python generate_logs.py`

```
Created: logs\database_failure.jsonl
Created: logs\http_500_error.jsonl
Created: logs\api_rate_limit.jsonl
Created: logs\application_exception.jsonl
Created: logs\request_timeout.jsonl
Created: logs\authentication_failure.jsonl
Created: logs\resource_exhaustion.jsonl

Done! Generated 7 log files.
```

### `python validate_logs.py`

```
PASS: logs\api_rate_limit.jsonl (5 entries)
PASS: logs\application_exception.jsonl (5 entries)
PASS: logs\authentication_failure.jsonl (5 entries)
PASS: logs\database_failure.jsonl (7 entries)
PASS: logs\http_500_error.jsonl (5 entries)
PASS: logs\request_timeout.jsonl (5 entries)
PASS: logs\resource_exhaustion.jsonl (6 entries)

All 7 files passed validation.
Total log entries: 38
```

### `python validate_reports.py`

```
PASS: expected_reports\api_rate_limit.json (incident: api_rate_limit, severity: medium, evidence: 5 items)
PASS: expected_reports\application_exception.json (incident: application_exception, severity: medium, evidence: 5 items)
PASS: expected_reports\authentication_failure.json (incident: authentication_failure, severity: low, evidence: 5 items)
PASS: expected_reports\database_failure.json (incident: database_failure, severity: high, evidence: 6 items)
PASS: expected_reports\http_500_error.json (incident: http_500_error, severity: high, evidence: 5 items)
PASS: expected_reports\request_timeout.json (incident: request_timeout, severity: medium, evidence: 5 items)
PASS: expected_reports\resource_exhaustion.json (incident: resource_exhaustion, severity: high, evidence: 6 items)

All 7 reports passed validation.
Total evidence items: 37
```

### Troubleshooting

| Error message | Likely cause | Fix |
|---------------|--------------|-----|
| `Log directory not found: logs` | Running from the wrong directory | Run the scripts from the project root |
| `Expected 7 files, found N` | Logs missing or extra files in `logs/` | Run `python generate_logs.py` (or remove unrelated files) |
| `Invalid JSON in logs\...:line` | A log line is corrupted | Regenerate the logs |
| `Missing fields in logs\...:line` | An entry lacks a required field | Regenerate the logs |
| `Invalid log level '...'` | Level outside `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` | Fix the entry; the generator only emits `INFO`/`WARNING`/`ERROR` |
| `Invalid timestamp format ...` / `Timestamps out of order` | Non-ISO 8601 or non-chronological entries | Regenerate the logs |
| `Reports directory not found: expected_reports` | `expected_reports/` missing | Restore the seven report files from the repository |
| `Expected 7 reports, found N` / `Report set mismatch` | Missing or extra report files | Ensure exactly the seven expected report files exist |
| `Evidence timestamp not found in logs\...` | A report cites a log entry that doesn't exist | Regenerate reports after regenerating logs so they stay in sync |
| `Evidence level/message/trace_id mismatch` | Report evidence drifted from the source logs | Regenerate logs and reports together, then re-validate |
