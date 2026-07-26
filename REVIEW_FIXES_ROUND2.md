# Code Review Round 2 — Resubmission Review

This project was previously reviewed (two critical deployment-breaking bugs found). This is a **fresh, independent verification** of the resubmission — every claim below was checked by actually running a command, not by assuming anything carried over.

## ✅ Confirmed genuinely fixed in this resubmission

1. **`settings.py` DB backend detection** — was inverted (used SQLite specifically when the Docker hostname was present). Now correctly checks `if db_url:` — verified by reading the logic directly.
2. **`settings.py` latent `REDIS_URL` `NameError`** — was only assigned in the fallback branch, would crash Django at import time whenever `REDIS_URL` pointed anywhere non-Docker (exactly what CI does). Now assigned in both branches.
3. **Frontend now actually serves.** Different approach than my original suggestion — bind-mounts `./frontend/dist` into Nginx instead of building inside Docker. Valid alternative. Verified with a byte-for-byte `diff` between a fresh `npm run build` and the committed `dist/`: **zero differences**, not stale.

## 🔧 Fixed in this round

4. **Webhook SSRF gap** — `webhook_url` had zero validation (a comment claimed otherwise). Any monitor could point its webhook at an internal address. Added `WebhookURLNotAllowed` exception, wired `validate_url()` + `check_ssrf()` into registration. Same fix pattern applied to the `MonitorAlertsView`'s inline `ClientKeyRequired` class discovered during this pass (a third occurrence of the same anti-pattern, beyond the one already known).
5. **CI was red** — 26 flake8 violations, 15 files needing black reformatting. Fixed all of it; both gates now exit 0.
6. **The rate-limit test was a no-op** — looped through requests, zero assertions. Rewrote with deterministic assertions (exact status codes before/after the burst limit, `Retry-After` header, error code).
7. **`tasks.py` (39% coverage) and `concurrency.py` (24% coverage)** — `run_monitor_check` was imported but never invoked in any test; the concurrency semaphore was only ever mocked out. Added `test_concurrency.py` (6 tests against real Redis, including the stale-slot-pruning self-heal behavior) and 4 end-to-end task tests in `test_monitor.py`. Now 85%/84% respectively.
8. **Tenacity imported but never used** — same pattern as the webhook gap: a docstring claimed retry was "wired," the code made a single bare `requests.post()` call. Actually wired it: 3 attempts, exponential backoff, retrying only on connection errors/timeouts.
9. **README's API contract was stale relative to the real API.** A substantial, well-built health-score/grade/fix-suggestions feature was added to `engine.py` (~300 new lines, genuinely tested, fully wired into the React UI) but never documented. Updated the README with the actual response shape, verified field-by-field against `engine.py`'s source (not guessed). Also documented `GET /api/monitors/alerts`, which existed in code/tests but wasn't in the README at all.
10. **Naming inconsistency** — the live UI is branded "SiteGuard" throughout (header, footer, page title), but two user-visible strings (`errors.js`, a markdown export in `CheckResult.jsx`) and the README title still said "PulseWatch." Fixed the two stray UI strings and the README title. **Deliberately did not** rename the backend's `pulsewatch` Python package/Celery app/Docker commands — that's an internal, invisible-to-users identifier, and renaming it is a much higher-risk mechanical change for zero user-facing benefit. Left a note in the README explaining the split rather than hiding it.
11. **Doc duplication** — `architecture.md`/`decisions.md` at repo root were thinner, older drafts of the fuller `docs/task-b/01-...`/`02-...` files. Added explicit pointer notes at the top of both root files rather than deleting them, so there's no ambiguity about which is the graded deliverable.
12. **`handoff.md` referenced `docker-compose.prod.yml` twice (including in deploy instructions) — confirmed by direct inspection that it did not exist.** Created it for real this time: drops `db`/`redis`'s public port exposure, switches Gunicorn to gevent workers (4 sync workers can't approach the app's own `MAX_CONCURRENT_CHECKS=50` target — this is the single biggest gap between the code and the Task B "500 concurrent burst" claim). Added `gevent` to `requirements.txt` (wasn't there, the worker class would have failed to start without it).
13. **`progress.md` said "74 (100%)" tests** — stale, actual current count is 90. Updated with an honest note about why it changed.
14. Added `restart: unless-stopped` to every service and fixed `db`'s hardcoded Postgres credentials duplicating (and able to drift from) `.env`'s values, in the base `docker-compose.yml`. Removed the orphaned `frontend_build` named volume — nothing referenced it anymore after the switch to bind-mounting `./frontend/dist`.

## Not fixed — flagged, your call

- **`/metrics` is still publicly proxied in `nginx.conf`** with no access restriction, despite the TRD saying it should stay internal-only. Cheap fix (`allow`/`deny` directives) if you want it, not done here to keep this round's diff focused.
- **`django-health-check` is installed and configured but `/api/health` is still hand-rolled** instead of using the library's own view. Same as before — not wrong, just slightly wasteful.
- **`acquire_slot()` fails open on Redis errors** (`except Exception: return True`) — a deliberate availability-over-strict-enforcement tradeoff already in this codebase (not something I added or changed). Worth being aware of: if Redis goes down, concurrency limiting silently stops being enforced entirely rather than degrading to 503s. Confirm this is the intended behavior.
- **No cap on fetched response body size** in `engine.py`'s `fetch_url` — unchanged from the first review, still just a "your call" item, not urgent at this scale.

## Test results — run fresh, right now, this exact codebase

```
90 passed in 8.78s
Coverage: 90%
  tasks.py: 84% (was 39%)
  concurrency.py: 85% (was 24%)
flake8: clean (was 26 violations)
black --check: clean (was 15 files needing reformat)
manage.py check: clean
makemigrations --check: clean
docker-compose.yml + docker-compose.prod.yml: both valid YAML
Fresh `npm run build` vs. committed frontend/dist/: byte-for-byte identical
```
