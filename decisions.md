# PulseWatch — Technology Decision Record (Decisions Log)

## Decisions Summary

| Decision | Selection | Alternatives Considered | Primary Rationale |
|---|---|---|---|
| Web Framework | Django + DRF | FastAPI, Express.js | Native serializer validation, ORM, django-celery-beat integration |
| Frontend | React + Vite + Vanilla CSS | Next.js, TailwindCSS | Fast static build, explicit CSS variable design system, single page layout |
| Database | PostgreSQL 16 | SQLite, MySQL | JSONB support, transactional integrity, production scale |
| Cache & Broker | Redis 7 | Memcached, RabbitMQ | Multi-role container (cache, throttle, concurrency semaphore, Celery broker) |
| Scheduling | Celery + django-celery-beat | APScheduler, Cron | DB-driven dynamic scheduling, horizontal worker scalability |
| Rate Limiting | DRF Throttling + Redis Token Bucket | Nginx rate limit, custom middleware | Dynamic client keying, burst allowance, Retry-After headers |
| Concurrency Control | Redis Sorted Set Semaphore | Redis INCR counter, Threading Lock | Self-healing against worker crash lock leaks |
| Monitor Ownership | Anonymous X-Client-Key | Full Auth (JWT/Sessions) | Keeps task scope tight while providing per-browser monitor isolation |
| History Retention | Prune-on-write (max 50) | Unbounded table + periodic cleanup | Guarantees O(1) space footprint per monitor |
