# Technical Requirements Document (TRD)

## PulseWatch *(working title — pending confirmation, see PRD §0.1)*
**Digital Heroes SDE Qualification Task — Task A (Production Build) + Task B (Scale Design)**

| | |
|---|---|
| **Doc** | 2 of 6 — TRD |
| **Version** | 2.1 — added error tracking, testing libraries, and scalability/observability components (§1.1) |
| **Status** | Draft for Review |
| **Traces to** | PRD v3.0 — every section below is tagged with the FR/goal it implements |
| **Next docs** | App Flow → UI/UX Brief → Backend Schema → Implementation Plan |

---

## 0. Purpose & Boundaries

This doc answers **"how does the Must-have and Should-have scope from the PRD actually get built"** — concrete API contract, request lifecycle, storage decisions, and CI pipeline. It does **not** re-litigate technology tradeoffs (chosen vs. rejected alternatives) — that reasoning belongs in Task B's Technology Decision Record. Where a decision is made here, it's stated with a one-line rationale.

Scope discipline carries over from the PRD: **§4–§9 below implement PRD §4.1/§5.1 (Must-have) and §4.2/§5.2 (Should-have) only.** PRD §4.5 (Future Roadmap) is referenced once at the end (§13) purely to show the contract doesn't need a redesign to support it later.

---

## 1. Confirmed Stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | **React.js** | Single-page app: URL input → submit → results view (Must-have); Monitor registration/history UI if Should-have is built in code |
| Backend | **Django + Django REST Framework** | API layer; serializers double as the input-validation layer (FR-1) |
| Database | **PostgreSQL** | Persists Monitor config, check history, and (optionally) a durable Audit log — schema detailed in the Backend Schema doc |
| Cache | **Redis** | Backs the Audit cache (FR-5/6), DRF throttling (FR-7), and the Celery broker — one piece of infra, three jobs |
| Task queue / scheduler | **Celery**, with **`django-celery-beat`** for DB-driven per-monitor schedules, Redis as broker | Runs Monitor's recurring checks (shipping in code — see below) and doubles as the answer to Task B's "queueing strategy" requirement |
| Rate limiting | **DRF throttling classes**, Redis-backed | Idiomatic DRF pattern rather than hand-rolled middleware |
| CI/CD | **GitHub Actions** | Lint → test → build, per rubric requirement |
| Containerization | **Docker** | Multi-service: `nginx`, `web` (Django/Gunicorn), `worker` (Celery), `beat` (Celery Beat w/ `DatabaseScheduler`), `db` (Postgres), `redis` |
| Reverse Proxy | **Nginx** | Serves the built React static bundle at `/`, reverse-proxies `/api/*` to Gunicorn — single origin, no CORS complexity |

**Confirmed:** `django-celery-beat` (DB-driven per-monitor schedules, §10) · DRF throttling for rate limiting (§8) · self-managed VPS deployment (§14) · **Monitor ships in code**, not design-only — the PRD's "build order" guidance (Must-have hardened before Should-have) still applies, but both are now real submitted code, not one deferred to documentation. §1.1's additions (Sentry, `django-health-check`, `drf-spectacular`, `django-prometheus`, testing libs) are confirmed as-is. Only open item: naming (PRD §0.1) — proceeding with **PulseWatch** unless changed.

### 1.1 Additional Production-Grade Components

The core stack table above answers "what serves the request." These answer "how do we know it's actually working, and how do we prove it under load" — the things a demo skips and a production build doesn't. Split by whether they're built for Task A or purely inform Task B.

**Error handling & error tracking (Must-have — cheap to add, high signal for "correctness and resilience")**

| Component | Library | Role |
|---|---|---|
| Exception tracking | **Sentry** (`sentry-sdk[django]`, wired into `web`, `worker`, and `beat` containers) | Captures anything that escapes the DRF custom exception handler (§5) — the safety net behind the safety net. Every event tagged with `request_id` for correlation with structured logs |
| Retry logic | **`tenacity`** | Wraps webhook delivery (§4.8) and any Celery task step that talks to external infra (Redis/Postgres transient errors) with bounded, backed-off retries — not the target-site fetch itself, which is intentionally single-attempt-with-timeout per FR-2 |
| Aggregated health check | **`django-health-check`** | Upgrades `/api/health` (§4.3) from a static `{"status": "ok"}` to a real check of DB, Redis, and Celery worker connectivity — meaningfully different failure signal for the Task B rollback plan |

