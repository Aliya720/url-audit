# UI/UX Brief

## PulseWatch
**Digital Heroes SDE Qualification Task — Task A (Production Build) + Task B (Scale Design)**

| | |
|---|---|
| **Doc** | 4 of 6 — UI/UX Brief |
| **Version** | 1.0 |
| **Status** | Draft for Review |
| **Traces to** | App Flow v1.1 (§1 screen map, §8 cross-cutting concerns) |
| **Next docs** | Backend Schema → Implementation Plan |

---

## 0. Purpose & Scope

This turns App Flow's five screens into actual layout, component, and interaction detail — what to build in React, not just what sequence of requests happens. No visual design tool output here (colors/fonts are directional, not a locked style guide) — the point is that whoever builds this doesn't have to invent screen structure from scratch.

**Design stance:** this is a developer-facing utility, evaluated by someone checking whether it *works*, not a consumer product being pitched on delight. Favor clarity, information density, and visible proof of the things being graded (cache hit/miss, error states, request IDs) over decoration. Nothing here should require custom illustration or a component library beyond basics.

---

## 1. Global Elements (present on every screen)

### 1.1 Header
- App name/logo (text is fine — "PulseWatch" or final chosen name)
- Nav: **Check** | **My Monitors**

### 1.2 Footer — Required, Non-Negotiable
Exact copy and behavior, per the task brief's Live Build Requirement:

