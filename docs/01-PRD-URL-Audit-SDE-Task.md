# Product Requirements Document (PRD)

## PulseWatch *(working title — pending confirmation, see §0.1)*
**Check it once, or watch it forever — a URL health audit & monitoring service**
**Digital Heroes SDE Qualification Task — Task A (Production Build) + Task B (Scale Design)**

| | |
|---|---|
| **Doc** | 1 of 6 — PRD |
| **Version** | 3.0 — merges enterprise vision as a labeled future roadmap; Task A/B locked as top priority |
| **Status** | Draft for Review |
| **Next docs** | TRD → App Flow → UI/UX Brief → Backend Schema → Implementation Plan |

---

## 0. Context

This is a **graded qualification task** — every requirement in the graded sections traces back to the rubric (§7). This version does two things at once:

1. Keeps Task A (build) and Task B (architecture docs) as the **only thing that gets built for submission**, with a hard priority order (§0.2).
2. Folds in the fuller product vision — inspired both by the original enterprise "audit everything" concept and by pagepulse.co's continuous-monitoring model — as a **clearly separated, unbuilt roadmap** (§4.5). This exists so the doc shows product thinking beyond the minimum bar, without putting any of that scope at risk of being mistaken for something you're expected to ship this week.

### 0.1 Naming — still open
Not using `PagePulse` (real, trademarked, live product — see prior review). Working title: **PulseWatch**. Alternates: `SiteSentinel`, `PingPulse`, `Vigil`, `Watchtower`. Confirm before TRD lock — it touches the repo name, deploy URL, and footer copy.

### 0.2 Priority Stack *(read this before reading anything else in the doc)*

| Priority | What | Status |
|---|---|---|
| **1 — Must build, fully graded** | Task A Must-have: on-demand `Check`/`Audit` with validation, timeouts, concurrency limits, caching, rate limiting, tests, CI, footer credit | §4.1, §5.1 |
| **2 — Build only after #1 is solid** | Task A Should-have: `Monitor` — scheduled recurring checks + webhook alert on state change | §4.2, §5.2 |
| **3 — Required, but a document not code** | Task B: architecture doc, tech decision record, failure-mode analysis, observability/rollback plan | Separate docs, this PRD feeds them |
| **4 — Vision only, NOT part of this submission** | Deep audit modules (SEO/Accessibility/Best Practices), AI recommendations, dashboards, teams/RBAC, PDF reports, enterprise SSO, etc. | §4.5 — for context only |

---

## 1. Assumptions to Confirm

1. **Check scope (graded core):** every check — on-demand or scheduled — runs the same lightweight engine: HTTP status, latency/TTFB, and a light content signal set (title/meta presence, key security headers present/absent). Not a headless-browser Core Web Vitals engine.
2. **Monitor is a stretch goal**, gradeable-optional per §0.2 priority 2.
3. **Monitor's alert channel, if built, is a webhook callback** — mockable in tests, no third-party credentials needed.
4. **§4.5 (Future Roadmap) is not built, not tested, not part of Task A/B deliverables.** It exists purely so the PRD reads as a real product plan, and so the TRD/architecture doc can note "designed to extend cleanly to X" without X existing in code.

Flag any of these before the TRD locks the API contract around them.

---

## 2. Product Concept

PulseWatch gives a user two ways to know their site is healthy:

- **Check** — "is my site okay *right now*?" One-shot, on-demand, returns immediately (or from cache if recently checked).
- **Monitor** — "tell me the moment my site stops being okay." Register a URL once; it's checked on a schedule, and a webhook fires the instant its state changes.

Both run on the same underlying check engine — this is a deliberate architecture choice (shared code path = less duplicated logic = a code-quality signal for the rubric), not two separate products bolted together.

---

## 3. Goals

### Task A Goals — Must-have (graded core)
1. A URL check runs end-to-end with real input validation, timeouts, and concurrency limits
2. Repeat checks within a configurable window are served from cache, not re-fetched
3. Requests are rate-limited per client with structured, request-ID-tagged logs
4. A meaningful automated test suite runs in CI on every push
5. Live deployment with the required footer credit

### Task A Goals — Should-have (Monitor stretch)
6. A URL can be registered for scheduled recurring checks
7. A state-change event (UP→DOWN, DOWN→UP, or latency threshold breach) fires a webhook alert
8. A bounded history/timeline of past checks for a monitored URL

### Task B Goals
1. Architecture that could plausibly handle 10,000 checks/day, 500-concurrent bursts, and (if Monitor is included) a scheduler fanning out recurring checks without becoming its own bottleneck
2. Explicit technology tradeoffs — chosen vs. rejected, with reasoning
3. Grounded failure-mode analysis
4. Concrete observability + rollback plan

