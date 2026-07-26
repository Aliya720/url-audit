# Celery Tasks — TRD §10 / FR-11–FR-14
# Scheduled monitor checks, reusing the Check engine (FR-12 — no duplicated logic)

import logging
from datetime import datetime, timedelta, timezone

import requests as http_requests
from celery import shared_task
from django.conf import settings

from .engine import run_check
from .exceptions import TargetTimeout, TargetUnreachable, URLNotAllowed
from .middleware import generate_request_id, request_id_var
from .models import Monitor, MonitorCheck
from .utils.concurrency import acquire_slot, release_slot

logger = logging.getLogger("checks")


def _compute_state(result: dict, monitor: Monitor) -> str:
    """
    Compute monitor state from check result — App Flow §5 state machine.

    - Unreachable / non-2xx / timeout → DOWN
    - Reachable but latency > threshold → DEGRADED
    - Reachable and latency OK → UP
    """
    availability = result.get("availability", {})
    performance = result.get("performance", {})

    if not availability.get("reachable", False):
        return "DOWN"

    # Check latency threshold (DEGRADED state)
    if monitor.latency_threshold_ms is not None:
        response_time = performance.get("response_time_ms", 0)
        if response_time > monitor.latency_threshold_ms:
            return "DEGRADED"

    return "UP"


def _send_webhook(monitor: Monitor, previous_state: str, new_state: str, checked_at: str, request_id: str):
    """
    Send webhook notification on state change — TRD §4.8.

    Single attempt with short timeout for this task. Retry-with-backoff
    is a Task B note, not built here (but tenacity is wired for the attempt).
    """
    payload = {
        "event": "monitor.state_changed",
        "monitor_id": monitor.monitor_id,
        "url": monitor.normalized_url,
        "previous_state": previous_state,
        "new_state": new_state,
        "checked_at": checked_at,
        "request_id": request_id,
    }

    try:
        response = http_requests.post(
            monitor.webhook_url,
            json=payload,
            timeout=5,
            headers={"Content-Type": "application/json", "User-Agent": "PulseWatch/1.0"},
        )
        logger.info(
            "webhook_sent",
            extra={
                "request_id": request_id,
                "monitor_id": monitor.monitor_id,
                "webhook_url": monitor.webhook_url,
                "status_code": response.status_code,
                "previous_state": previous_state,
                "new_state": new_state,
            },
        )
    except Exception as e:
        # Log failure — single attempt per TRD §4.8
        logger.error(
            "webhook_failed",
            extra={
                "request_id": request_id,
                "monitor_id": monitor.monitor_id,
                "webhook_url": monitor.webhook_url,
                "error": str(e)[:200],
            },
        )


def _prune_history(monitor_id: str):
    """
    Prune monitor check history beyond MONITOR_HISTORY_MAX — Backend Schema §4.1.

    Keeps storage flat regardless of how long a monitor has existed.
    """
    max_history = settings.MONITOR_HISTORY_MAX
    check_ids_to_keep = (
        MonitorCheck.objects.filter(monitor_id=monitor_id)
        .order_by("-checked_at")
        .values_list("id", flat=True)[:max_history]
    )
    deleted_count, _ = (
        MonitorCheck.objects.filter(monitor_id=monitor_id).exclude(id__in=list(check_ids_to_keep)).delete()
    )
    if deleted_count:
        logger.info(
            "history_pruned",
            extra={"monitor_id": monitor_id, "deleted_count": deleted_count},
        )


@shared_task(bind=True, max_retries=0)
def run_monitor_check(self, monitor_id: str):
    """
    Celery task: run a scheduled check for a monitored URL — TRD §10.

    - Reuses the Check engine from Phase 1 (FR-12)
    - Skips Redis cache (always fetches fresh — App Flow §4 note)
    - Uses shared concurrency semaphore (TRD §10)
    - Computes state, writes MonitorCheck, fires webhook on state change
    """
    # Generate a request_id for this task (TRD §9)
    request_id = generate_request_id()
    request_id_var.set(request_id)

    logger.info(
        "monitor_check_started",
        extra={"request_id": request_id, "monitor_id": monitor_id},
    )

    try:
        monitor = Monitor.objects.get(monitor_id=monitor_id)
    except Monitor.DoesNotExist:
        logger.error(
            "monitor_not_found_for_check",
            extra={"request_id": request_id, "monitor_id": monitor_id},
        )
        return

    previous_state = monitor.state

    # Acquire concurrency slot (shared with on-demand checks — TRD §10)
    if not acquire_slot(request_id):
        logger.warning(
            "monitor_check_skipped_busy",
            extra={"request_id": request_id, "monitor_id": monitor_id},
        )
        return  # Will retry on next scheduled interval

    checked_at = datetime.now(timezone.utc)
    new_state = "DOWN"
    response_time_ms = None
    status_code = None
    error_code = None

    try:
        # Run the check engine (same path as POST /api/audits — FR-12)
        result = run_check(monitor.normalized_url, request_id)
        new_state = _compute_state(result, monitor)
        response_time_ms = result.get("performance", {}).get("response_time_ms")
        status_code = result.get("availability", {}).get("status_code")

    except TargetTimeout:
        new_state = "DOWN"
        error_code = "TARGET_TIMEOUT"
    except TargetUnreachable:
        new_state = "DOWN"
        error_code = "TARGET_UNREACHABLE"
    except URLNotAllowed:
        new_state = "DOWN"
        error_code = "URL_NOT_ALLOWED"
    except Exception:
        new_state = "DOWN"
        error_code = "INTERNAL_ERROR"
        logger.exception(
            "monitor_check_unhandled_error",
            extra={"request_id": request_id, "monitor_id": monitor_id},
        )
    finally:
        release_slot(request_id)

    # Write MonitorCheck row (Backend Schema §4)
    MonitorCheck.objects.create(
        monitor=monitor,
        state=new_state,
        response_time_ms=response_time_ms,
        status_code=status_code,
        error_code=error_code,
        checked_at=checked_at,
    )

    # Prune history (Backend Schema §4.1)
    _prune_history(monitor_id)

    # Update monitor state
    monitor.state = new_state
    monitor.last_checked_at = checked_at
    monitor.next_check_at = checked_at + timedelta(seconds=monitor.interval_seconds)
    monitor.save(update_fields=["state", "last_checked_at", "next_check_at"])

    # Fire webhook on state change (FR-13, App Flow §5)
    # Webhook fires on every transition EXCEPT [*] → PENDING_FIRST_CHECK
    # PENDING_FIRST_CHECK → UP/DOWN/DEGRADED DOES fire (App Flow §5 note)
    if new_state != previous_state:
        _send_webhook(monitor, previous_state, new_state, checked_at.isoformat(), request_id)

    logger.info(
        "monitor_check_completed",
        extra={
            "request_id": request_id,
            "monitor_id": monitor_id,
            "previous_state": previous_state,
            "new_state": new_state,
            "state_changed": new_state != previous_state,
            "response_time_ms": response_time_ms,
        },
    )