**Testing (Must-have — these are what actually earns the 25%-weighted rubric line)**

| Component | Library | Role |
|---|---|---|
| Test runner | `pytest` + `pytest-django` | Already named in §12; listed here for completeness |
| Coverage | `pytest-cov` | Produces the coverage report the CI pipeline (§13) publishes |
| Test data | `factory_boy` (or `model_bakery`) + `Faker` | Generates realistic Monitor/Audit fixtures without hand-writing every test object |
| Outbound HTTP mocking | `responses` (or `requests-mock`) | Stubs the target-site fetch so tests are deterministic and don't make real network calls |
| Time control | `freezegun` | Essential for testing cache TTL expiry (FR-6) and Monitor interval scheduling (FR-11) without real sleeps in the test suite |
| Load/burst testing | **Locust** or **k6** | Not part of the CI suite — a standalone script used to *generate real evidence* for Task B's 500-concurrent-burst and 10K/day claims, rather than asserting them without data. Run manually against a staging deploy, results captured in the Failure Mode Analysis doc |

**Scalability & observability (mostly Task B — described, not necessarily deployed for this submission)**

| Component | Library | Role | Built for Task A? |
|---|---|---|---|
| Metrics endpoint | `django-prometheus` | Exposes `/metrics` (request counts, latency histograms, cache hit ratio) | Cheap enough to add now — just middleware + one URL route |
| Metrics dashboard | Prometheus + Grafana | Scrapes `/metrics`, visualizes it | Task B description only — extra containers not justified for a take-home demo |
| Connection pooling | **PgBouncer** | Prevents Postgres connection exhaustion when Gunicorn/Celery worker counts scale up | Task B only — not needed at this task's traffic scale |
| Cache/broker HA | Redis Sentinel or Redis Cluster | Removes Redis as a single point of failure once it's load-bearing for cache + throttle + Celery broker simultaneously | Task B only |
| API documentation | **`drf-spectacular`** | Auto-generates an OpenAPI schema + Swagger UI from the DRF serializers/views — strengthens the README's "API contract" deliverable by linking live, always-accurate docs instead of hand-maintained examples | Worth adding now — low effort, direct rubric benefit |

**Config & secrets (Must-have)**

| Component | Library | Role |
|---|---|---|
| Env parsing | `django-environ` | Typed `.env` parsing into Django settings; `.env.example` committed, real `.env` gitignored |
| Secrets in CI/deploy | GitHub Actions encrypted secrets + Docker secrets/env file on the VPS | `SENTRY_DSN`, `DJANGO_SECRET_KEY`, `DATABASE_URL` never committed to the repo |

---

## 2. System Components

```
                         ┌───────────────┐
                         │     Nginx      │  (reverse proxy, TLS termination)
                         └───────┬───────┘
                    ┌────────────┼────────────┐
                    ▼                          ▼
           ┌────────────────┐         ┌─────────────────┐
           │  React build    │         │  Django + DRF     │
           │  (static, "/")  │         │  via Gunicorn     │
           └────────────────┘         │  ("/api/*")        │
                                       └─────────┬─────────┘
                          ┌─────────────┬────────┼────────┬──────────────┐
                          ▼             ▼        ▼        ▼              ▼
                   ┌───────────┐ ┌───────────┐ ┌─────┐ ┌───────────┐ ┌────────────┐
                   │ PostgreSQL│ │   Redis    │ │ ... │ │  Target    │ │  Logger     │
                   │ (Monitor, │ │ (cache +   │ │     │ │  Website   │ │ (structured │
                   │  history) │ │ throttle + │ │     │ │(3rd party) │ │  JSON)      │
                   └───────────┘ │  broker)   │ └─────┘ └───────────┘ └────────────┘
                                  └─────┬─────┘
                                        ▼
                          ┌─────────────────────────┐
                          │  Celery worker + Beat     │  (Should-have — Monitor scheduling)
                          └─────────────┬─────────────┘
                                        ▼
                                 ┌─────────────┐
                                 │  Webhook     │
                                 │  target      │
                                 └─────────────┘
```

---

## 3. Request Lifecycle — `POST /api/audits`