### Non-Goals for THIS submission
Everything in §4.5 is explicitly a non-goal for the actual build — multi-dimensional deep audits, AI recommendations, dashboards/history comparisons, teams/RBAC, PDF export, email/SMS alerts, enterprise SSO, billing, white-label, mobile apps.

---

## 4. Scope

### 4.1 Must-have (Task A graded core)
- Single-page web UI: URL input → submit → results view
- `POST /audits` (run a check now) · `GET /audits/{id}` (fetch result/status)
- Input validation: malformed URLs, non-HTTP(S) schemes, localhost/private-IP rejection (SSRF protection)
- Outbound fetch timeout (configurable, default ~10s)
- Concurrency limit on simultaneous outbound checks
- Structured error responses on every failure path
- Cache: repeat checks of the same normalized URL within a configurable TTL return cached result
- Rate limit: per-client, `429` + `Retry-After` on breach
- Structured JSON logs with request ID, correlated end-to-end
- Test suite: unit + integration + at least one true end-to-end test
- CI: lint → test → build, on every push
- Footer credit line, live and visible

### 4.2 Should-have (Monitor extension — build only after 4.1 is solid)
- `POST /monitors` — register URL + interval + webhook URL
- Background scheduler triggers periodic checks reusing the Check/Audit engine
- State machine: `UP` / `DOWN` / `DEGRADED` (latency over threshold)
- Webhook POST on state transition
- `GET /monitors/{id}/history` — bounded list of past checks (e.g., last 50)

### 4.3 Could-have (only if time remains after 4.1 and 4.2)
- Configurable latency-only alert threshold, independent of up/down
- Manual "pause monitor" toggle

### 4.4 Out of scope for THIS submission (hard cut, not roadmap)
Multi-page crawl, mobile apps, 13-month-style long retention, competitor comparison, real-time dashboards beyond the basic UI.

### 4.5 Future Roadmap — Vision Only, NOT Built for This Task

*This section merges the original enterprise "audit everything" concept back in — labeled explicitly so it never gets mistaken for graded scope. Useful in the TRD/architecture doc as "here's what this cleanly extends to," useful nowhere else this week.*

**Phase 2 — Deepen the Check itself**
- Full SEO module (canonical tags, sitemap/robots presence, Open Graph/Twitter Card tags, heading structure, internal/external/broken link detection, duplicate metadata)
- Accessibility module (WCAG compliance, ARIA, color contrast, keyboard nav, semantic HTML)
- Best Practices module (deprecated APIs, console errors, manifest/service worker checks)
- PDF export of a Check result
- Audit history + before/after comparison dashboard
- Upgrade Monitor alerts from webhook-only to email/SMS

