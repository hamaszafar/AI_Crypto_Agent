# Observability & Alerting Foundations

This document outlines the core alerting rules intended for Prometheus. These alerts monitor the fundamental health, performance, and reliability of the Trading Signal Agent.

## Alerting Rules

### 1. API Unavailability
**Condition:** API is down or not responding.
```yaml
- alert: ApiDown
  expr: up{job="trading_signal_api"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "API is down"
    description: "The API has been unreachable for more than 1 minute."
```

### 2. High Error Rate
**Condition:** More than 5% of requests return 5xx errors in a 5-minute window.
```yaml
- alert: HighApiErrorRate
  expr: sum(rate(api_requests_total{status_code=~"5.."}[5m])) / sum(rate(api_requests_total[5m])) > 0.05
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "High API Error Rate"
```

### 3. High Request Latency
**Condition:** 95th percentile request latency is over 500ms.
```yaml
- alert: HighRequestLatency
  expr: histogram_quantile(0.95, sum(rate(api_request_latency_seconds_bucket[5m])) by (le)) > 0.5
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "High API Request Latency"
```

### 4. Exchange / Data Source Failure
**Condition:** Rate of exchange fetch failures is non-zero.
```yaml
- alert: ExchangeDataFailure
  expr: rate(exchange_failures_total[5m]) > 0
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "Exchange Data Fetch Failures detected"
```

### 5. Signal Generation Failure
**Condition:** Frequent signal generation failures (e.g. calculation errors).
```yaml
- alert: SignalGenerationFailure
  expr: rate(signal_generation_total{status="failure"}[5m]) > 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Signal Generation is failing"
```

### 6. Scheduler Failure
**Condition:** Scheduler job fails or isn't running successfully.
```yaml
- alert: SchedulerFailure
  expr: rate(scheduler_executions_total{status="failure"}[5m]) > 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Scheduler executions are failing"
```
