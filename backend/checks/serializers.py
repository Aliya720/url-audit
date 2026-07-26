# DRF Serializers — TRD §4.1, §4.4
# Input validation via serializers (FR-1), response shaping

from rest_framework import serializers

from .models import Audit, Monitor, MonitorCheck


class AuditRequestSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/audits — TRD §4.1 / FR-1.

    Validates URL format at the DRF layer before SSRF checks run.
    """

    url = serializers.URLField(
        required=True,
        help_text="The URL to check (must be http:// or https://)",
    )


class AuditResultSerializer(serializers.ModelSerializer):
    """
    Output serializer for audit results — TRD §4.1 response shape.
    """

    class Meta:
        model = Audit
        fields = ["audit_id", "url", "cache", "checked_at", "result"]

    url = serializers.CharField(source="normalized_url")
    cache = serializers.SerializerMethodField()

    def get_cache(self, obj):
        return self.context.get("cache_status", "miss")


class MonitorRequestSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/monitors — TRD §4.4 / FR-11.
    """

    url = serializers.URLField(required=True)
    interval_seconds = serializers.IntegerField(required=True, min_value=1)
    webhook_url = serializers.URLField(required=True)
    latency_threshold_ms = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, default=None
    )


class MonitorResponseSerializer(serializers.ModelSerializer):
    """
    Output serializer for monitor responses — TRD §4.4, §4.5.
    """

    class Meta:
        model = Monitor
        fields = [
            "monitor_id",
            "url",
            "interval_seconds",
            "state",
            "last_checked_at",
            "next_check_at",
            "webhook_url",
            "latency_threshold_ms",
            "created_at",
        ]

    url = serializers.CharField(source="normalized_url")


class MonitorListSerializer(serializers.ModelSerializer):
    """
    Compact serializer for GET /api/monitors list.
    """

    class Meta:
        model = Monitor
        fields = [
            "monitor_id",
            "url",
            "state",
            "last_checked_at",
            "interval_seconds",
        ]

    url = serializers.CharField(source="normalized_url")


class MonitorCheckSerializer(serializers.ModelSerializer):
    """
    Output serializer for monitor check history — TRD §4.6.
    """

    class Meta:
        model = MonitorCheck
        fields = ["checked_at", "state", "response_time_ms", "status_code", "error_code"]
