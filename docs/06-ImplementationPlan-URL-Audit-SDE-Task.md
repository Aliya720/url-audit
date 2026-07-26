# Implementation Plan

## PulseWatch
**Digital Heroes SDE Qualification Task — Task A (Production Build) + Task B (Scale Design)**

| | |
|---|---|
| **Doc** | 6 of 6 — Implementation Plan |
| **Version** | 1.0 |
| **Status** | Draft for Review |
| **Traces to** | PRD v3.0, TRD v2.1, App Flow v1.1, UI/UX Brief v1.0, Backend Schema v1.1 |

---

## 0. Purpose

Everything up to this doc answered "what are we building and how does it work." This one answers **"in what order do I actually write it, and how do I know each piece is done before moving to the next."** It also folds in Task B — the architecture doc, tech decision record, failure-mode analysis, and observability/rollback plan aren't a separate afterthought here; they're produced alongside the code they describe, because writing them *after* the fact tends to produce documents that describe an idealized system instead of the real one.

**Governing rule, carried from PRD §0.2:** Must-have Check is fully hardened and tested before any Should-have Monitor code is written. Nothing in this plan reorders that.

---

## 1. Repo Structure

```
pulsewatch/
├── backend/
│   ├── pulsewatch/          # Django project (settings, urls, celery.py)
│   ├── checks/               # app: Audit, Monitor, MonitorCheck models, views, serializers, tasks
│   ├── requirements.txt
│   ├── Dockerfile
│   └── manage.py
├── frontend/
│   ├── src/                  # React app — pages/, components/, api/
│   ├── package.json
│   └── Dockerfile             # multi-stage: build → copy into nginx image
├── nginx/
│   ├── Dockerfile
│   └── nginx.conf
├── docs/                      # this doc set — PRD, TRD, App Flow, UI/UX Brief, Backend Schema, Implementation Plan
│   └── task-b/                # Architecture doc, Tech Decision Record, Failure Mode Analysis, Observability & Rollback
├── .github/workflows/ci.yml
├── docker-compose.yml
├── docker-compose.prod.yml    # VPS overrides (no dev volume mounts, real env)
└── README.md                  # API contract + footer requirement + live URL
```

---

## 2. Phase 0 — Scaffolding (target: ~1 day)

**Goal:** every service starts, talks to every other service, CI runs and passes on an empty test suite. Nothing functional yet — this phase exists so Phase 1 is pure feature work, not fighting infrastructure.

- [ ] `django-admin startproject pulsewatch`, add DRF, `django-environ`, `django-redis`
- [ ] `checks/` app scaffolded, empty models
- [ ] Celery configured (`pulsewatch/celery.py`), `django_celery_beat` added to `INSTALLED_APPS`, migrated
- [ ] `docker-compose.yml` with all six services (§ TRD 14) — confirm every container starts and `web` can reach `db` and `redis`
- [ ] React app scaffolded (`create-react-app` or Vite), one placeholder page
- [ ] Nginx config: static React build at `/`, proxy `/api/*` to `web:8000`
- [ ] `.github/workflows/ci.yml` — even with zero real tests, confirm lint + a trivial passing test + Docker build all go green
- [ ] `.env.example` committed with every var from TRD §11

**Definition of done for this phase:** `docker-compose up` brings up a working (empty) stack locally, and a push to GitHub shows a green CI check.

---

## 3. Phase 1 — Must-Have: Check/Audit (target: ~3 days)

*This phase alone should be gradeable on its own if nothing else ships — treat it that way.*

### 3.1 Backend, in dependency order
1. `Audit` model + migration (Backend Schema §2)
2. URL normalization + validation function (unit-testable in isolation, no Django/DRF dependency ideally)
3. SSRF check module (DNS resolve + IP range check, TRD §6) — **write tests for this before wiring it into a view**, it's the single highest-stakes piece of logic in the whole build
4. Redis cache wrapper (get/set on `cache:audit:{normalized_url}`, TRD §7)
5. Redis concurrency semaphore (sorted-set design, Backend Schema §5.1)
6. Outbound fetch function: `requests` session, manual redirect handling + re-validation per hop, timeout
7. Check engine: runs the fetch, computes `availability`/`performance`/`seo_signals`/`security_headers`
8. DRF serializer + view for `POST /api/audits`, wired to steps 2–7 in the order from App Flow Flow 1
9. `GET /api/audits/{id}` view
10. Custom DRF exception handler + error catalog (TRD §5)
11. DRF throttle class (TRD §8)
12. Structured logging middleware (request ID generation/propagation, TRD §9)
13. `django-health-check`, `drf-spectacular`, Sentry wiring, `django-prometheus` `/metrics` — cheap, do them now while the shape of the app is still simple, not bolted on later

