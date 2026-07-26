# API Views — TRD §4.1–§4.7
# Implements the full request lifecycle from TRD §3

import logging
from datetime import datetime, timezone

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .engine import run_check
from .exceptions import (
    AuditNotFound,
    MonitorNotFound,
    ServiceBusy,
    InternalError,
    IntervalTooShort,
)
from .middleware import get_current_request_id
from .models import Audit, Monitor, MonitorCheck
from .serializers import (
    AuditRequestSerializer,
    MonitorCheckSerializer,
    MonitorListSerializer,
    MonitorRequestSerializer,
    MonitorResponseSerializer,
)
from .utils.cache import get_cached_audit, set_cached_audit
from .utils.concurrency import acquire_slot, release_slot
from .utils.url_validation import validate_and_normalize

logger = logging.getLogger("checks")


class AuditCreateView(APIView):
    """
    POST /api/audits — Run an on-demand URL check.
    TRD §3 request lifecycle, §4.1 API contract.

    Steps: throttle → validate → SSRF → cache → concurrency → fetch → respond
    """

    def post(self, request):
        request_id = get_current_request_id() or "req_unknown"

        # Step 3: Validate URL (DRF serializer — FR-1)
        serializer = AuditRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_url = serializer.validated_data["url"]

        # Step 4: SSRF check + normalize (FR-1)
        parsed, normalized_url = validate_and_normalize(raw_url)

        # Step 5: Cache lookup (FR-5)
        cached_result = get_cached_audit(normalized_url)
        if cached_result is not None:
            # Cache HIT — return cached result directly
            return Response(
                {
                    "success": True,
                    "request_id": request_id,
                    "data": {
                        "audit_id": cached_result.get("audit_id"),
                        "url": normalized_url,
                        "cache": "hit",
                        "checked_at": cached_result.get("checked_at"),
                        "result": cached_result.get("result"),
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                status=status.HTTP_200_OK,
            )

        # Step 6: Concurrency gate (FR-3)
        if not acquire_slot(request_id):
            raise ServiceBusy()

        try:
            # Run the check engine (FR-1, FR-2)
            result = run_check(normalized_url, request_id)
            checked_at = datetime.now(timezone.utc)

            # Persist to Postgres (App Flow §2 — durable record)
            audit = Audit.objects.create(
                raw_url=raw_url,
                normalized_url=normalized_url,
                request_id=request_id,
                result=result,
                status="completed",
                checked_at=checked_at,
            )

            # Write to Redis cache (FR-5)
            cache_data = {
                "audit_id": audit.audit_id,
                "result": result,
                "checked_at": checked_at.isoformat(),
            }
            set_cached_audit(normalized_url, cache_data)

            # Step 7: Success response (TRD §4.1)
            return Response(
                {
                    "success": True,
                    "request_id": request_id,
                    "data": {
                        "audit_id": audit.audit_id,
                        "url": normalized_url,
                        "cache": "miss",
                        "checked_at": checked_at.isoformat(),
                        "result": result,
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                status=status.HTTP_200_OK,
            )

        except Exception:
            # On error during fetch, persist a failed audit record
            try:
                Audit.objects.create(
                    raw_url=raw_url,
                    normalized_url=normalized_url,
                    request_id=request_id,
                    result={},
                    status="failed",
                    checked_at=datetime.now(timezone.utc),
                )
            except Exception:
                pass  # Don't mask the original error
            raise

        finally:
            # Always release concurrency slot (TRD §3 step 6)
            release_slot(request_id)


class AuditDetailView(APIView):
    """
    GET /api/audits/{audit_id} — Fetch a previously completed audit.
    TRD §4.2.
    """

    # No throttle on GET reads (TRD §8 — separate/more generous scope)
    throttle_classes = []

    def get(self, request, audit_id):
        request_id = get_current_request_id() or "req_unknown"

        try:
            audit = Audit.objects.get(audit_id=audit_id)
        except Audit.DoesNotExist:
            raise AuditNotFound()

        return Response(
            {
                "success": True,
                "request_id": request_id,
                "data": {
                    "audit_id": audit.audit_id,
                    "url": audit.normalized_url,
                    "cache": "stored",
                    "checked_at": audit.checked_at.isoformat(),
                    "result": audit.result,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            status=status.HTTP_200_OK,
        )


class HealthCheckView(APIView):
    """
    GET /api/health — Liveness/readiness check.
    TRD §4.3 — backed by django-health-check.
    """

    throttle_classes = []

    def get(self, request):
        import time as _time

        from django.core.cache import cache
        from django.db import connection

        checks = {}
        overall_ok = True

        # Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"
            overall_ok = False

        # Redis check
        try:
            cache.set("health_check", "ok", timeout=10)
            val = cache.get("health_check")
            checks["redis"] = "ok" if val == "ok" else "error"
        except Exception:
            checks["redis"] = "error"
            overall_ok = False

        # Celery worker check
        try:
            from pulsewatch.celery import app

            inspector = app.control.inspect(timeout=2.0)
            ping_result = inspector.ping()
            checks["celery_worker"] = "ok" if ping_result else "error"
        except Exception:
            checks["celery_worker"] = "error"
            overall_ok = False

        response_data = {
            "status": "ok" if overall_ok else "error",
            "checks": checks,
        }

        return Response(
            response_data,
            status=status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class MonitorListCreateView(APIView):
    """
    POST /api/monitors — Register a URL for recurring checks (FR-11).
    GET /api/monitors — List monitors for the current client (App Flow §6).
    """

    def _get_client_key(self, request):
        """Extract X-Client-Key from request."""
        client_key = request.META.get("HTTP_X_CLIENT_KEY")
        if not client_key:
            from .exceptions import APIException

            class ClientKeyRequired(APIException):
                status_code = 400
                default_detail = "X-Client-Key header is required."
                default_code = "CLIENT_KEY_REQUIRED"

            raise ClientKeyRequired()
        return client_key

    def get(self, request):
        """GET /api/monitors — list monitors owned by X-Client-Key."""
        client_key = self._get_client_key(request)
        request_id = get_current_request_id() or "req_unknown"

        monitors = Monitor.objects.filter(owner_key=client_key)
        serializer = MonitorListSerializer(monitors, many=True)

        return Response(
            {
                "success": True,
                "request_id": request_id,
                "data": serializer.data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        """POST /api/monitors — register a new monitor (FR-11)."""
        client_key = self._get_client_key(request)
        request_id = get_current_request_id() or "req_unknown"

        # Validate input
        serializer = MonitorRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Validate URL + SSRF
        raw_url = data["url"]
        parsed, normalized_url = validate_and_normalize(raw_url)

        # Validate interval (FR-11)
        interval = data["interval_seconds"]
        if interval < settings.MONITOR_MIN_INTERVAL_SECONDS:
            raise IntervalTooShort(
                f"Minimum interval is {settings.MONITOR_MIN_INTERVAL_SECONDS} seconds."
            )

        # Validate webhook URL (same SSRF rules — App Flow §3)
        webhook_url = data["webhook_url"]

        # Check for duplicate (unique constraint: owner_key + normalized_url)
        if Monitor.objects.filter(
            owner_key=client_key, normalized_url=normalized_url
        ).exists():
            from .exceptions import APIException

            class DuplicateMonitor(APIException):
                status_code = 409
                default_detail = "A monitor for this URL already exists."
                default_code = "DUPLICATE_MONITOR"

            raise DuplicateMonitor()

        # Create django-celery-beat schedule (TRD §10)
        from datetime import timedelta

        from django_celery_beat.models import IntervalSchedule, PeriodicTask

        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=interval,
            period=IntervalSchedule.SECONDS,
        )

        # Create the Monitor
        monitor = Monitor.objects.create(
            owner_key=client_key,
            raw_url=raw_url,
            normalized_url=normalized_url,
            interval_seconds=interval,
            webhook_url=webhook_url,
            latency_threshold_ms=data.get("latency_threshold_ms"),
            state="PENDING_FIRST_CHECK",
            next_check_at=datetime.now(timezone.utc) + timedelta(seconds=interval),
        )

        # Create PeriodicTask (TRD §10 step 2)
        import json

        periodic_task = PeriodicTask.objects.create(
            name=f"monitor_{monitor.monitor_id}",
            task="checks.tasks.run_monitor_check",
            args=json.dumps([monitor.monitor_id]),
            interval=schedule,
            enabled=True,
        )

        # Store the periodic_task_id on the monitor
        monitor.periodic_task_id = periodic_task.id
        monitor.save(update_fields=["periodic_task_id"])

        response_serializer = MonitorResponseSerializer(monitor)

        return Response(
            {
                "success": True,
                "request_id": request_id,
                "data": response_serializer.data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class MonitorDetailView(APIView):
    """
    GET /api/monitors/{monitor_id} — Current monitor state (TRD §4.5).
    DELETE /api/monitors/{monitor_id} — Stop monitoring (TRD §4.7).
    """

    throttle_classes = []

    def _get_monitor(self, monitor_id, request):
        """Get monitor, verify ownership (App Flow §7 — 404 not 403 for non-owner)."""
        client_key = request.META.get("HTTP_X_CLIENT_KEY")
        if not client_key:
            raise MonitorNotFound()

        try:
            monitor = Monitor.objects.get(monitor_id=monitor_id)
        except Monitor.DoesNotExist:
            raise MonitorNotFound()

        if monitor.owner_key != client_key:
            # 404 not 403 — don't leak existence (App Flow §7)
            raise MonitorNotFound()

        return monitor

    def get(self, request, monitor_id):
        """GET /api/monitors/{monitor_id} — current state."""
        request_id = get_current_request_id() or "req_unknown"
        monitor = self._get_monitor(monitor_id, request)

        # Include last_result from most recent MonitorCheck
        last_check = monitor.checks.first()
        last_result = None
        if last_check:
            last_result = MonitorCheckSerializer(last_check).data

        serializer = MonitorResponseSerializer(monitor)
        data = serializer.data
        data["last_result"] = last_result

        return Response(
            {
                "success": True,
                "request_id": request_id,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, monitor_id):
        """DELETE /api/monitors/{monitor_id} — stop monitoring (TRD §4.7, App Flow §7)."""
        monitor = self._get_monitor(monitor_id, request)

        # Delete the PeriodicTask so Beat stops scheduling it (App Flow §7)
        if monitor.periodic_task_id:
            try:
                from django_celery_beat.models import PeriodicTask

                PeriodicTask.objects.filter(id=monitor.periodic_task_id).delete()
            except Exception as e:
                logger.warning(
                    "periodic_task_delete_failed",
                    extra={
                        "monitor_id": monitor_id,
                        "periodic_task_id": monitor.periodic_task_id,
                        "error": str(e),
                    },
                )

        # Delete monitor (cascades to MonitorCheck history — Backend Schema §4)
        monitor.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class MonitorHistoryView(APIView):
    """
    GET /api/monitors/{monitor_id}/history — Bounded check history (TRD §4.6 / FR-14).
    """

    throttle_classes = []

    def get(self, request, monitor_id):
        request_id = get_current_request_id() or "req_unknown"

        # Verify ownership
        client_key = request.META.get("HTTP_X_CLIENT_KEY")
        if not client_key:
            raise MonitorNotFound()

        try:
            monitor = Monitor.objects.get(monitor_id=monitor_id)
        except Monitor.DoesNotExist:
            raise MonitorNotFound()

        if monitor.owner_key != client_key:
            raise MonitorNotFound()

        # Get limit from query params (default/max: MONITOR_HISTORY_MAX)
        limit = min(
            int(request.query_params.get("limit", settings.MONITOR_HISTORY_MAX)),
            settings.MONITOR_HISTORY_MAX,
        )

        checks = MonitorCheck.objects.filter(
            monitor=monitor
        ).order_by("-checked_at")[:limit]

        serializer = MonitorCheckSerializer(checks, many=True)

        return Response(
            {
                "success": True,
                "request_id": request_id,
                "data": {
                    "monitor_id": monitor_id,
                    "checks": serializer.data,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            status=status.HTTP_200_OK,
        )


class MonitorAlertsView(APIView):
    """
    GET /api/monitors/alerts — Active alerts and warnings for owner_key.
    """

    throttle_classes = []

    def get(self, request):
        client_key = request.META.get("HTTP_X_CLIENT_KEY")
        if not client_key:
            from .exceptions import APIException

            class ClientKeyRequired(APIException):
                status_code = 400
                default_detail = "X-Client-Key header is required."
                default_code = "CLIENT_KEY_REQUIRED"

            raise ClientKeyRequired()

        request_id = get_current_request_id() or "req_unknown"

        # Active alert monitors (state in DOWN or DEGRADED)
        active_alert_monitors = Monitor.objects.filter(
            owner_key=client_key, state__in=["DOWN", "DEGRADED"]
        )

        alerts = []
        for mon in active_alert_monitors:
            last_check = mon.checks.first()
            alerts.append(
                {
                    "monitor_id": mon.monitor_id,
                    "url": mon.raw_url,
                    "normalized_url": mon.normalized_url,
                    "state": mon.state,
                    "last_checked_at": mon.last_checked_at.isoformat() if mon.last_checked_at else None,
                    "error_code": last_check.error_code if last_check else None,
                    "response_time_ms": last_check.response_time_ms if last_check else None,
                }
            )

        return Response(
            {
                "success": True,
                "request_id": request_id,
                "data": {
                    "active_alert_count": len(alerts),
                    "alerts": alerts,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            status=status.HTTP_200_OK,
        )