**Phase 3 — Make it smart**
- AI Recommendation Module: per-issue severity, plain-language explanation, business/technical impact, suggested fix, code example, estimated improvement
- A real scoring methodology (documented, versioned "Health Score Algorithm") powering a single unified score across modules
- Custom monitoring scripts (multi-step flows — inspired by the real PagePulse's "complex monitoring" scripting language), not just single-URL pings
- SEO/uptime trend analysis over time

**Phase 4 — Make it enterprise-ready**
- Team workspaces + RBAC (Owner/Admin/Editor/Viewer)
- Shareable public report links
- Enterprise SSO
- White-label reports
- Billing/monetization tiers
- SLA dashboards, multi-region deployment, autoscaling infrastructure

**Legal/ethical note carried forward from the enterprise draft, worth keeping in mind even for the graded build:** this service fetches third-party URLs that didn't opt in. Even at Task A scale, per-target-domain rate limiting and a clear crawler User-Agent are cheap to add and meaningfully reduce "this looks like an abuse vector" risk — worth a line in the TRD even if not explicitly graded.

---

## 5. Functional Requirements

### 5.1 Check/Audit — Must-have (mapped to task brief a/b/c/d)

| Task Item | Requirement | Acceptance Signal |
|---|---|---|
| (a) Validation, timeouts, concurrency, structured errors | FR-1: Reject invalid/unsafe URLs before any network call | Malformed URL → `400 INVALID_URL`; private IP → `400 URL_NOT_ALLOWED` |
| | FR-2: Outbound fetch has a hard timeout | Slow/hanging target → `504 TARGET_TIMEOUT` |
| | FR-3: Concurrent outbound checks are capped | Beyond cap → queue or `503 SERVICE_BUSY` |
| | FR-4: Every error path returns a structured response | `{ success, request_id, error: { code, message }, timestamp }` on 100% of non-2xx |
| (b) Caching, configurable window | FR-5: Repeat checks of the same normalized URL within TTL return cached result | Second identical request within window shows `"cache": "hit"`, materially faster |
| | FR-6: TTL window is configurable | Changeable via env/config, no code change |
| (c) Rate limiting, structured logging | FR-7: Per-client rate limit with clear breach response | Breach → `429` + `Retry-After` |
| | FR-8: Structured logs with request ID | Every request traceable via one `request_id` |
| (d) Tests + CI | FR-9: Suite covers validation, caching, rate limiting, and one real end-to-end check | CI shows passing suite + coverage report |
| | FR-10: CI runs on every push | GitHub Actions status visible in repo |

### 5.2 Monitor — Should-have (stretch)

| ID | Requirement | Acceptance Signal |
|---|---|---|
| FR-11 | Register a URL for recurring checks with configurable interval | `POST /monitors` returns `monitor_id`, first check runs within one interval |
| FR-12 | Scheduled checks reuse the Check engine (no duplicated logic) | Same validation/timeout/error handling applies |
| FR-13 | State transitions trigger a webhook POST | Simulated downtime → webhook receives alert within one check cycle |
| FR-14 | Bounded check history retrievable per monitor | `GET /monitors/{id}/history` returns last N checks, oldest evicted |

### 5.3 Future FRs (Phase 2–4)
Not specified at requirement level in this doc — deliberately left as roadmap bullets in §4.5 only, to avoid over-speccing scope that isn't being built.

---

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Latency (Task B target) | New check p95 under the stated SLA *(defined in TRD)* |
| Cached latency | Materially faster than fresh fetch, provably so |
| Scale (Task B) | 10,000 checks/day; 500 concurrent bursts |
| Monitor cadence (if built) | Minimum interval floor (e.g., 60s) so one monitor can't dominate the shared concurrency budget |
| Availability | Graceful degradation under load via rate limiting + concurrency caps |
| Security | SSRF protection at DNS-resolution time; no secrets in repo; HTTPS on live deploy |
| Observability | Structured JSON logs; request ID propagation end-to-end |

---

## 7. Success Metrics = Grading Rubric (Task A)

| Criterion | Weight | What "done" looks like |
|---|---|---|
| Correctness and resilience | 30% | Handles bad input, slow targets, target failures, concurrent load without crashing or hanging |
| Caching and rate limiting design | 20% | TTL configurable and provably reduces re-fetch; rate limit per-client, clearly signaled |
| Test coverage and CI | 25% | Meaningful tests (not just happy path), green CI on every push |
| Code quality and structure | 25% | Clean separation of concerns; Monitor (if built) reuses the Check engine rather than forking it |

**§4.5 (Future Roadmap) is not graded and should never consume time that belongs to the four criteria above.**

---

## 8. Live Build Requirements (Non-negotiable per brief)

- Publicly accessible live URL
- Visible footer: **"Built for Digital Heroes Training Task"**, hyperlinked to `digitalheroesco.com`
- Public GitHub repo containing tests + CI config
- README with the full API contract
- Submission includes the live URL, per the brief's submission instructions

---

## 9. Deliverables Checklist

**Task A**
- [ ] Public GitHub repo (tests + CI config included)
- [ ] Live deployed link
- [ ] README with API contract (Check/Audit required; Monitor documented if built, or noted "designed, not shipped" if time-constrained)
- [ ] Footer credit line + link, visible on the live page

**Task B**
- [ ] Architecture document + diagram (can reference how it extends to Monitor's scheduler and to Phase 2+ modules, without those being built)
- [ ] Technology Decision Record
- [ ] Failure Mode Analysis (top 3, with mitigations)
- [ ] Observability & Rollback Plan

---

## 10. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| §4.5 roadmap gets mistaken for required scope, leading to overbuilding | Medium | High | Explicit "vision only, NOT built" labeling in §0.2, §4.5 header, and §7; re-read §0.2 before starting any new feature |
| Monitor/alerting eats time needed to harden the graded Check path | High | High | Fixed build order: 4.1 complete + tested before any 4.2 code |
| Naming collision if "PulseWatch" turns out to also collide with something live | Low | Medium | Quick domain/trademark sanity check before final deploy naming |
| SSRF validation treated as an afterthought | Medium | High | Explicit FR-1 |
| Shallow ("happy-path only") tests hurt the 25%-weighted criterion | Medium | High | FR-9 requires validation-failure, cache-hit, rate-limit-breach, and timeout cases explicitly |
| Webhook alert delivery flakiness makes Monitor look broken during grading | Medium | Medium | Mock/stub the webhook target in tests |
| Footer credit requirement forgotten under build pressure | Low | High (disqualifying) | Called out as its own PRD section (§8) |

---

## 11. What's Next

Once naming (§0.1) is confirmed, the next document is the **TRD** — API contract (Check and Monitor endpoints), concurrency/timeout/rate-limit implementation approach, caching mechanism decision (in-memory vs. Redis), scheduler approach for Monitor, CI pipeline definition, and a short "extension points" note showing how §4.5's roadmap would plug in without being built now.
