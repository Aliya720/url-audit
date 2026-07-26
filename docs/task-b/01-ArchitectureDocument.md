# Task B: Architecture Document

## System Architecture Overview — PulseWatch

PulseWatch is designed as a highly resilient, scalable, distributed service capable of handling 10,000 checks/day with bursts of up to 500 concurrent checks.

```
                         ┌───────────────┐
                         │     Nginx      │  (Reverse Proxy / Static SPA)
                         └───────┬───────┘
                     ┌───────────┴───────────┐
                     ▼                       ▼
           ┌────────────────┐       ┌─────────────────┐
           │   React SPA    │       │  Django + DRF   │
           │ (Static Bundle)│       │  (via Gunicorn) │
           └────────────────┘       └────────┬────────┘
                                             │
                       ┌─────────────────────┼─────────────────────┐
                       ▼                     ▼                     ▼
                ┌────────────┐        ┌─────────────┐       ┌──────────────┐
                │ PostgreSQL │        │    Redis    │       │ Logger/Logs  │
                │ (Audits,   │        │ (Cache,     │       │ (Structured  │
                │ Monitors,  │        │ Semaphore,  │       │  JSON)       │
                │ History)   │        │ Throttle,   │       └──────────────┘
                └────────────┘        │ Celery)     │
                                      └──────┬──────┘
                                             │
                                             ▼
                               ┌─────────────────────────┐
                               │  Celery Worker + Beat   │  (Scheduled Checks)
                               └─────────────┬───────────┘
                                             ▼
                                      ┌─────────────┐
                                      │   Webhook   │
                                      │  Endpoints  │
                                      └─────────────┘
```

---

## 1. System Components

### 1.1 Web Layer & Ingress (Nginx + React SPA)
- **Nginx**: Serves the static React build directly at `/` and reverse-proxies `/api/*` requests to Gunicorn application servers.
- **TLS Termination**: Handles SSL/TLS encryption.
- **Static Assets**: Offloads static asset delivery from Python workers.

### 1.2 Application API Layer (Django REST Framework)
- **Stateless API Services**: Runs under Gunicorn worker processes.
- **Request Lifecycle**:
  1. Assigns/extracts `X-Request-Id` for request correlation.
  2. Applies Redis token-bucket rate limiting per client (`X-Client-Key` or IP).
  3. Validates incoming URLs and enforces strict SSRF protections (pre-connect DNS resolution against RFC1918 / cloud metadata / loopback ranges).
  4. Queries Redis cache for recent audit results.
  5. Acquires a Redis Sorted-Set concurrency slot before making outbound HTTP calls.
  6. Executes multi-dimensional audit checks (Availability, Performance, SEO Signals, Security Headers).
  7. Persists audit records to PostgreSQL and updates the Redis cache.

### 1.3 Shared Concurrency & Ephemeral Storage (Redis)
Redis serves three distinct operational roles without introducing additional infrastructure complexity:
1. **Audit Cache**: Short-term TTL-bound audit result storage (`cache:audit:{normalized_url}`).
2. **Rate Limiter Throttling**: Token-bucket throttle counters (`throttle:{client_key}`).
3. **Concurrency Semaphore**: Cross-process distributed lock using a Redis Sorted Set (`concurrency:active_checks`) with score-based auto-pruning to self-heal against crashed worker processes.
4. **Celery Task Broker**: Message broker for Celery background tasks.

### 1.4 Background Worker & Scheduling Layer (Celery + Celery Beat)
- **`django-celery-beat`**: Database-backed periodic task scheduler storing per-monitor schedules in PostgreSQL (`PeriodicTask`, `IntervalSchedule`).
- **Celery Workers**: Executes `run_monitor_check` tasks asynchronously. Reuses the core check engine, bypasses cache to force fresh checks, enforces the shared concurrency semaphore, updates monitor state machines, and dispatches webhook alert POSTs on state transitions.

### 1.5 Durable Storage Layer (PostgreSQL)
- **Audits (`audits`)**: Point-in-time historical record of every on-demand check.
- **Monitors (`monitors`)**: Monitor configurations, state (`UP`, `DOWN`, `DEGRADED`, `PENDING_FIRST_CHECK`), and last/next check timestamps.
- **Monitor Checks (`monitor_checks`)**: Bounded historical timeline of monitor checks with prune-on-write enforcing a flat storage footprint (`MONITOR_HISTORY_MAX = 50`).

---

## 2. Horizontal Scaling Strategy (10,000 checks/day, 500-concurrent burst)

```
                            ┌──────────────┐
                            │ Load Balancer│
                            └──────┬───────┘
                      ┌────────────┴────────────┐
                      ▼                         ▼
              ┌───────────────┐         ┌───────────────┐
              │ App Server 1  │         │ App Server 2  │
              │ (Gunicorn x4) │         │ (Gunicorn x4) │
              └───────┬───────┘         └───────┬───────┘
                      │                         │
        ┌─────────────┴───────────┬─────────────┴───────────┐
        ▼                         ▼                         ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│ PgBouncer     │         │ Redis Sentinel│         │ Celery Worker │
│ Pool          │         │ Cluster       │         │ Cluster (xN)  │
└───────┬───────┘         └───────────────┘         └───────────────┘
        ▼
┌───────────────┐
│ PostgreSQL    │
│ Primary/Repl  │
└───────────────┘
```

1. **API Tier**: Gunicorn processes can be scaled across multiple container instances or nodes behind an AWS ALB or Nginx load balancer.
2. **Database Tier**: `PgBouncer` connection pooler handles high connection bursts from web and worker nodes. Read-replicas can handle `GET /api/monitors` and history reads.
3. **Worker Tier**: Celery workers scale horizontally by adding worker containers. Since concurrency is bounded by the shared Redis Sorted Set semaphore, scaling workers increases execution throughput without swamping external target sites.
