"""Generate seven realistic JSONL incident log files for AI Incident Detective.

Each file tells one incident story with a realistic narrative arc:
normal INFO events -> WARNING early-warning signs -> the ERROR failure ->
follow-up events (failover, retry, throttling, recovery).
"""

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG_DIR = Path("logs")

# All incidents happen on the same morning (UTC). Each scenario starts at
# BASE_TIME + start_after_minutes; each event then adds offset_seconds.
BASE_TIME = datetime(2026, 10, 11, 6, 0, 0, tzinfo=timezone.utc)

# Deterministic millisecond component so output is reproducible.
rng = random.Random(42)

HOSTS = {
    "order-service": "ord-svc-01",
    "api-service": "api-svc-02",
    "gateway": "gw-edge-01",
    "report-service": "rpt-svc-03",
    "search-service": "srch-svc-01",
    "auth-service": "auth-svc-01",
    "system-monitor": "mon-agent-01",
    "file-service": "file-svc-02",
}

# filename -> (start_after_minutes, trace_id, events)
# event -> (offset_seconds, level, service, message, details)
SCENARIOS = {
    # 1. Database connection failure - connection pool exhaustion on the primary DB
    "database_failure.jsonl": (
        5, "trc-7f3a91c2",
        [
            (0, "INFO", "order-service", "Application started",
             {"version": "2.14.3", "port": 8080}),
            (4, "INFO", "order-service", "Received order request",
             {"order_id": "ORD-101", "user_id": "usr-8842", "total_amount": 129.99}),
            (9, "WARNING", "order-service", "Database response is slow",
             {"database": "orders_db", "query": "INSERT INTO orders",
              "latency_ms": 4500, "pool_active": 46, "pool_max": 50}),
            (12, "WARNING", "order-service", "Connection pool nearing exhaustion",
             {"database": "orders_db", "pool_active": 50, "pool_max": 50,
              "waiting_requests": 7}),
            (18, "ERROR", "order-service", "Database connection timeout",
             {"database": "orders_db", "db_host": "db-primary-01",
              "timeout_seconds": 30, "error_code": "DB_TIMEOUT_30000"}),
            (21, "ERROR", "order-service", "Order could not be saved",
             {"order_id": "ORD-101", "reason": "database_unavailable",
              "retries_attempted": 3}),
            (26, "WARNING", "order-service", "Failover to replica initiated",
             {"database": "orders_db", "new_primary": "db-replica-02",
              "estimated_recovery_seconds": 45}),
        ],
    ),

    # 2. HTTP 500 error - unhandled exception while creating an order
    "http_500_error.jsonl": (
        52, "trc-b21e48d7",
        [
            (0, "INFO", "api-service", "Request received",
             {"method": "POST", "path": "/api/orders",
              "client_ip": "203.0.113.44", "content_length": 512}),
            (2, "INFO", "api-service", "Request validation completed",
             {"schema": "order-v3", "validation_ms": 4}),
            (5, "ERROR", "api-service", "Unexpected error while creating order",
             {"exception": "InternalServerError",
              "cause": "payment gateway unreachable",
              "traceback": "Traceback (most recent call last):\n"
                           "  File \"order_views.py\", line 88, in create_order\n"
                           "    charge = payment_client.charge(order)\n"
                           "InternalServerError: upstream returned 503"}),
            (7, "ERROR", "api-service", "Request failed",
             {"method": "POST", "path": "/api/orders", "status_code": 500,
              "duration_ms": 1873, "request_id": "req-5f9a21"}),
            (12, "WARNING", "api-service", "Elevated 5xx rate detected",
             {"window_seconds": 300, "error_count": 14, "threshold": 10}),
        ],
    ),

    # 3. API rate limiting - client exceeds its per-minute quota
    "api_rate_limit.jsonl": (
        98, "trc-4d6c0a99",
        [
            (0, "INFO", "gateway", "API request received",
             {"client": "client-A", "endpoint": "/api/orders", "method": "GET"}),
            (3, "WARNING", "gateway", "Request rate approaching limit",
             {"client": "client-A", "requests_per_minute": 90,
              "limit": 100, "window_seconds": 60}),
            (6, "ERROR", "gateway", "Rate limit exceeded",
             {"client": "client-A", "status_code": 429,
              "requests_per_minute": 120, "limit": 100, "window_seconds": 60}),
            (9, "WARNING", "gateway", "Client throttled, retry advised",
             {"client": "client-A", "retry_after_seconds": 60,
              "response_header": "Retry-After: 60"}),
            (69, "INFO", "gateway", "Rate limit window reset",
             {"client": "client-A", "requests_per_minute": 0}),
        ],
    ),

    # 4. Application exception - TypeError during report aggregation
    "application_exception.jsonl": (
        141, "trc-91af6e04",
        [
            (0, "INFO", "report-service", "Report generation started",
             {"report_id": "RPT-202", "report_type": "monthly_sales",
              "user_id": "usr-5521"}),
            (3, "INFO", "report-service", "Reading report input",
             {"source": "s3://reports-input/october.csv", "rows_expected": 1520}),
            (6, "ERROR", "report-service", "Unexpected data type",
             {"exception": "TypeError", "field": "total_amount",
              "expected_type": "float", "received_type": "str",
              "offending_value": "N/A"}),
            (8, "ERROR", "report-service", "Report generation failed",
             {"report_id": "RPT-202", "error_code": "E_RPT_TYPE",
              "stage": "aggregation"}),
            (12, "WARNING", "report-service", "Report queued for retry",
             {"report_id": "RPT-202", "retry_in_seconds": 300}),
        ],
    ),

    # 5. Request timeout - downstream catalog-service too slow
    "request_timeout.jsonl": (
        207, "trc-c5028b3e",
        [
            (0, "INFO", "search-service", "Search request received",
             {"path": "/api/search", "query": "wireless headphones",
              "user_id": "usr-3307"}),
            (2, "WARNING", "search-service", "Dependency response is slow",
             {"dependency": "catalog-service",
              "dependency_endpoint": "/api/catalog/lookup", "latency_ms": 4200}),
            (4, "WARNING", "search-service", "Retry attempt failed",
             {"dependency": "catalog-service", "attempt": 1, "max_attempts": 2,
              "latency_ms": 5100}),
            (6, "ERROR", "search-service", "Request timed out",
             {"path": "/api/search", "timeout_seconds": 5, "waited_ms": 5012,
              "dependency": "catalog-service"}),
            (8, "INFO", "search-service", "Request completed with failure",
             {"status_code": 504, "duration_ms": 5015}),
        ],
    ),

    # 6. Authentication failure - repeated bad passwords end in lockout
    "authentication_failure.jsonl": (
        249, "trc-e77b1d55",
        [
            (0, "INFO", "auth-service", "Login attempt received",
             {"user_id": "test-user-01", "client_ip": "198.51.100.23",
              "method": "password"}),
            (3, "WARNING", "auth-service", "Invalid password",
             {"user_id": "test-user-01", "attempt": 1, "max_attempts": 3}),
            (7, "WARNING", "auth-service", "Invalid password",
             {"user_id": "test-user-01", "attempt": 2, "max_attempts": 3}),
            (10, "WARNING", "auth-service", "Account approaching lockout",
             {"user_id": "test-user-01", "attempts_remaining": 1,
              "lockout_threshold": 3}),
            (13, "ERROR", "auth-service", "Authentication rejected",
             {"user_id": "test-user-01", "reason": "invalid_credentials",
              "account_locked": True, "lockout_minutes": 15}),
        ],
    ),

    # 7. Resource exhaustion - disk fills up until writes fail
    "resource_exhaustion.jsonl": (
        333, "trc-2a98f6c1",
        [
            (0, "INFO", "system-monitor", "Resource check completed",
             {"cpu_percent": 45, "memory_percent": 60, "disk_percent": 74}),
            (30, "WARNING", "system-monitor", "Disk usage is high",
             {"mount": "/var/data", "disk_percent": 88, "threshold_percent": 85}),
            (55, "WARNING", "system-monitor", "Memory pressure rising",
             {"memory_percent": 85, "swap_percent": 41}),
            (78, "ERROR", "system-monitor", "Disk usage critical",
             {"mount": "/var/data", "disk_percent": 96, "threshold_percent": 90,
              "free_mb": 412}),
            (82, "ERROR", "file-service", "Unable to write temporary file",
             {"path": "/var/data/tmp/upload_4f2a.tmp",
              "reason": "insufficient_disk_space", "errno": "ENOSPC"}),
            (90, "WARNING", "system-monitor", "Cleanup job triggered",
             {"deleted_temp_mb": 1840, "disk_percent_after": 89}),
        ],
    ),
}


def create_logs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    for filename, (start_after_minutes, trace_id, events) in SCENARIOS.items():
        file_path = LOG_DIR / filename
        incident_start = BASE_TIME + timedelta(minutes=start_after_minutes)

        with file_path.open("w", encoding="utf-8") as file:
            for offset_seconds, level, service, message, details in events:
                moment = incident_start + timedelta(
                    seconds=offset_seconds, milliseconds=rng.randrange(1000)
                )
                entry = {
                    "timestamp": moment.isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z"),
                    "level": level,
                    "service": service,
                    "incident_id": file_path.stem,
                    "trace_id": trace_id,
                    "host": HOSTS[service],
                    "message": message,
                    "details": details,
                }
                file.write(json.dumps(entry) + "\n")

        print(f"Created: {file_path}")

    print(f"\nDone! Generated {len(SCENARIOS)} log files.")


if __name__ == "__main__":
    create_logs()
