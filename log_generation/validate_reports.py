"""Validate the expected incident reports in expected_reports/.

Checks report structure and cross-checks every evidence item against the
corresponding source log in logs/ so the reports remain true ground truth.
"""

import json
import re
from pathlib import Path

REPORTS_DIR = Path("expected_reports")
LOG_DIR = Path("logs")

EXPECTED_REPORT_COUNT = 7

EXPECTED_INCIDENT_IDS = {
    "database_failure",
    "http_500_error",
    "api_rate_limit",
    "application_exception",
    "request_timeout",
    "authentication_failure",
    "resource_exhaustion",
}

REQUIRED_FIELDS = [
    "incident_id",
    "incident_type",
    "severity",
    "affected_service",
    "probable_root_cause",
    "evidence",
    "troubleshooting_steps",
    "expected_resolution",
]

STRING_FIELDS = [
    "incident_id",
    "incident_type",
    "severity",
    "affected_service",
    "probable_root_cause",
    "expected_resolution",
]

VALID_SEVERITIES = {"low", "medium", "high", "critical"}

EVIDENCE_FIELDS = {"timestamp", "level", "service", "message"}

TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$"
)


def load_log_entries(log_path: Path) -> list:
    entries = []
    with log_path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise SystemExit(f"Invalid JSON in {log_path}:{line_number}: {error}")
    return entries


def validate_report(path: Path) -> dict:
    """Validate one report file and return the parsed report."""
    with path.open(encoding="utf-8") as file:
        try:
            report = json.load(file)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid JSON in {path}: {error}")

    if not isinstance(report, dict):
        raise SystemExit(f"Report is not a JSON object: {path}")

    missing = [field for field in REQUIRED_FIELDS if field not in report]
    if missing:
        raise SystemExit(f"Missing fields in {path}: {missing}")

    for field in STRING_FIELDS:
        value = report[field]
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f"Field '{field}' must be a non-empty string in {path}")

    if report["severity"].lower() not in VALID_SEVERITIES:
        raise SystemExit(
            f"Invalid severity '{report['severity']}' in {path} "
            f"(expected one of {sorted(VALID_SEVERITIES)})"
        )

    if not isinstance(report["evidence"], list) or not report["evidence"]:
        raise SystemExit(f"'evidence' must be a non-empty list in {path}")

    if not isinstance(report["troubleshooting_steps"], list) or not report["troubleshooting_steps"]:
        raise SystemExit(f"'troubleshooting_steps' must be a non-empty list in {path}")

    for index, step in enumerate(report["troubleshooting_steps"], 1):
        if not isinstance(step, str) or not step.strip():
            raise SystemExit(
                f"Troubleshooting step {index} is not a non-empty string in {path}"
            )

    # Cross-check against the corresponding source log file.
    log_path = LOG_DIR / f"{path.stem}.jsonl"
    if not log_path.is_file():
        raise SystemExit(f"Corresponding log file not found: {log_path}")

    if report["incident_id"] != log_path.stem:
        raise SystemExit(
            f"incident_id '{report['incident_id']}' does not match "
            f"log filename '{log_path.stem}' in {path}"
        )

    log_by_timestamp = {entry["timestamp"]: entry for entry in load_log_entries(log_path)}

    for index, item in enumerate(report["evidence"], 1):
        if not isinstance(item, dict):
            raise SystemExit(f"Evidence item {index} is not a JSON object in {path}")

        missing = EVIDENCE_FIELDS - item.keys()
        if missing:
            raise SystemExit(
                f"Evidence item {index} is missing fields {sorted(missing)} in {path}"
            )

        timestamp = item["timestamp"]
        if not TIMESTAMP_PATTERN.match(timestamp):
            raise SystemExit(
                f"Invalid timestamp in evidence item {index} of {path}: {timestamp}"
            )

        log_entry = log_by_timestamp.get(timestamp)
        if log_entry is None:
            raise SystemExit(
                f"Evidence timestamp not found in {log_path}: {timestamp}"
            )

        if item["level"] != log_entry["level"]:
            raise SystemExit(
                f"Evidence level mismatch in {path} item {index}: "
                f"{item['level']} != {log_entry['level']}"
            )

        if item["message"] != log_entry["message"]:
            raise SystemExit(
                f"Evidence message mismatch in {path} item {index}:\n"
                f"  report: {item['message']}\n"
                f"  log:    {log_entry['message']}"
            )

        if item.get("trace_id") != log_entry.get("trace_id"):
            raise SystemExit(
                f"Evidence trace_id mismatch in {path} item {index}: "
                f"{item.get('trace_id')} != {log_entry.get('trace_id')}"
            )

    return report


def main() -> None:
    if not REPORTS_DIR.is_dir():
        raise SystemExit(f"Reports directory not found: {REPORTS_DIR}")

    reports = sorted(REPORTS_DIR.glob("*.json"))

    if len(reports) != EXPECTED_REPORT_COUNT:
        raise SystemExit(f"Expected {EXPECTED_REPORT_COUNT} reports, found {len(reports)}")

    found_ids = {path.stem for path in reports}
    if found_ids != EXPECTED_INCIDENT_IDS:
        raise SystemExit(
            f"Report set mismatch. "
            f"Missing: {sorted(EXPECTED_INCIDENT_IDS - found_ids)}, "
            f"unexpected: {sorted(found_ids - EXPECTED_INCIDENT_IDS)}"
        )

    total_evidence = 0
    for path in reports:
        report = validate_report(path)
        total_evidence += len(report["evidence"])
        print(
            f"PASS: {path} "
            f"(incident: {report['incident_id']}, "
            f"severity: {report['severity']}, "
            f"evidence: {len(report['evidence'])} items)"
        )

    print(f"\nAll {len(reports)} reports passed validation.")
    print(f"Total evidence items: {total_evidence}")


if __name__ == "__main__":
    main()