The path 30% of the grade ("correctness and resilience") directly exercises.

```
1. Request hits Nginx → proxied to Gunicorn/Django → request_id generated/extracted → logged
2. DRF throttle class check → 429 if breached (skip to step 8)
3. DRF serializer validates URL (format, scheme) → 400 if invalid (skip to step 8)
4. SSRF check: resolve hostname via socket.getaddrinfo, reject private/loopback/link-local/metadata IPs
   → 400 if blocked (skip to step 8)
5. Redis cache lookup on normalized URL → if HIT and within TTL, skip to step 7 with cached result
6. Concurrency gate: atomic Redis INCR-based semaphore →
   if no slot available, 503 (skip to step 8); otherwise:
   fetch target via `requests`, `timeout=FETCH_TIMEOUT_SECONDS`, `allow_redirects=False`,
   manually following + re-validating each redirect hop (§7) →
   on timeout/connection error, structured error (skip to step 8);
   on success, run checks (status/latency/SEO signals/security headers), write to Redis cache,
   release semaphore slot
7. Serialize success response (includes cache hit/miss flag)
8. Log outcome (status, latency, cache hit/miss, error code) with request_id
9. Return response
```

**Design decision — synchronous, not async/queued:** `/api/audits` responds once the check completes (bounded by `FETCH_TIMEOUT_SECONDS`), not a job-ID-plus-polling pattern. Django/Gunicorn's sync worker model makes this the natural fit; an async/ASGI + polling design is a legitimate alternative to note as considered-and-rejected in the Task B Technology Decision Record, not something to build here.

**Why a Redis semaphore, not just a Python threading lock:** Gunicorn runs multiple worker *processes*; concurrency must be capped *across* all of them, not per-process. An in-memory lock only limits one worker. Redis `INCR`/`DECR` (or a small Lua script for atomicity) gives a global, cross-process concurrency gate — this is the same reason Redis backs the cache and throttle, not three separate pieces of infra.

---

## 4. API Contract

*(Unchanged in shape from v1.0 of this doc — framework-agnostic. Reproduced here with `/api/` prefix, matching Django/DRF convention and the Nginx routing in §2.)*

### 4.1 `POST /api/audits` — run a check now *(FR-1–FR-8)*

**Request**
```json
{ "url": "https://example.com" }
```

**Response — 200 OK**
```json
{
  "success": true,
  "request_id": "req_9f3a2b1c",
  "data": {
    "audit_id": "aud_7c1e4d90",
    "url": "https://example.com/",
    "cache": "miss",
    "checked_at": "2026-07-25T10:15:00Z",
    "result": {
      "availability": { "reachable": true, "status_code": 200, "redirect_count": 0 },
      "performance": { "response_time_ms": 214, "ttfb_ms": 120, "page_size_bytes": 48213 },
      "seo_signals": { "title_present": true, "title_length": 42, "meta_description_present": true, "h1_count": 1 },
      "security_headers": { "hsts": true, "csp": false, "x_frame_options": true, "x_content_type_options": true }
    }
  },
  "timestamp": "2026-07-25T10:15:00Z"
}
```
Cached case: identical shape, `"cache": "hit"`, materially lower latency.

### 4.2 `GET /api/audits/{audit_id}` — fetch a previously completed audit
Same `data` shape. `404 AUDIT_NOT_FOUND` if unknown/expired.

### 4.3 `GET /api/health` — liveness/readiness
Backed by `django-health-check` (§1.1) — checks Postgres, Redis, and Celery worker connectivity, not just "the process is running":
```json
{
  "status": "ok",
  "uptime_seconds": 8213,
  "checks": {
    "database": "ok",
    "redis": "ok",
    "celery_worker": "ok"
  }
}
```
Returns `503` with the same shape (individual check values showing `"error"`) if any dependency is unreachable — this is what the Task B rollback plan alerts on.

### 4.4 `POST /api/monitors` — register recurring checks *(Should-have, FR-11)*
**Request**
```json
{
  "url": "https://example.com",
  "interval_seconds": 300,
  "webhook_url": "https://client.example/webhooks/pulsewatch",
  "latency_threshold_ms": 2000
}
```
**Response — 201 Created**
```json
{
  "success": true,
  "request_id": "req_1a2b3c4d",
  "data": {
    "monitor_id": "mon_5e6f7a8b",
    "url": "https://example.com/",
    "interval_seconds": 300,
    "state": "PENDING_FIRST_CHECK",
    "next_check_at": "2026-07-25T10:20:00Z"
  },
  "timestamp": "2026-07-25T10:15:00Z"
}
```
`interval_seconds` below `MONITOR_MIN_INTERVAL_SECONDS` → `400 INTERVAL_TOO_SHORT`. Same URL validation/SSRF rules as `/api/audits`.