### 3.2 Frontend
1. Home/Check screen (UI/UX Brief §2) — form, submit, loading state
2. Check Result screen (§3) — four result cards, cache badge
3. Error state handling wired to the copy mapping (§8 of the brief)
4. Footer component with the required credit line — **build this in Phase 0/1, not last.** It's small, easy to forget under later time pressure, and disqualifying if missing.

### 3.3 Tests (write alongside, not after)
Per TRD §12: unit tests for validation/SSRF/cache/semaphore logic, integration tests against a mocked target for every error code in §5, at least one true end-to-end test, `freezegun`-based TTL expiry test. **At least one test per error code — this is checked explicitly, not just "good coverage."**

### 3.4 Phase 1 Definition of Done
- [ ] Every FR-1 through FR-10 has a passing test
- [ ] Manually submitting a real URL through the local React app returns a correct result
- [ ] Submitting the same URL twice within the TTL shows `cache: hit` the second time, visibly in the UI
- [ ] Submitting 60+ rapid requests triggers a `429`
- [ ] CI is green, coverage report generated
- [ ] **Stop and confirm this phase is solid before starting Phase 2 — this is the PRD §0.2 gate, not a suggestion**

---

## 4. Phase 2 — Should-Have: Monitor (target: ~2 days)

Only begins once Phase 1's Definition of Done is fully checked.

