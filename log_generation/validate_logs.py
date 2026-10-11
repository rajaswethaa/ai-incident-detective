"""Validate the JSONL incident logs in the logs/ directory."""

import json
import re
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("logs")
EXPECTED_FILE_COUNT = 7

REQUIRED_FIELDS = {
    "timestamp", "level", "service", "incident_id", "message", "details"
}

VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$"
)


def validate_file(path: Path) -> int:
    """Validate one JSONL file and return its entry count."""
    entries = 0
    previous_timestamp = None

    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as error:
                raise SystemExit(f"Invalid JSON in {path}:{line_number}: {error}")

            if not isinstance(entry, dict):
                raise SystemExit(f"Entry is not a JSON object: {path}:{line_number}")

            missing = REQUIRED_FIELDS - entry.keys()
            if missing:
                raise SystemExit(
                    f"Missing fields in {path}:{line_number}: {sorted(missing)}"
                )

            if entry["level"] not in VALID_LEVELS:
                raise SystemExit(
                    f"Invalid log level '{entry['level']}' in {path}:{line_number}"
                )

            if not isinstance(entry["details"], dict):
                raise SystemExit(
                    f"'details' must be an object in {path}:{line_number}"
                )

            if entry["incident_id"] != path.stem:
                raise SystemExit(
                    f"incident_id '{entry['incident_id']}' does not match "
                    f"filename in {path}:{line_number}"
                )

            timestamp = entry["timestamp"]
            if not TIMESTAMP_PATTERN.match(timestamp):
                raise SystemExit(
                    f"Invalid timestamp format in {path}:{line_number}: {timestamp}"
                )

            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if previous_timestamp is not None and parsed < previous_timestamp:
                raise SystemExit(f"Timestamps out of order in {path}:{line_number}")
            previous_timestamp = parsed

            entries += 1

    if entries == 0:
        raise SystemExit(f"Empty log file: {path}")

    return entries


def main() -> None:
    if not LOG_DIR.is_dir():
        raise SystemExit(f"Log directory not found: {LOG_DIR}")

    files = sorted(LOG_DIR.glob("*.jsonl"))

    if len(files) != EXPECTED_FILE_COUNT:
        raise SystemExit(f"Expected {EXPECTED_FILE_COUNT} files, found {len(files)}")

    total_entries = 0
    for path in files:
        entries = validate_file(path)
        total_entries += entries
        print(f"PASS: {path} ({entries} entries)")

    print(f"\nAll {len(files)} files passed validation.")
    print(f"Total log entries: {total_entries}")


if __name__ == "__main__":
    main()