### 4.5 `GET /api/monitors/{monitor_id}` — current state *(Should-have, FR-12)*
```json
{
  "success": true,
  "data": {
    "monitor_id": "mon_5e6f7a8b",
    "url": "https://example.com/",
    "state": "UP",
    "last_checked_at": "2026-07-25T10:20:04Z",
    "last_result": { "...": "same shape as an audit result" }
  }
}
```

### 4.6 `GET /api/monitors/{monitor_id}/history?limit=50` *(Should-have, FR-14)*
```json
{
  "success": true,
  "data": {
    "monitor_id": "mon_5e6f7a8b",
    "checks": [
      { "checked_at": "2026-07-25T10:20:04Z", "state": "UP", "response_time_ms": 210 },
      { "checked_at": "2026-07-25T10:15:04Z", "state": "UP", "response_time_ms": 198 }
    ]
  }
}
```

### 4.7 `DELETE /api/monitors/{monitor_id}` — stop monitoring *(Should-have)*
`204 No Content`.

### 4.8 Webhook payload *(Should-have, FR-13)*
```json
{
  "event": "monitor.state_changed",
  "monitor_id": "mon_5e6f7a8b",
  "url": "https://example.com/",
  "previous_state": "UP",
  "new_state": "DOWN",
  "checked_at": "2026-07-25T10:35:04Z",
  "request_id": "req_c9d8e7f6"
}
```
Single POST attempt with a short timeout for this task; retry-with-backoff is a Task B "production-grade version" note, not built here.

---

## 5. Error Code Catalog

```json
{ "success": false, "request_id": "req_...", "error": { "code": "...", "message": "..." }, "timestamp": "..." }
```

| HTTP Status | Code | When |
|---|---|---|
| 400 | `INVALID_URL` | Malformed URL, unsupported scheme — caught at DRF serializer level |
| 400 | `URL_NOT_ALLOWED` | Resolves to private/loopback/link-local/metadata IP |
| 400 | `INTERVAL_TOO_SHORT` | Monitor interval below configured floor |
| 404 | `AUDIT_NOT_FOUND` / `MONITOR_NOT_FOUND` | Unknown or expired ID |
| 429 | `RATE_LIMITED` | DRF throttle breach — includes `Retry-After` |
| 502 | `TARGET_UNREACHABLE` | DNS failure, connection refused |
| 504 | `TARGET_TIMEOUT` | Fetch exceeded `FETCH_TIMEOUT_SECONDS` |
| 503 | `SERVICE_BUSY` | Redis concurrency semaphore has no free slot |
| 500 | `INTERNAL_ERROR` | Unhandled — should be rare given the codes above |

