from prometheus_client import Counter, Histogram

# HTTP API Metrics
API_REQUESTS = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"]
)

API_ERRORS = Counter(
    "api_errors_total",
    "Total API errors",
    ["method", "endpoint", "status_code", "error_type"]
)

REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"]
)

# Domain Metrics
SIGNAL_GENERATION = Counter(
    "signal_generation_total",
    "Total signal generation attempts",
    ["symbol", "timeframe", "status"]  # status: success, failure
)

EXCHANGE_FAILURES = Counter(
    "exchange_failures_total",
    "Total exchange/data-source failures",
    ["exchange", "operation"]
)

SCHEDULER_EXECUTIONS = Counter(
    "scheduler_executions_total",
    "Total scheduler job executions",
    ["job", "status"]  # status: success, failure
)