### 4.1 Backend, in dependency order
1. `Monitor`, `MonitorCheck` models + migrations (Backend Schema §3–4), including the `unique(owner_key, normalized_url)` constraint and prune-on-write logic
2. `X-Client-Key` middleware/dependency (App Flow §0.1) — reused by both the throttle key and Monitor ownership
3. `run_monitor_check` Celery task — reuses the check engine from Phase 1 step 7 (this reuse is itself a code-quality signal, don't fork the logic)
4. `POST /api/monitors` view: creates `Monitor`, `IntervalSchedule`, `PeriodicTask` (TRD §10)
5. `GET /api/monitors` (list, owner-scoped), `GET /api/monitors/{id}`, `GET /api/monitors/{id}/history`
6. `DELETE /api/monitors/{id}` — owner check, `404` on mismatch (not `403`), deletes `PeriodicTask` + cascades to history
7. Webhook delivery on state transition, wrapped with `tenacity` retry (§1.1 of TRD)

### 4.2 Frontend
1. Register a Monitor screen (UI/UX Brief §4)
2. My Monitors list screen (§5), including the empty state with the "tied to this browser" disclosure
3. Monitor Detail + History screen (§6), delete confirmation

### 4.3 Tests
`CELERY_TASK_ALWAYS_EAGER=True` for synchronous task testing; state-machine transition tests (App Flow §5's diagram, every arrow tested); webhook delivery tested against a mocked receiver; prune-on-write tested (insert past `MONITOR_HISTORY_MAX`, confirm row count stays bounded).

### 4.4 Phase 2 Definition of Done
- [ ] FR-11 through FR-14 have passing tests
- [ ] A registered monitor actually ticks on schedule locally (verify via logs, not just "the code looks right")
- [ ] Simulating a target going down flips state and fires the mocked webhook exactly once
- [ ] Deleting a monitor removes its `PeriodicTask` (confirm no orphaned scheduled task keeps firing)

---

## 5. Phase 3 — Task B Documents (runs in parallel with Phases 1–2, finalized after)

These don't block code, but they shouldn't be written cold at the end either — capture real decisions and real numbers as they happen.

| Document | Start When | Content Source |
|---|---|---|
| **Architecture Document + Diagram** | After Phase 0 (system shape is stable) | TRD §2 system diagram, Backend Schema §1 ERD — refine, don't redraw from scratch |
| **Technology Decision Record** | After Phase 0 | Every "confirmed" stack choice across this doc set (React/Django/Postgres/Redis/Celery/Docker/Nginx, `django-celery-beat` vs. plain polling, DRF throttling vs. `django-ratelimit`, VPS vs. PaaS) — for each, state the rejected alternative and why, one paragraph apiece |
| **Failure Mode Analysis** | During Phase 2, after real load/edge-case testing | Top 3 candidates: (1) worker crash mid-check — mitigated by the sorted-set concurrency gate, Backend Schema §5.1; (2) unbounded `monitor_checks` growth — mitigated by prune-on-write, §4.1; (3) target site blocking the crawler / SSRF via redirect — mitigated by TRD §6/§3's per-hop revalidation. Pick the three most likely to actually bite, not the three easiest to write about |
| **Observability & Rollback Plan** | After Phase 3 (Sentry/health-check/Prometheus wired) | What's monitored: `/api/health` (aggregated dependency check), Sentry error rate, `/metrics` latency/cache-hit-ratio. What alerts: health check failing, error rate spike. Rollback: tagged Docker images, `docker-compose pull && up -d` to the previous tag; document the actual command sequence, not just "we'd roll back" |

**Load testing (Locust/k6, TRD §1.1) belongs here too** — run it against the deployed staging/prod instance once Phase 4 is live, feed real numbers into the Failure Mode Analysis rather than hypothetical ones.

---

## 6. Phase 4 — Deployment (target: ~0.5–1 day)

- [ ] Provision VPS (DigitalOcean/Linode/Lightsail)
- [ ] Install Docker + Docker Compose on the VPS
- [ ] DNS pointed at the VPS
- [ ] `docker-compose.prod.yml` applied — real `.env` (secrets never committed), HTTPS via Certbot
- [ ] Smoke test: submit a real Check, register a real Monitor, confirm it ticks, confirm the webhook fires against a real endpoint (e.g., a temporary [webhook.site](https://webhook.site) URL for manual verification)
- [ ] **Confirm the footer credit renders on the live URL**, links correctly to `digitalheroesco.com`
- [ ] Confirm `/api/docs` (Swagger) and `/api/health` are reachable live

---

## 7. Final Submission Checklist

Directly from PRD §9, re-verified here as the last gate before submitting:

**Task A**
- [ ] Public GitHub repo, tests + CI config included, CI green on the latest commit
- [ ] Live deployed link, smoke-tested
- [ ] README with full API contract (link to `/api/docs` Swagger, plus a written summary)
- [ ] Footer credit line + link, visible on the live page

**Task B**
- [ ] Architecture document + diagram
- [ ] Technology Decision Record
- [ ] Failure Mode Analysis (top 3, with mitigations — grounded in what was actually built)
- [ ] Observability & Rollback Plan

**Submission**
- [ ] Live URL included in the submission
- [ ] Posted per the brief's Instagram submission instructions (`@realshreyanshsingh`)

---

## 8. Time Estimate Summary

| Phase | Estimate | Cumulative |
|---|---|---|
| 0 — Scaffolding | ~1 day | Day 1 |
| 1 — Must-Have Check | ~3 days | Day 4 |
| 2 — Should-Have Monitor | ~2 days | Day 6 |
| 3 — Task B docs | Parallel, finalized by | Day 7 |
| 4 — Deployment | ~0.5–1 day | Day 7–8 |

**If time runs short, the cut point is clean:** ship Phase 1 fully hardened, skip Phase 2 entirely, and note in the README/Task B docs that Monitor was designed (App Flow, Backend Schema both cover it in full) but not built, in favor of a fully solid Must-have. That's a defensible, explainable tradeoff — a half-built Monitor with weak tests is not.

---

## 9. Closing Note

This is the last of the six planning docs. Everything from here is execution against Phases 0–4 above. If a decision surfaces during build that isn't covered by PRD/TRD/App Flow/UI-UX Brief/Backend Schema, the fallback principle is the one repeated throughout this set: **default toward what's explicitly graded (PRD §7) over what's merely nice — and when in doubt, it's cheaper to ask than to guess and rebuild.**
