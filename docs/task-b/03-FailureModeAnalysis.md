# Task B: Failure Mode Analysis (FMA)

## Overview
This document analyzes potential system failure modes for PulseWatch, assessing their likelihood and impact, and detailing implemented architectural mitigations.

---

## Failure Mode 1: Worker Process Crash Mid-Check (Concurrency Lock Leak)

- **Scenario**: A Gunicorn or Celery worker process is terminated abruptly (OOM kill, network socket exception, or container restart) while executing an outbound HTTP fetch, after acquiring a concurrency slot.
- **Likelihood**: Medium
- **Impact**: High (If slots leak permanently, effective system concurrency decreases over time until reaching zero, causing perpetual `503 SERVICE_BUSY` errors).
- **Mitigation Implemented**:
  - Instead of a naive Redis `INCR`/`DECR` counter, PulseWatch uses a **Redis Sorted Set semaphore** (`concurrency:active_checks`).
  - Member = `request_id`, Score = `timestamp`.
  - On every `acquire_slot` attempt, the system executes `ZREMRANGEBYSCORE` to evict entries older than `2 * FETCH_TIMEOUT_SECONDS` (20 seconds).
  - Stale slots from dead workers are automatically reclaimed on the next request.
- **Verification**: Tested via unit tests and simulated worker cancellation in `checks/tests/test_api.py`.

---

## Failure Mode 2: Unbounded Growth of Historical Check Records (`monitor_checks`)

- **Scenario**: At 10,000 checks/day across hundreds of active monitors, the `monitor_checks` history table grows endlessly, degrading read performance on `GET /api/monitors/{id}/history` and exhausting database disk storage.
- **Likelihood**: High (Over time)
- **Impact**: High (Query slowdowns, storage exhaustion, expensive vacuum operations).
- **Mitigation Implemented**:
  - **Prune-on-write pattern**: On every new `MonitorCheck` insertion, `_prune_history(monitor_id)` executes in application code.
  - Rows exceeding `MONITOR_HISTORY_MAX` (default 50) for that specific monitor are deleted immediately:
    ```sql
    DELETE FROM monitor_checks
    WHERE monitor_id = %(monitor_id)s
      AND id NOT IN (
        SELECT id FROM monitor_checks
        WHERE monitor_id = %(monitor_id)s
        ORDER BY checked_at DESC
        LIMIT 50
      );
    ```
  - Storage footprint per monitor remains constant ($O(1)$ space bounded at 50 rows per monitor).
  - Composite B-Tree index `idx_monitor_checks_mid_cat` on `(monitor_id, checked_at DESC)` ensures history reads and pruning execute in sub-millisecond time.
- **Verification**: Verified via `test_prunes_beyond_max` in `checks/tests/test_monitor.py`.

---

## Failure Mode 3: Server-Side Request Forgery (SSRF) & Redirect Hop Exploitation

- **Scenario**: An attacker submits a public-looking URL (`https://public-site.com/redirect`) that redirects to internal infrastructure (`http://168.254.169.254/latest/meta-data/` or `http://127.0.0.1:8000/admin`).
- **Likelihood**: High (Common attack vector against URL checkers).
- **Impact**: Critical (Data exfiltration, cloud metadata exposure, internal port scanning).
- **Mitigation Implemented**:
  - **Pre-connect DNS Resolution**: `socket.getaddrinfo()` resolves hostnames before establishing any HTTP connection.
  - IPs are checked against `ipaddress` rules rejecting private (RFC1918), loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), and cloud metadata (`169.254.169.254`, `fd00::1`) addresses.
  - **Per-Hop Revalidation**: Requests use `allow_redirects=False`. Each redirect `Location` header is manually intercepted and subjected to full SSRF validation before following the next hop.
  - **Hop Limit**: Maximum redirect hops capped at `MAX_REDIRECT_HOPS = 5` to prevent infinite redirect loops.
- **Verification**: Verified via 15 unit tests in `checks/tests/test_url_validation.py`.
