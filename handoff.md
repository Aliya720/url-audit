# PulseWatch — Model Handoff Document

## 1. Project Overview
PulseWatch is a production-ready URL health audit & monitoring service built with Django REST Framework, React (Vite), Redis, PostgreSQL, Celery, and Nginx.

## 2. Status of Deliverables

### Task A (Production Build) — 100% Complete
- [x] On-demand URL health audit (`POST /api/audits`, `GET /api/audits/{id}`)
- [x] URL validation & SSRF protection (DNS pre-check, private IP rejection, per-hop revalidation)
- [x] Redis result caching with configurable TTL (`cache: "hit" | "miss"`)
- [x] Per-client token-bucket rate limiting (`429` + `Retry-After`)
- [x] Redis Sorted Set concurrency semaphore (self-healing)
- [x] Structured JSON logging with `X-Request-Id` correlation
- [x] Monitor registration (`POST /api/monitors`) & dynamic scheduling (`django-celery-beat`)
- [x] Background check execution, state machine (`UP`/`DOWN`/`DEGRADED`), and webhook alert POSTs
- [x] Bounded history retrievable per monitor (`GET /api/monitors/{id}/history`, max 50 rows)
- [x] React single-page UI (5 screens: Home, Result, Register, My Monitors, Detail)
- [x] Footer credit line ("Built for Digital Heroes Training Task" linked to `https://digitalheroesco.com`)
- [x] 74/74 passing automated tests in pytest suite
- [x] GitHub Actions CI workflow (`.github/workflows/ci.yml`)
- [x] Multi-container Docker Compose configuration (`docker-compose.yml`, `docker-compose.prod.yml`)

### Task B (Scale Architecture & Design) — 100% Complete
- [x] `docs/task-b/01-ArchitectureDocument.md`
- [x] `docs/task-b/02-TechnologyDecisionRecord.md`
- [x] `docs/task-b/03-FailureModeAnalysis.md`
- [x] `docs/task-b/04-ObservabilityAndRollback.md`

## 3. Folder Structure
```
url_audit/
├── backend/
│   ├── checks/
│   │   ├── models.py         # Audit, Monitor, MonitorCheck
│   │   ├── views.py          # API endpoints
│   │   ├── engine.py         # Check engine (availability, perf, SEO, security headers)
│   │   ├── tasks.py          # Celery background tasks & webhooks
│   │   ├── exceptions.py     # Custom exception handler & error catalog
│   │   ├── throttling.py     # Token-bucket rate throttle
│   │   ├── middleware.py     # Request ID middleware
│   │   ├── utils/            # url_validation.py, cache.py, concurrency.py
│   │   └── tests/            # 74 automated unit & integration tests
│   ├── pulsewatch/           # settings.py, celery.py, urls.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/            # Home, CheckResult, RegisterMonitor, MyMonitors, MonitorDetail
│   │   ├── components/       # Header, Footer, ErrorBanner
│   │   ├── api/              # client.js, errors.js
│   │   ├── App.jsx
│   │   └── index.css
│   ├── Dockerfile
│   └── package.json
├── nginx/
│   ├── nginx.conf
│   └── Dockerfile
├── docs/
│   └── task-b/               # Task B architecture docs
├── .github/workflows/ci.yml
├── docker-compose.yml
├── docker-compose.prod.yml
├── progress.md
├── architecture.md
├── decisions.md
├── handoff.md
└── README.md
```

## 4. Next Immediate Tasks (Deployment Steps for User)
1. Push repo to GitHub (`git init`, `git add .`, `git commit`, `git push`).
2. Run `docker-compose up --build` to start local full-stack environment.
3. Deploy to production VPS (DigitalOcean / AWS / Linode) using `docker-compose.prod.yml`.
4. Point DNS to VPS and run Certbot for HTTPS termination.
