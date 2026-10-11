/* ==========================================================================
   AI Incident Detective — sample results (Demo mode only)
   --------------------------------------------------------------------------
   These are hand-authored examples based on the ground-truth reports in
   ../log_generation/expected_reports/. They exist ONLY so the interface can be
   demonstrated before the backend is ready. They are NOT produced by any AI
   model and are always shown behind a "Demo mode" banner.
   ========================================================================== */

window.AID_SAMPLE_REPORTS = {
  database_failure: {
    incident_id: "database_failure",
    incident_type: "database_connection_failure",
    severity: "high",
    affected_service: "order-service",
    probable_root_cause:
      "Connection pool exhaustion on the orders_db primary (db-primary-01): the pool filled to 50/50 connections with 7 requests waiting, the INSERT INTO orders query latency reached 4500 ms, and subsequent connections timed out after 30 seconds (error code DB_TIMEOUT_30000), so order ORD-101 could not be saved after 3 retries.",
    evidence: [
      { timestamp: "2026-10-11T06:05:04.114Z", level: "INFO", service: "order-service", host: "ord-svc-01", message: "Received order request", details: { order_id: "ORD-101", user_id: "usr-8842", total_amount: 129.99 } },
      { timestamp: "2026-10-11T06:05:09.025Z", level: "WARNING", service: "order-service", host: "ord-svc-01", message: "Database response is slow", details: { database: "orders_db", query: "INSERT INTO orders", latency_ms: 4500, pool_active: 46, pool_max: 50 } },
      { timestamp: "2026-10-11T06:05:12.759Z", level: "WARNING", service: "order-service", host: "ord-svc-01", message: "Connection pool nearing exhaustion", details: { database: "orders_db", pool_active: 50, pool_max: 50, waiting_requests: 7 } },
      { timestamp: "2026-10-11T06:05:18.281Z", level: "ERROR", service: "order-service", host: "ord-svc-01", message: "Database connection timeout", details: { database: "orders_db", db_host: "db-primary-01", timeout_seconds: 30, error_code: "DB_TIMEOUT_30000" } },
      { timestamp: "2026-10-11T06:05:21.250Z", level: "ERROR", service: "order-service", host: "ord-svc-01", message: "Order could not be saved", details: { order_id: "ORD-101", reason: "database_unavailable", retries_attempted: 3 } },
      { timestamp: "2026-10-11T06:05:26.228Z", level: "WARNING", service: "order-service", host: "ord-svc-01", message: "Failover to replica initiated", details: { database: "orders_db", new_primary: "db-replica-02", estimated_recovery_seconds: 45 } }
    ],
    troubleshooting_steps: [
      "Check connection pool metrics for orders_db: pool_active reached pool_max of 50 with 7 waiting requests.",
      "Verify the health and load of the primary database host db-primary-01.",
      "Review the slow INSERT INTO orders query that took 4500 ms.",
      "Confirm the failover to db-replica-02 completed within the estimated 45 seconds.",
      "Verify that order ORD-101 is persisted or safely retried after the pool recovers."
    ],
    expected_resolution:
      "Failover to db-replica-02 completes within the estimated 45 seconds, the orders_db connection pool recovers below its 50-connection maximum, and order ORD-101 is successfully saved on retry."
  },

  http_500_error: {
    incident_id: "http_500_error",
    incident_type: "http_500_error",
    severity: "high",
    affected_service: "api-service",
    probable_root_cause:
      "The payment gateway was unreachable (upstream returned 503) during order creation: the call to payment_client.charge(order) at order_views.py line 88 raised InternalServerError, causing POST /api/orders to fail with HTTP 500. Request validation had passed in 4 ms, so the request input was not the cause.",
    evidence: [
      { timestamp: "2026-10-11T06:52:00.142Z", level: "INFO", service: "api-service", host: "api-svc-02", message: "Request received", details: { method: "POST", path: "/api/orders", client_ip: "203.0.113.44", content_length: 512 } },
      { timestamp: "2026-10-11T06:52:02.754Z", level: "INFO", service: "api-service", host: "api-svc-02", message: "Request validation completed", details: { schema: "order-v3", validation_ms: 4 } },
      { timestamp: "2026-10-11T06:52:05.104Z", level: "ERROR", service: "api-service", host: "api-svc-02", message: "Unexpected error while creating order", details: { exception: "InternalServerError", cause: "payment gateway unreachable", traceback: "Traceback (most recent call last):\n  File \"order_views.py\", line 88, in create_order\n    charge = payment_client.charge(order)\nInternalServerError: upstream returned 503" } },
      { timestamp: "2026-10-11T06:52:07.692Z", level: "ERROR", service: "api-service", host: "api-svc-02", message: "Request failed", details: { method: "POST", path: "/api/orders", status_code: 500, duration_ms: 1873, request_id: "req-5f9a21" } },
      { timestamp: "2026-10-11T06:52:12.758Z", level: "WARNING", service: "api-service", host: "api-svc-02", message: "Elevated 5xx rate detected", details: { window_seconds: 300, error_count: 14, threshold: 10 } }
    ],
    troubleshooting_steps: [
      "Check the payment gateway health: it returned 503 (service unavailable) to the upstream call.",
      "Review order_views.py line 88, where payment_client.charge(order) raised InternalServerError.",
      "Track request req-5f9a21 (trace trc-b21e48d7) to confirm the failure path.",
      "Monitor the 5xx rate: 14 errors in a 300-second window against a threshold of 10."
    ],
    expected_resolution:
      "The payment gateway recovers and stops returning 503, POST /api/orders succeeds end-to-end, and the 5xx rate drops back below the threshold of 10 errors per 300 seconds."
  },

  api_rate_limit: {
    incident_id: "api_rate_limit",
    incident_type: "api_rate_limiting",
    severity: "medium",
    affected_service: "gateway",
    probable_root_cause:
      "Client client-A exceeded its configured quota of 100 requests per 60-second window, reaching 120 requests per minute, so the gateway correctly rejected requests with HTTP 429 and advised a 60-second cooldown via the Retry-After header. This is expected protective behavior, not a server fault.",
    evidence: [
      { timestamp: "2026-10-11T07:38:00.913Z", level: "INFO", service: "gateway", host: "gw-edge-01", message: "API request received", details: { client: "client-A", endpoint: "/api/orders", method: "GET" } },
      { timestamp: "2026-10-11T07:38:03.558Z", level: "WARNING", service: "gateway", host: "gw-edge-01", message: "Request rate approaching limit", details: { client: "client-A", requests_per_minute: 90, limit: 100, window_seconds: 60 } },
      { timestamp: "2026-10-11T07:38:06.089Z", level: "ERROR", service: "gateway", host: "gw-edge-01", message: "Rate limit exceeded", details: { client: "client-A", status_code: 429, requests_per_minute: 120, limit: 100, window_seconds: 60 } },
      { timestamp: "2026-10-11T07:38:09.604Z", level: "WARNING", service: "gateway", host: "gw-edge-01", message: "Client throttled, retry advised", details: { client: "client-A", retry_after_seconds: 60, response_header: "Retry-After: 60" } },
      { timestamp: "2026-10-11T07:39:09.432Z", level: "INFO", service: "gateway", host: "gw-edge-01", message: "Rate limit window reset", details: { client: "client-A", requests_per_minute: 0 } }
    ],
    troubleshooting_steps: [
      "Confirm client-A's request pattern: 90 requests/minute approaching the limit, then 120 requests/minute against a 100 requests/minute limit.",
      "Verify the rate-limit configuration: 100 requests per 60-second window.",
      "Check that client-A honors the Retry-After: 60 response header.",
      "Confirm the window reset at 2026-10-11T07:39:09.432Z with requests_per_minute back to 0."
    ],
    expected_resolution:
      "client-A respects the 60-second Retry-After cooldown, the rate-limit window resets (already observed at 2026-10-11T07:39:09.432Z with 0 requests/minute), and subsequent requests are accepted below the 100 requests/minute limit."
  },

  application_exception: {
    incident_id: "application_exception",
    incident_type: "application_exception",
    severity: "medium",
    affected_service: "report-service",
    probable_root_cause:
      "Dirty input data in s3://reports-input/october.csv: the total_amount field contains the string \"N/A\" where a float is expected, raising a TypeError during the aggregation stage and failing report RPT-202 (error code E_RPT_TYPE).",
    evidence: [
      { timestamp: "2026-10-11T08:21:00.032Z", level: "INFO", service: "report-service", host: "rpt-svc-03", message: "Report generation started", details: { report_id: "RPT-202", report_type: "monthly_sales", user_id: "usr-5521" } },
      { timestamp: "2026-10-11T08:21:03.030Z", level: "INFO", service: "report-service", host: "rpt-svc-03", message: "Reading report input", details: { source: "s3://reports-input/october.csv", rows_expected: 1520 } },
      { timestamp: "2026-10-11T08:21:06.095Z", level: "ERROR", service: "report-service", host: "rpt-svc-03", message: "Unexpected data type", details: { exception: "TypeError", field: "total_amount", expected_type: "float", received_type: "str", offending_value: "N/A" } },
      { timestamp: "2026-10-11T08:21:08.223Z", level: "ERROR", service: "report-service", host: "rpt-svc-03", message: "Report generation failed", details: { report_id: "RPT-202", error_code: "E_RPT_TYPE", stage: "aggregation" } },
      { timestamp: "2026-10-11T08:21:12.238Z", level: "WARNING", service: "report-service", host: "rpt-svc-03", message: "Report queued for retry", details: { report_id: "RPT-202", retry_in_seconds: 300 } }
    ],
    troubleshooting_steps: [
      "Inspect rows in s3://reports-input/october.csv where total_amount is not numeric (offending value: \"N/A\").",
      "Clean or sanitize the input data so total_amount can be parsed as a float.",
      "Monitor the retry already queued for report RPT-202 (retry_in_seconds: 300).",
      "Add input validation for non-numeric total_amount values to prevent recurrence."
    ],
    expected_resolution:
      "After the input data is corrected or sanitized, the queued retry of report RPT-202 completes the aggregation stage successfully and the monthly_sales report is generated for user usr-5521."
  },

  request_timeout: {
    incident_id: "request_timeout",
    incident_type: "request_timeout",
    severity: "medium",
    affected_service: "search-service",
    probable_root_cause:
      "The downstream dependency catalog-service (/api/catalog/lookup) responded too slowly - 4200 ms initially, then 5100 ms on the retry - consuming the entire 5-second timeout budget (waited 5012 ms), so the search request failed with HTTP 504 after both retry attempts were exhausted.",
    evidence: [
      { timestamp: "2026-10-11T09:27:00.517Z", level: "INFO", service: "search-service", host: "srch-svc-01", message: "Search request received", details: { path: "/api/search", query: "wireless headphones", user_id: "usr-3307" } },
      { timestamp: "2026-10-11T09:27:02.616Z", level: "WARNING", service: "search-service", host: "srch-svc-01", message: "Dependency response is slow", details: { dependency: "catalog-service", dependency_endpoint: "/api/catalog/lookup", latency_ms: 4200 } },
      { timestamp: "2026-10-11T09:27:04.027Z", level: "WARNING", service: "search-service", host: "srch-svc-01", message: "Retry attempt failed", details: { dependency: "catalog-service", attempt: 1, max_attempts: 2, latency_ms: 5100 } },
      { timestamp: "2026-10-11T09:27:06.574Z", level: "ERROR", service: "search-service", host: "srch-svc-01", message: "Request timed out", details: { path: "/api/search", timeout_seconds: 5, waited_ms: 5012, dependency: "catalog-service" } },
      { timestamp: "2026-10-11T09:27:08.203Z", level: "INFO", service: "search-service", host: "srch-svc-01", message: "Request completed with failure", details: { status_code: 504, duration_ms: 5015 } }
    ],
    troubleshooting_steps: [
      "Check the health and performance of catalog-service and its /api/catalog/lookup endpoint.",
      "Compare the dependency latency (4200 ms, then 5100 ms) against the 5-second request timeout.",
      "Review the retry policy: attempt 1 of max_attempts 2 already failed with 5100 ms latency.",
      "Consider a circuit breaker or a raised timeout for catalog-service calls if the slowness persists."
    ],
    expected_resolution:
      "catalog-service latency drops below the 5-second timeout budget, /api/search requests complete within the timeout, and retries succeed instead of returning 504."
  },

  authentication_failure: {
    incident_id: "authentication_failure",
    incident_type: "authentication_failure",
    severity: "low",
    affected_service: "auth-service",
    probable_root_cause:
      "Three consecutive invalid password attempts for user test-user-01 from client IP 198.51.100.23 exhausted the lockout threshold of 3, so auth-service rejected the login (reason: invalid_credentials) and locked the account for 15 minutes. All attempts came from a single user and a single IP, which is consistent with a forgotten password rather than a distributed brute-force attack.",
    evidence: [
      { timestamp: "2026-10-11T10:09:00.733Z", level: "INFO", service: "auth-service", host: "auth-svc-01", message: "Login attempt received", details: { user_id: "test-user-01", client_ip: "198.51.100.23", method: "password" } },
      { timestamp: "2026-10-11T10:09:03.665Z", level: "WARNING", service: "auth-service", host: "auth-svc-01", message: "Invalid password", details: { user_id: "test-user-01", attempt: 1, max_attempts: 3 } },
      { timestamp: "2026-10-11T10:09:07.718Z", level: "WARNING", service: "auth-service", host: "auth-svc-01", message: "Invalid password", details: { user_id: "test-user-01", attempt: 2, max_attempts: 3 } },
      { timestamp: "2026-10-11T10:09:10.558Z", level: "WARNING", service: "auth-service", host: "auth-svc-01", message: "Account approaching lockout", details: { user_id: "test-user-01", attempts_remaining: 1, lockout_threshold: 3 } },
      { timestamp: "2026-10-11T10:09:13.429Z", level: "ERROR", service: "auth-service", host: "auth-svc-01", message: "Authentication rejected", details: { user_id: "test-user-01", reason: "invalid_credentials", account_locked: true, lockout_minutes: 15 } }
    ],
    troubleshooting_steps: [
      "Confirm with user test-user-01 whether they made the attempts from 198.51.100.23 (a single user and single IP suggests forgotten credentials).",
      "Verify the account unlocks after the 15-minute lockout (lockout_minutes: 15).",
      "Watch for repeated failures from 198.51.100.23 after the unlock, which would indicate a brute-force attempt.",
      "Offer a password reset for test-user-01 if the failures continue."
    ],
    expected_resolution:
      "The account unlocks after the 15-minute lockout, test-user-01 authenticates successfully with the correct password or a reset, and no further invalid-password warnings are logged for 198.51.100.23."
  },

  resource_exhaustion: {
    incident_id: "resource_exhaustion",
    incident_type: "resource_exhaustion",
    severity: "high",
    affected_service: "system-monitor, file-service",
    probable_root_cause:
      "Disk space exhaustion on mount /var/data: usage climbed from 74% to 88% (above the 85% threshold) to 96% (above the 90% threshold) with only 412 MB free, causing file-service to fail writing /var/data/tmp/upload_4f2a.tmp with ENOSPC (insufficient_disk_space). Memory pressure (85% memory, 41% swap) is a secondary signal.",
    evidence: [
      { timestamp: "2026-10-11T11:33:00.225Z", level: "INFO", service: "system-monitor", host: "mon-agent-01", message: "Resource check completed", details: { cpu_percent: 45, memory_percent: 60, disk_percent: 74 } },
      { timestamp: "2026-10-11T11:33:30.459Z", level: "WARNING", service: "system-monitor", host: "mon-agent-01", message: "Disk usage is high", details: { mount: "/var/data", disk_percent: 88, threshold_percent: 85 } },
      { timestamp: "2026-10-11T11:33:55.603Z", level: "WARNING", service: "system-monitor", host: "mon-agent-01", message: "Memory pressure rising", details: { memory_percent: 85, swap_percent: 41 } },
      { timestamp: "2026-10-11T11:34:18.284Z", level: "ERROR", service: "system-monitor", host: "mon-agent-01", message: "Disk usage critical", details: { mount: "/var/data", disk_percent: 96, threshold_percent: 90, free_mb: 412 } },
      { timestamp: "2026-10-11T11:34:22.828Z", level: "ERROR", service: "file-service", host: "file-svc-02", message: "Unable to write temporary file", details: { path: "/var/data/tmp/upload_4f2a.tmp", reason: "insufficient_disk_space", errno: "ENOSPC" } },
      { timestamp: "2026-10-11T11:34:30.890Z", level: "WARNING", service: "system-monitor", host: "mon-agent-01", message: "Cleanup job triggered", details: { deleted_temp_mb: 1840, disk_percent_after: 89 } }
    ],
    troubleshooting_steps: [
      "Identify the largest consumers of disk space on /var/data (usage reached 96% with 412 MB free).",
      "Verify the cleanup job that deleted 1840 MB of temporary files and returned usage to 89%.",
      "Keep monitoring /var/data against the 85% warning and 90% critical thresholds.",
      "Investigate the secondary memory pressure (85% memory, 41% swap)."
    ],
    expected_resolution:
      "The cleanup job keeps /var/data below the 90% critical threshold (already reduced to 89% by deleting 1840 MB), temporary file writes succeed again without ENOSPC, and memory pressure subsides."
  }
};

/* Fallback order when a filename doesn't match a known incident. */
window.AID_SAMPLE_ORDER = [
  "database_failure",
  "http_500_error",
  "api_rate_limit",
  "application_exception",
  "request_timeout",
  "authentication_failure",
  "resource_exhaustion"
];