```
Built for Digital Heroes Training Task
```
- Hyperlinked to `https://digitalheroesco.com`
- Visible on every screen, not just Home — this is how the evaluator verifies the build
- Not dismissible, not below-the-fold in a way that requires scrolling to notice (footer of a short page is fine; don't bury it in a long scroll on a data-heavy screen like Monitor Detail)

### 1.3 Client-Key handling — invisible to the user
Per App Flow §0.1, the `X-Client-Key` header is generated once on first visit and stored in `localStorage`. **No UI for this at all** — no "your ID is..." display, no settings screen. It just works silently. (If it's ever surfaced, it should only be for a "this browser only" disclaimer near My Monitors — see §6 empty state — not as a feature.)

---

## 2. Screen 1 — Home / Check

```
┌──────────────────────────────────────────────┐
│  PulseWatch          [ Check ]  My Monitors    │
├──────────────────────────────────────────────┤
│                                                │
│   Check any website's health, instantly.       │
│                                                │
│   ┌──────────────────────────────┐  ┌───────┐ │
│   │ https://example.com           │  │ Check │ │
│   └──────────────────────────────┘  └───────┘ │
│                                                │
│   [inline error message appears here, if any] │
│                                                │
├──────────────────────────────────────────────┤
│  Built for Digital Heroes Training Task        │
└──────────────────────────────────────────────┘
```

**Components:** URL text input (with basic client-side format hint, not a replacement for server validation), Submit button (disabled while a request is in flight), inline error banner (appears only on error, pushes nothing else around unexpectedly).

**States:**
| State | Behavior |
|---|---|
| Idle | Empty input, button enabled once input is non-empty |
| Loading | Button shows a spinner + "Checking…", input disabled, no layout shift |
| Error | Red-toned inline banner above/below the input with the mapped message (§8) — input keeps the user's typed value so they can edit and resubmit |
| Success | Navigates to Check Result screen |

---

## 3. Screen 2 — Check Result

```
┌──────────────────────────────────────────────┐
│  ← Back            https://example.com         │
│  [cache: MISS]  Checked at 10:15:00 UTC         │
├──────────────────────────────────────────────┤
│  ┌ Availability ─────────┐ ┌ Performance ────┐ │
│  │ ● Reachable            │ │ 214ms response  │ │
│  │ Status: 200             │ │ 120ms TTFB      │ │
│  │ 0 redirects              │ │ 48.2 KB page   │ │
│  └───────────────────────┘ └────────────────┘ │
│  ┌ SEO Signals ───────────┐ ┌ Security ───────┐ │
│  │ ✓ Title present (42ch)  │ │ ✓ HSTS          │ │
│  │ ✓ Meta description       │ │ ✗ CSP           │ │
│  │ 1 H1 tag                  │ │ ✓ X-Frame-Opts │ │
│  └───────────────────────┘ └────────────────┘ │
│                                                │
│  [ Monitor this URL instead → ]                │
├──────────────────────────────────────────────┤
│  Built for Digital Heroes Training Task        │
└──────────────────────────────────────────────┘
```

**Components:** four result cards (Availability, Performance, SEO Signals, Security Headers), a cache badge (`MISS` in neutral gray, `HIT` in a distinct accent — this badge is the visible proof of FR-5/6 for anyone clicking around), a CTA that pre-fills the Register Monitor form with this URL.

**Error variant:** same screen shell, cards replaced by a single centered error state with the mapped message + retry button where applicable (§8 in App Flow already defines which codes are retryable).

**Design note — pass/fail iconography:** ✓/✗ (or colored dot) per boolean signal, not a single aggregate score. The PRD explicitly avoided building a unified scoring algorithm for this task (that's Phase 3 territory) — the UI shouldn't imply one exists by rendering something that looks like a single "grade."

---

## 4. Screen 3 — Register a Monitor

```
┌──────────────────────────────────────────────┐
│  PulseWatch          Check   [ My Monitors ]   │
├──────────────────────────────────────────────┤
│  Watch a website continuously                   │
│                                                │
│  URL                                           │
│  ┌──────────────────────────────────────────┐ │
│  │ https://example.com                        │ │
│  └──────────────────────────────────────────┘ │
│  Check every                                    │
│  [ 5 minutes ▾ ]   (min: 1 minute)              │
│  Alert webhook URL                              │
│  ┌──────────────────────────────────────────┐ │
│  │ https://your-endpoint.example/webhook       │ │
│  └──────────────────────────────────────────┘ │
│  Alert if slower than (optional)                │
│  [ 2000 ] ms                                    │
│                                                │
│              [ Start Monitoring ]               │
├──────────────────────────────────────────────┤
│  Built for Digital Heroes Training Task        │
└──────────────────────────────────────────────┘
```

**Components:** URL input, interval dropdown (preset options: 1/5/15/30/60 min — all above the configured floor, so the client can't even construct an invalid request), webhook URL input, optional latency threshold number input, submit button.

**Validation:** same inline-error pattern as Screen 1 for URL errors; a distinct message for `INTERVAL_TOO_SHORT` shouldn't be reachable at all if the dropdown only offers valid presets — defensive UI, not just relying on the server to catch it.

**On success:** redirect to My Monitors, with the new monitor visible showing `PENDING_FIRST_CHECK`.

---

## 5. Screen 4 — My Monitors (list)

```
┌──────────────────────────────────────────────┐
│  PulseWatch          Check   [ My Monitors ]   │
├──────────────────────────────────────────────┤
│  My Monitors                    [ + Add New ]  │
│                                                │
│  ┌────────────────────────────────────────┐  │
│  │ ● UP   example.com          5 min ago    │  │
│  ├────────────────────────────────────────┤  │
│  │ ● DOWN  another-site.com     2 min ago   │  │
│  ├────────────────────────────────────────┤  │
│  │ ◐ PENDING  new-site.com       just added │  │
│  └────────────────────────────────────────┘  │
├──────────────────────────────────────────────┤
│  Built for Digital Heroes Training Task        │
└──────────────────────────────────────────────┘
```

**Empty state** (no monitors yet, or a fresh browser with no `localStorage` key history):
```
No monitors yet.
Monitors are tied to this browser — clearing site data will lose access to them.
[ Register your first monitor ]
```
That second line is the one honest disclosure needed given the no-auth design (App Flow §0.1) — better to say it plainly than have someone confused later.

**Row → Monitor Detail** on click. State badge colors: see §7.

---

## 6. Screen 5 — Monitor Detail + History

```
┌──────────────────────────────────────────────┐
│  ← My Monitors                                │
│  example.com                          ● UP     │
│  Checked every 5 min · Last: 10:20:04 UTC       │
│                                    [ Delete ]   │
├──────────────────────────────────────────────┤
│  History                                        │
│  10:20:04  ● UP    210ms                        │
│  10:15:04  ● UP    198ms                         │
│  10:10:04  ● DOWN  timeout                       │
│  10:05:04  ● UP    205ms                         │
│  ...                                            │
├──────────────────────────────────────────────┤
│  Built for Digital Heroes Training Task        │
└──────────────────────────────────────────────┘
```

**Components:** current-state header (large, unmissable — this is the "is it okay right now" answer), metadata line (interval, last checked), delete button (with a confirm step — this is destructive and stops real monitoring), history list (timestamp, state, latency; failed checks show the error type instead of a latency number).

**Delete confirmation:** a simple "Stop monitoring example.com? This can't be undone." confirm/cancel — not a full modal component library dependency, a native `confirm()`-style pattern is acceptable for this scope.

---

## 7. State/Badge Color Mapping

| State | Color | Icon |
|---|---|---|
| `UP` | Green | ● |
| `DOWN` | Red | ● |
| `DEGRADED` | Amber/yellow | ● |
| `PENDING_FIRST_CHECK` | Gray | ◐ |
| Cache `HIT` | Teal/blue accent | — badge text "HIT" |
| Cache `MISS` | Neutral gray | — badge text "MISS" |

Color alone never carries meaning without the accompanying text/icon (§9 accessibility).

---

## 8. Error Copy Mapping

*One canonical message per error code, reused everywhere it can occur — per App Flow §8.2.*

| Error Code | User-Facing Message | Retry Offered? |
|---|---|---|
| `INVALID_URL` | "That doesn't look like a valid URL. Check the format and try again." | No — fix input |
| `URL_NOT_ALLOWED` | "This URL can't be checked — it points to a private or internal address." | No — fix input |
| `INTERVAL_TOO_SHORT` | *(shouldn't be reachable — dropdown constrains this)* | — |
| `CLIENT_KEY_REQUIRED` | *(internal — shouldn't surface; the app always sends this header)* | — |
| `AUDIT_NOT_FOUND` / `MONITOR_NOT_FOUND` | "We couldn't find that — it may have been removed." | No |
| `RATE_LIMITED` | "You're checking sites a bit fast — try again in a few seconds." | Yes, after `Retry-After` |
| `TARGET_UNREACHABLE` | "We couldn't reach that site. It may be down or blocking automated requests." | Yes |
| `TARGET_TIMEOUT` | "That site took too long to respond." | Yes |
| `SERVICE_BUSY` | "PulseWatch is handling a lot of checks right now — try again in a moment." | Yes |
| `INTERNAL_ERROR` | "Something went wrong on our end. Try again, or come back shortly." | Yes |

---

## 9. Accessibility Notes (light-touch, not a full audit)

- All interactive elements reachable and operable via keyboard (Tab/Enter) — no click-only handlers
- Form inputs have associated `<label>` elements, not placeholder-only labeling
- Loading state announced via an `aria-live="polite"` region so screen readers register "Checking…" → result without the user needing to notice a visual change
- State badges (§7) always pair color with text/icon, never color alone
- Minimum contrast: body text and status text both meet WCAG AA (4.5:1) against their background

*(Deliberately not building the deep Accessibility **module** here — that's PRD §4.5 Phase 2, auditing *other* sites' accessibility. This section is about this app's own basic usability, which costs little and is good practice regardless of task scope.)*

---

## 10. Responsive Behavior

- **Desktop (≥768px):** Result cards (§3) in a 2×2 grid; Monitor list rows full-width
- **Mobile (<768px):** Result cards stack vertically in a single column; header nav collapses to a simple two-link row (no hamburger menu needed for two items)
- Footer credit line stays visible and legible at both breakpoints — no truncation of the required text

---

## 11. Loading & Empty States — Summary

| Screen | Loading | Empty |
|---|---|---|
| Home/Check | Button spinner, input disabled | N/A (nothing to be empty) |
| Check Result | N/A (navigated to only after a response) | N/A |
| Register Monitor | Button spinner on submit | N/A |
| My Monitors | Skeleton rows or simple spinner on initial list load | "No monitors yet" message (§6) |
| Monitor Detail | Spinner on initial load | "No checks yet" if viewed before the first scheduled run completes |

---

## 12. Open Items Before Next Doc

1. Confirm the pass/fail icon (✓/✗) treatment for Check Result (§3) instead of a unified score — this is a deliberate product decision (no scoring algorithm exists yet, per PRD Phase 3), flagging in case a single visual score is actually wanted despite the backend not computing one.
2. Confirm native `confirm()`-style delete confirmation (§6) is acceptable, or if a proper modal component is expected.
3. None of §9's accessibility notes are rubric-required — confirm they're worth the small extra build time, or should be trimmed to keep scope tight.

Once confirmed, the **Backend Schema** doc defines the actual Postgres tables (`Monitor`, `MonitorCheck`, `Audit`, plus `django-celery-beat`'s own tables) that everything in this brief and the App Flow doc reads from and writes to.