Implemented as a DRF custom exception handler so every view (including DRF's own validation errors) is coerced into this shape — avoids Django's default HTML error pages leaking through on an unhandled case. Sentry (§1.1) sits behind this handler, not in front of it: expected errors (§5 table) are handled and logged normally without alerting noise; only genuinely *unhandled* exceptions reach Sentry, keeping signal-to-noise high.

---

## 6. SSRF Protection — Implementation Detail *(FR-1)*

1. DRF serializer rejects non-`http`/`https` schemes and malformed URLs at the validation layer
2. Resolve hostname via `socket.getaddrinfo()` **before** connecting
3. Reject if resolved IP falls in Python `ipaddress` module's private/loopback/link-local ranges (covers `127.0.0.0/8`, RFC1918 ranges, `169.254.0.0/16` including cloud metadata `169.254.169.254`, IPv6 `::1`/`fc00::/7`/`fe80::/10`)
4. Use `requests.Session()` with `allow_redirects=False`; manually follow each `Location` header, re-running steps 2–3 on every hop — a public URL can redirect to an internal one
5. Cap total redirects followed (e.g., 5) to prevent loops from holding a concurrency slot indefinitely

---

## 7. Caching Design *(FR-5, FR-6)*

- **Backend:** Redis via `django-redis` as Django's cache backend (`CACHES` setting) — no separate library needed, reuses Redis already in the stack
- **Key:** normalized URL (lowercase host, stripped default port, sorted query params, trailing slash normalized)
- **Value:** full audit result JSON + `checked_at`
- **TTL:** `CACHE_TTL_SECONDS` (default 900), passed to `cache.set(key, value, timeout=...)` — read from Django settings/env at request time
- **Cache hit signal:** every response includes `"cache": "hit" | "miss"` — provable in tests, not just claimed

---

## 8. Rate Limiting Design *(FR-7)*

- **Mechanism:** DRF `SimpleRateThrottle` subclass, keyed on `X-API-Key` header if present else client IP, backed by the same Redis cache configured in §7
- **Defaults:** `RATE_LIMIT_MAX_REQUESTS=60`/min, burst `RATE_LIMIT_BURST=100` (implemented as a token-bucket-style throttle rather than DRF's default fixed-window, for a more accurate "burst" behavior — a small custom throttle class, ~30 lines)
- **Breach response:** `429 RATE_LIMITED`, `Retry-After` header set via the exception handler in §5
- **Scope:** applied to `/api/audits` and `/api/monitors` (POST); `GET` status/history reads use a more generous or separate throttle scope since they don't trigger outbound fetches

---

## 9. Structured Logging *(FR-8)*

- Standard library `logging` + `python-json-logger` (or `structlog`) for JSON-formatted log lines
- Django middleware generates/extracts `request_id` (UUID4, or passthrough of an incoming `X-Request-Id` header) and stores it via `contextvars` so every log call in that request's lifecycle — including inside the SSRF check, cache lookup, and outbound fetch — can pull it without threading it through every function signature manually
- Celery tasks (Monitor checks) receive/generate their own `request_id` and log with the same JSON shape, so a monitor's scheduled check is traceable the same way an on-demand audit is

Minimum log fields:
```json
{
  "timestamp": "2026-07-25T10:15:00.412Z",
  "level": "info",
  "request_id": "req_9f3a2b1c",
  "method": "POST",
  "path": "/api/audits",
  "status_code": 200,
  "duration_ms": 214,
  "cache": "miss",
  "client_key": "ip:203.0.113.4",
  "error_code": null
}
```

---

## 10. Scheduler Design — Celery + `django-celery-beat` *(Shipping in code — FR-11–FR-14)*

`django-celery-beat` replaces the "one poller queries for due monitors" design with per-monitor schedules stored directly in Postgres, read by Beat's `DatabaseScheduler`. This is more precise (each monitor fires exactly on its own interval, not on the granularity of a shared poll tick) and more idiomatic for a Django-native stack.

**On `POST /api/monitors`:**
1. Create (or reuse, via `get_or_create`) an `IntervalSchedule` row matching the requested `interval_seconds`
2. Create a `PeriodicTask` row bound to task `run_monitor_check`, `args=[monitor_id]`, linked to that schedule, `enabled=True`
3. Beat's `DatabaseScheduler` picks up the new `PeriodicTask` on its next refresh (near-immediate — it polls the DB for changes, no restart required) and begins firing it on schedule

**On task execution (`run_monitor_check`, run by a Celery worker):**
- Runs the same check logic as `/api/audits` (§3 steps 4–6, minus the cache read — a scheduled check always fetches fresh)
- Writes a `MonitorCheck` row to Postgres, updates the Monitor's `state` and `last_checked_at`
- If the resulting state differs from the previously stored state, fires the webhook (§4.8)
- Acquires the same Redis concurrency semaphore as on-demand audits (§3) — Monitor and Audit share one concurrency budget, so a burst of scheduled checks can't starve incoming audit requests, and vice versa

**On `DELETE /api/monitors/{id}`:** the linked `PeriodicTask` is deleted (or `enabled=False`'d if a "paused, not deleted" state is wanted later) so Beat stops scheduling it.

**Beat command (matters for the docker-compose entry, §14):**
```
celery -A pulsewatch beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

**Testing:** `CELERY_TASK_ALWAYS_EAGER=True` runs `run_monitor_check` synchronously in tests without a live broker; `django-celery-beat`'s own scheduling logic (whether a `PeriodicTask` fires at the right time) is Celery's own well-tested code — the test suite should focus on *what happens when the task runs* (FR-12–FR-14), not re-testing Beat's internals.

**Schema note for the next doc:** `django-celery-beat` creates its own tables (`django_celery_beat_periodictask`, `django_celery_beat_intervalschedule`, etc.) via its own migrations — the Backend Schema doc should note these exist alongside the app's own `Monitor`/`MonitorCheck` tables, linked by `PeriodicTask.args` referencing `monitor_id`, rather than a formal foreign key (Celery's schema doesn't know about app-specific models).

**Why this is a stronger Task B story than a bespoke poll loop:** Celery + `django-celery-beat` + Redis + Postgres is a real, horizontally scalable, DB-driven scheduling architecture already running for the actual submission — not a placeholder. Task B's architecture document describes *scaling* this (more worker containers, `django-celery-beat`'s own leader-election concerns if ever running multiple Beat instances) rather than *replacing* it.

---

## 11. Configuration Reference

| Env Var | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | — | Django signing key (required, no default) |
| `DEBUG` | `False` | Must be `False` in production deploy |
| `ALLOWED_HOSTS` | — | Django host allowlist |
| `DATABASE_URL` | — | Postgres connection string |
| `REDIS_URL` | — | Redis connection string (cache + throttle + Celery broker) |
| `CELERY_BROKER_URL` | `${REDIS_URL}` | Usually same Redis instance, separate DB index |
| `CACHE_TTL_SECONDS` | `900` | Audit cache window (FR-6) |
| `FETCH_TIMEOUT_SECONDS` | `10` | Outbound check timeout |
| `MAX_CONCURRENT_CHECKS` | `50` | Redis semaphore cap |
| `RATE_LIMIT_MAX_REQUESTS` | `60` | Requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Throttle window |
| `RATE_LIMIT_BURST` | `100` | Burst allowance |
| `MONITOR_MIN_INTERVAL_SECONDS` | `60` | Floor on Monitor interval |
| `MONITOR_HISTORY_MAX` | `50` | Bounded history length per monitor |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `CORS_ALLOWED_ORIGINS` | — | Only needed if React is ever served from a different origin than Nginx's proxy setup |
| `SENTRY_DSN` | — | Unset in CI/local dev by convention; set only on the live deploy so error tracking doesn't fire on test runs |
| `SENTRY_ENVIRONMENT` | `production` | Tags events so staging/prod aren't conflated if a staging deploy exists |
| `PROMETHEUS_METRICS_ENABLED` | `True` | Toggles the `/metrics` endpoint from `django-prometheus` |

---

## 12. Testing Strategy → Maps to Rubric §7 (25% weight)

| Layer | Tooling | Covers |
|---|---|---|
| Unit | `pytest` + `pytest-django`, `factory_boy`/`Faker` for fixtures | URL normalization, SSRF IP-range check, cache TTL logic, throttle math, Monitor state-machine transitions |
| Integration (API-level) | DRF `APIClient`, `responses` to stub the outbound `requests` call | Full `/api/audits` lifecycle against a mocked target: slow target → `504`; target 500 → surfaced correctly; concurrent burst → `503` once the Redis semaphore is exhausted |
| Time-dependent logic | `freezegun` | Cache TTL expiry (FR-6) and Monitor `next_check_at` scheduling (FR-11) tested deterministically, no real `sleep()` calls |
| End-to-end | Real request against a real or fixture URL | Full response shape validated; `cache: miss` then `cache: hit` on immediate repeat |
| Celery (Should-have) | `CELERY_TASK_ALWAYS_EAGER=True` | Scheduler tick triggers a check; state change fires webhook (mocked receiver via `responses`) |
| CI integration tests | GitHub Actions `services:` block spinning up real Postgres + Redis containers | Confirms behavior against real infra, not just mocks, for at least the cache/throttle paths |
| Coverage | `pytest-cov` | Publishes the coverage report the CI badge/artifact links to |
| Load/burst (Task B evidence, not CI) | Locust or k6, run manually against a staging deploy | Produces real numbers backing the 500-concurrent-burst and 10K/day claims in the Failure Mode Analysis doc, rather than asserting them unverified |

**Explicitly required:** at least one test per error code in §5 — happy-path-only coverage does not satisfy FR-9 or the 25%-weighted rubric line.

---

## 13. CI Pipeline (GitHub Actions)

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: pulsewatch_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
      redis:
        image: redis:7
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: flake8 .
      - run: black --check .
      - run: pytest --cov=. --cov-report=term-missing --cov-report=xml
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/pulsewatch_test
          REDIS_URL: redis://localhost:6379/0
          CELERY_TASK_ALWAYS_EAGER: "True"
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage.xml
      - run: docker build -t pulsewatch-web .
```
Badge in README pointed at this workflow, plus the coverage artifact so the evaluator can see the number, not just take it on faith. No `continue-on-error` on lint, test, or build steps. `SENTRY_DSN` is deliberately **not** set in CI — Sentry only runs against the live deploy, so test runs don't emit noise to it.

---

## 14. Deployment (Docker Compose)

```yaml
services:
  nginx:
    build: ./nginx
    ports: ["80:80", "443:443"]
    depends_on: [web]
  web:
    build: ./backend
    command: gunicorn pulsewatch.wsgi:application --bind 0.0.0.0:8000
    env_file: .env
    depends_on: [db, redis]
  worker:
    build: ./backend
    command: celery -A pulsewatch worker -l info
    env_file: .env
    depends_on: [db, redis]
  beat:
    build: ./backend
    command: celery -A pulsewatch beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file: .env
    depends_on: [db, redis]
  db:
    image: postgres:16
    volumes: ["pgdata:/var/lib/postgresql/data"]
    env_file: .env
  redis:
    image: redis:7
volumes:
  pgdata:
```

- `nginx` serves the React production build (`npm run build` output, copied in at image build time) as static files at `/`, and reverse-proxies `/api/*` to `web:8000`
- Deploy target: a small VPS (DigitalOcean/Linode/Lightsail) running `docker-compose up -d` is the most direct match for "Docker + Nginx reverse proxy" as explicitly named components. A managed multi-service PaaS (Railway/Render/Fly.io) is a viable alternative if you'd rather not manage a VPS, but then Nginx's role is partially redundant with the platform's own routing — flag which you'd prefer.
- **Non-negotiable:** HTTPS on the live URL (Let's Encrypt via Certbot if self-managed VPS), and the footer credit rendering from the deployed React build, not just in local dev.
- `drf-spectacular`'s Swagger UI (e.g., `/api/docs`) and the `/api/health` aggregated check should both be reachable on the live deploy — the first strengthens the README's API contract deliverable, the second is what an evaluator (or a real on-call engineer, per Task B) would hit first to check the service is actually up
- `/metrics` (django-prometheus) can stay internal-only (not proxied through Nginx to the public) — it's for Task B's observability story, not something the evaluator needs public access to

---

## 15. Extension Points (Task B / PRD §4.5 — not built now)

- **Deeper checks (Phase 2):** `result` in §4.1 is already namespaced (`availability`, `performance`, `seo_signals`, `security_headers`) — adding `accessibility`/`best_practices` keys later doesn't break existing clients
- **AI recommendations (Phase 3):** slots in as a `recommendations` array alongside `result`
- **Team/RBAC (Phase 4):** `client_key` already threads through logs and throttling — swapping IP-based keys for authenticated user/org IDs (Django's built-in auth + DRF permissions) is additive, not a rewrite
- **Scale (Task B):** Celery workers and Gunicorn already scale horizontally as separate containers — Task B's architecture doc extends this to multiple worker replicas behind a load balancer, read replicas for Postgres, and Redis Cluster if a single instance becomes the bottleneck

---

## 16. Confirmed / Open Items

**Confirmed this round:** `django-celery-beat` for scheduling (§10) · DRF throttling for rate limiting (§8) · self-managed VPS deployment (§14) · Monitor ships in code (not design-only) · §1.1 additions (Sentry, `django-health-check`, `drf-spectacular`, `django-prometheus`, testing libs) all in.

**Still open before App Flow:**
1. Naming — proceeding with **PulseWatch** unless you want to change it; it's referenced throughout diagrams/URLs from here on
2. Since Monitor now ships in code alongside Audit, the **App Flow doc will diagram both flows** (on-demand Check, and Register→Scheduled Check→Alert) rather than treating Monitor as a documentation-only appendix — flag now if you'd rather keep it lighter-weight for this doc
