# Task B: Technology Decision Record (TDR)

## Overview
This document records key technology choices made during the design and implementation of PulseWatch, including considered alternatives, selection rationale, and trade-offs.

---

## 1. Web Framework: Django + Django REST Framework (DRF)

- **Choice**: Django 5.1 + Django REST Framework
- **Alternatives Considered**: FastAPI, Express.js (Node.js), Go (Gin)
- **Rationale**:
  - Django REST Framework provides out-of-the-box input validation via serializers, built-in exception handling hooks, structured response formatting, and native ORM integration.
  - Excellent ecosystem integration with `django-celery-beat`, `django-redis`, `drf-spectacular`, and `django-health-check`.
  - Rapid, robust development for qualification requirements while guaranteeing production-grade code structure.
- **Trade-off**: Slightly higher memory overhead per worker process compared to Go or FastAPI, mitigated by running Gunicorn with an optimal worker count and stateless app containers.

---

## 2. Scheduler: Celery + `django-celery-beat` (DatabaseScheduler)

- **Choice**: Celery with `django-celery-beat` storing schedules in PostgreSQL
- **Alternatives Considered**: Custom background thread poll loop, APScheduler, Cron jobs
- **Rationale**:
  - `django-celery-beat` allows per-monitor dynamic scheduling stored directly in PostgreSQL (`PeriodicTask`).
  - Schedules can be added, updated, or removed at runtime without restarting worker or scheduler processes.
  - Decouples task scheduling (`celery beat`) from task execution (`celery worker`), allowing workers to scale horizontally.
  - Shares the Redis broker infrastructure already present in the stack.
- **Trade-off**: Requires running dedicated `worker` and `beat` containers.

---

## 3. Rate Limiting: DRF Throttling + Redis Token Bucket

- **Choice**: Custom DRF `BaseThrottle` implementation using a Redis-backed Token-Bucket algorithm
- **Alternatives Considered**: In-memory fixed-window rate limiting, Nginx `limit_req_zone`
- **Rationale**:
  - Token bucket allows smooth burst handling (`RATE_LIMIT_BURST=100`) while enforcing sustained rate limits (`RATE_LIMIT_MAX_REQUESTS=60`/min).
  - Keyed dynamically on `X-Client-Key` header or client IP.
  - Cross-process consistency across Gunicorn instances via Redis.
  - Emits proper `429 RATE_LIMITED` status with `Retry-After` HTTP headers.
- **Trade-off**: Requires Redis network round-trips for token bucket state updates, minimized by using fast atomic key reads/writes.

---

## 4. Concurrency Gate: Redis Sorted Set Semaphore

- **Choice**: Redis Sorted Set (`concurrency:active_checks`) with score = timestamp
- **Alternatives Considered**: Simple `INCR`/`DECR` Redis counter, Python `threading.Lock`
- **Rationale**:
  - A simple counter leaks slots permanently if a worker process crashes mid-fetch between `INCR` and `DECR`.
  - Sorted set member score stores the acquisition timestamp. Before evaluating capacity, stale entries (`now - 2 * FETCH_TIMEOUT`) are pruned via `ZREMRANGEBYSCORE`.
  - Self-healing: slot leaks caused by worker crashes or OOM kills are automatically reclaimed within 20 seconds.
- **Trade-off**: Slightly more complex Redis commands (`ZREMRANGEBYSCORE`, `ZCARD`, `ZADD`, `ZREM`) compared to simple counter, but guarantees resilience under failure.

---

## 5. Storage Architecture: PostgreSQL + Redis Dual-Storage Split

- **Choice**: PostgreSQL for durable state (Audits, Monitors, History); Redis for ephemeral fast-path (Cache, Concurrency, Rate limits, Celery broker)
- **Alternatives Considered**: PostgreSQL-only (using unlogged tables for caching), Redis-only
- **Rationale**:
  - Clear separation of concerns: Redis handles high-frequency volatile ops; PostgreSQL handles relational queries, indexing, and durable history.
  - Audit lookups hit Redis first (`cache:audit:{normalized_url}`). Cache hits skip outbound fetching entirely.
  - `GET /api/audits/{id}` falls back to PostgreSQL if cache expires.
- **Trade-off**: Two storage dependencies in `docker-compose`, both standard production components.

---

## 6. Frontend Stack: React + Vanilla CSS (Vite)

- **Choice**: React 18 SPA with Vite and Vanilla CSS
- **Alternatives Considered**: Next.js, TailwindCSS, Bootstrap
- **Rationale**:
  - Clean SPA design mapping directly to the 5 user flows in the UI/UX Brief.
  - Vanilla CSS CSS variables provide maximum control over state badge colors, dark mode design tokens, animations, and responsive breakpoints without build-tool complexity or framework overhead.
  - Fast asset generation via Vite multi-stage Docker build outputting static assets directly to Nginx.
- **Trade-off**: Manual CSS utility management, compensated by maintaining a clean CSS variable system.
