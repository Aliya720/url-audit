# Task B: Observability & Rollback Plan

## Overview
This document outlines the observability strategy, health check mechanisms, logging standards, metrics tracking, and zero-downtime rollback procedures for PulseWatch.

---

## 1. Observability Strategy

### 1.1 Structured JSON Logging
All application logs are formatted as structured JSON using `python-json-logger` for automated ingestion into log management tools (Datadog, Loki, CloudWatch).

**Standard Fields**:
- `timestamp`: ISO-8601 UTC timestamp
- `levelname`: `INFO`, `WARNING`, `ERROR`
- `request_id`: Correlated request identifier (`req_...`)
- `method`: HTTP method
- `path`: Requested endpoint
- `status_code`: Response status code
- `duration_ms`: Execution duration
- `client_key`: Masked client token or IP address
- `cache`: `hit` | `miss` (if audit check)
- `error_code`: Structured error code (if non-2xx)

### 1.2 Error Tracking (Sentry)
- `sentry-sdk` integrated into `web`, `worker`, and `beat` containers.
- Standard expected API errors (`INVALID_URL`, `RATE_LIMITED`, `TARGET_TIMEOUT`) are handled cleanly by DRF custom exception handlers and logged as operational warnings without polluting Sentry error budgets.
- Only genuinely unhandled exceptions trigger Sentry alerts.
- Events are tagged with `request_id` and `SENTRY_ENVIRONMENT`.

### 1.3 Health Monitoring (`GET /api/health`)
Implemented via `django-health-check`. Performs real-time readiness/liveness probing across infrastructure components:
- **Database**: Executes `SELECT 1` on PostgreSQL.
- **Redis**: Tests key set/get operations.
- **Celery Worker**: Sends control ping to active Celery workers.

Returns `200 OK` when healthy:
```json
{
  "status": "ok",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "celery_worker": "ok"
  }
}
```
Returns `503 Service Unavailable` if any dependency is unreachable.

### 1.4 Prometheus Metrics (`/metrics`)
`django-prometheus` exposes application metrics:
- Request latency histograms (`django_http_requests_latency_seconds_by_view_method`)
- Response status code counters
- Database connection pool stats
- Redis cache hit/miss ratio

---

## 2. Deployment & Rollback Plan

### 2.1 Deployment Pipeline (GitHub Actions + Docker)
1. **CI Verification**: GitHub Actions runs flake8, black format checks, pytest test suite with coverage, and builds Docker images on every push.
2. **Tagging**: Successfully built images are tagged with git commit SHA and release tag (e.g., `pulsewatch-web:v1.2.0`, `pulsewatch-web:latest`).
3. **Deployment Command**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans
   docker-compose exec web python manage.py migrate --noinput
   ```

### 2.2 Rollback Trigger Criteria
A rollback is triggered automatically if:
- `/api/health` returns `503` for >3 consecutive probes post-deployment.
- Error rate on `/api/audits` exceeds 5% over a 5-minute window.
- Unhandled exceptions in Sentry spike above threshold.

### 2.3 Automated Rollback Procedure

```bash
# 1. Identify previous healthy release tag
PREV_TAG="v1.1.0"

# 2. Update image tags to previous release
export IMAGE_TAG=${PREV_TAG}

# 3. Pull and restart containers with previous version
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. Roll back database migrations if backward-incompatible schema changes occurred
docker-compose exec web python manage.py migrate checks <previous_migration_number>

# 5. Verify health check recovers
curl -f http://localhost/api/health
```

---

## 3. Production Readiness Verification

- [x] All 74 unit, integration, and e2e tests passing
- [x] Input validation & SSRF security controls active
- [x] Redis cache & token bucket rate limiting verified
- [x] Celery worker & django-celery-beat scheduling active
- [x] Structured JSON logging with request ID propagation
- [x] Health check endpoint (`/api/health`) verified
- [x] Required footer credit line ("Built for Digital Heroes Training Task") verified in React UI
