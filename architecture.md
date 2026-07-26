# PulseWatch — Architecture Document

## High-Level Architecture

PulseWatch is structured as a multi-container microservices application:

1. **Nginx (Reverse Proxy & Ingress)**
   - Serves React static SPA at `/`
   - Proxies `/api/*` requests to Gunicorn
   - Enforces TLS termination & static asset caching

2. **React SPA (Frontend)**
   - 5 screens: Home/Check, Check Result, Register Monitor, My Monitors, Monitor Detail
   - Client-side token generation (`X-Client-Key` stored in localStorage for anonymous monitor ownership)

3. **Django REST Framework (Backend API)**
   - Stateless web workers running under Gunicorn
   - Serializers validate inputs and format structured JSON responses
   - Custom exception handler coerces all errors into uniform schema
   - Redis token-bucket rate limiter (`RATE_LIMIT_BURST=100`, `RATE_LIMIT_MAX_REQUESTS=60`/min)
   - Concurrency gate backed by Redis Sorted Set (`concurrency:active_checks`)

4. **Check Engine**
   - Shared execution core used by both on-demand Audit and scheduled Monitor
   - Measures availability (status code, reachability, redirects), performance (response time, TTFB, page size), SEO signals (title, meta desc, H1s), and security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options)

5. **Celery Worker & Celery Beat (Scheduler)**
   - `django-celery-beat` manages DB-driven periodic task schedules (`PeriodicTask`)
   - Celery workers execute `run_monitor_check` on schedule, evaluate state transitions, update PostgreSQL records, prune historical rows, and fire webhooks on state changes

6. **PostgreSQL & Redis (Data Layer)**
   - PostgreSQL: Stores durable `audits`, `monitors`, `monitor_checks`, and `django_celery_beat_*` tables
   - Redis: Serves as Audit result cache (`cache:audit:{normalized_url}`), throttle counter store, concurrency semaphore, and Celery broker
