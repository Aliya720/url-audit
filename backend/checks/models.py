# Models — Backend Schema §2, §3, §4
# Audit, Monitor, MonitorCheck

import secrets

from django.conf import settings
from django.db import models


def generate_audit_id():
    """Generate prefixed audit ID: aud_ + 8 hex chars (Backend Schema §2)."""
    return f"aud_{secrets.token_hex(8)}"


def generate_monitor_id():
    """Generate prefixed monitor ID: mon_ + 8 hex chars (Backend Schema §3)."""
    return f"mon_{secrets.token_hex(8)}"


class Audit(models.Model):
    """
    Durable record of every completed Check — Backend Schema §2.

    Persisted to Postgres so GET /api/audits/{id} works even after
    the Redis cache entry expires.
    """

    audit_id = models.CharField(
        max_length=32, primary_key=True, default=generate_audit_id, editable=False
    )
    raw_url = models.TextField(help_text="URL exactly as submitted, pre-normalization")
    normalized_url = models.CharField(
        max_length=2048,
        db_index=True,
        help_text="Lowercased host, stripped default port, sorted query params",
    )
    request_id = models.CharField(
        max_length=64, help_text="Correlates to structured log lines (TRD §9)"
    )
    result = models.JSONField(
        help_text="Full result: availability/performance/seo_signals/security_headers"
    )
    status = models.CharField(
        max_length=16,
        choices=[("completed", "Completed"), ("failed", "Failed")],
        help_text="completed | failed — failed audits still get a row",
    )
    checked_at = models.DateTimeField(help_text="When the check actually ran")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audits"
        indexes = [
            models.Index(
                fields=["-created_at"], name="idx_audits_created_at"
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.audit_id} — {self.normalized_url}"


class Monitor(models.Model):
    """
    Monitor configuration — Backend Schema §3.

    Tracks a URL registered for recurring checks with a webhook alert.
    """

    STATE_CHOICES = [
        ("PENDING_FIRST_CHECK", "Pending First Check"),
        ("UP", "Up"),
        ("DOWN", "Down"),
        ("DEGRADED", "Degraded"),
    ]

    monitor_id = models.CharField(
        max_length=32, primary_key=True, default=generate_monitor_id, editable=False
    )
    owner_key = models.CharField(
        max_length=64,
        db_index=True,
        help_text="X-Client-Key header value (App Flow §0.1)",
    )
    raw_url = models.TextField(help_text="URL as submitted")
    normalized_url = models.CharField(max_length=2048)
    interval_seconds = models.IntegerField(
        help_text="Check interval (min: MONITOR_MIN_INTERVAL_SECONDS)"
    )
    webhook_url = models.TextField(help_text="Alert destination URL")
    latency_threshold_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="NULL = no latency-based DEGRADED check, only up/down",
    )
    state = models.CharField(
        max_length=24,
        choices=STATE_CHOICES,
        default="PENDING_FIRST_CHECK",
    )
    last_checked_at = models.DateTimeField(
        null=True, blank=True, help_text="NULL until first scheduled check"
    )
    next_check_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Display-only estimate, real schedule in django-celery-beat",
    )
    periodic_task_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Points to django_celery_beat_periodictask.id (no DB FK — §1 note)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "monitors"
        indexes = [
            models.Index(fields=["normalized_url"], name="idx_monitors_normalized_url"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["owner_key", "normalized_url"],
                name="unique_owner_url",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.monitor_id} — {self.normalized_url} ({self.state})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.interval_seconds < settings.MONITOR_MIN_INTERVAL_SECONDS:
            raise ValidationError(
                f"Interval must be at least {settings.MONITOR_MIN_INTERVAL_SECONDS}s"
            )


class MonitorCheck(models.Model):
    """
    Individual check result for a monitored URL — Backend Schema §4.

    Bounded history: prune-on-write keeps row count ≤ MONITOR_HISTORY_MAX.
    """

    monitor = models.ForeignKey(
        Monitor,
        on_delete=models.CASCADE,
        related_name="checks",
        to_field="monitor_id",
        db_column="monitor_id",
    )
    state = models.CharField(
        max_length=24, help_text="State snapshot as of this check"
    )
    response_time_ms = models.IntegerField(
        null=True, blank=True, help_text="NULL on outright failure"
    )
    status_code = models.IntegerField(
        null=True, blank=True, help_text="NULL on total unreachability"
    )
    error_code = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="TRD §5 error code, populated only on failure",
    )
    checked_at = models.DateTimeField()

    class Meta:
        db_table = "monitor_checks"
        indexes = [
            models.Index(
                fields=["monitor", "-checked_at"],
                name="idx_monitor_checks_mid_cat",
            ),
        ]
        ordering = ["-checked_at"]

    def __str__(self):
        return f"{self.monitor_id} @ {self.checked_at} — {self.state}"
