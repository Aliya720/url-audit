# Tests for Monitor state machine and Celery tasks
# App Flow §5: every arrow in the state diagram tested
# TRD §10: task execution, webhook delivery, history pruning

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from checks.models import Monitor, MonitorCheck
from checks.tasks import _compute_state, _prune_history


@pytest.fixture
def mock_monitor(db):
    """Create a test monitor."""
    return Monitor.objects.create(
        owner_key="test-key",
        raw_url="https://example.com",
        normalized_url="https://example.com/",
        interval_seconds=300,
        webhook_url="https://hooks.example.com/test",
        latency_threshold_ms=2000,
        state="PENDING_FIRST_CHECK",
    )


class TestComputeState:
    """Tests for state computation — App Flow §5."""

    def test_unreachable_is_down(self, mock_monitor):
        result = {"availability": {"reachable": False}, "performance": {}}
        assert _compute_state(result, mock_monitor) == "DOWN"

    def test_reachable_normal_latency_is_up(self, mock_monitor):
        result = {
            "availability": {"reachable": True},
            "performance": {"response_time_ms": 200},
        }
        assert _compute_state(result, mock_monitor) == "UP"

    def test_reachable_high_latency_is_degraded(self, mock_monitor):
        result = {
            "availability": {"reachable": True},
            "performance": {"response_time_ms": 3000},
        }
        assert _compute_state(result, mock_monitor) == "DEGRADED"

    def test_no_latency_threshold_never_degraded(self, db):
        monitor = Monitor.objects.create(
            owner_key="test-key2",
            raw_url="https://no-threshold.example.com",
            normalized_url="https://no-threshold.example.com/",
            interval_seconds=300,
            webhook_url="https://hooks.example.com/test",
            latency_threshold_ms=None,
            state="UP",
        )
        result = {
            "availability": {"reachable": True},
            "performance": {"response_time_ms": 99999},
        }
        assert _compute_state(result, monitor) == "UP"


@pytest.mark.django_db
class TestStateTransitions:
    """Tests for every arrow in the state machine — App Flow §5.

    PENDING_FIRST_CHECK → UP (first check succeeds)
    PENDING_FIRST_CHECK → DOWN (first check fails)
    UP → DOWN (unreachable)
    UP → DEGRADED (slow)
    DEGRADED → UP (recovered)
    DEGRADED → DOWN (unreachable)
    DOWN → UP (recovered)
    DOWN → DEGRADED (reachable but slow)
    """

    def test_pending_to_up(self, mock_monitor):
        result = {"availability": {"reachable": True}, "performance": {"response_time_ms": 200}}
        new_state = _compute_state(result, mock_monitor)
        assert new_state == "UP"

    def test_pending_to_down(self, mock_monitor):
        result = {"availability": {"reachable": False}, "performance": {}}
        new_state = _compute_state(result, mock_monitor)
        assert new_state == "DOWN"

    def test_up_to_down(self, mock_monitor):
        mock_monitor.state = "UP"
        result = {"availability": {"reachable": False}, "performance": {}}
        assert _compute_state(result, mock_monitor) == "DOWN"

    def test_up_to_degraded(self, mock_monitor):
        mock_monitor.state = "UP"
        result = {"availability": {"reachable": True}, "performance": {"response_time_ms": 5000}}
        assert _compute_state(result, mock_monitor) == "DEGRADED"

    def test_degraded_to_up(self, mock_monitor):
        mock_monitor.state = "DEGRADED"
        result = {"availability": {"reachable": True}, "performance": {"response_time_ms": 100}}
        assert _compute_state(result, mock_monitor) == "UP"

    def test_degraded_to_down(self, mock_monitor):
        mock_monitor.state = "DEGRADED"
        result = {"availability": {"reachable": False}, "performance": {}}
        assert _compute_state(result, mock_monitor) == "DOWN"

    def test_down_to_up(self, mock_monitor):
        mock_monitor.state = "DOWN"
        result = {"availability": {"reachable": True}, "performance": {"response_time_ms": 150}}
        assert _compute_state(result, mock_monitor) == "UP"

    def test_down_to_degraded(self, mock_monitor):
        mock_monitor.state = "DOWN"
        result = {"availability": {"reachable": True}, "performance": {"response_time_ms": 5000}}
        assert _compute_state(result, mock_monitor) == "DEGRADED"


@pytest.mark.django_db
class TestPruneHistory:
    """Tests for prune-on-write — Backend Schema §4.1."""

    def test_prunes_beyond_max(self, mock_monitor):
        """Row count stays bounded at MONITOR_HISTORY_MAX."""
        # Create 55 checks (above default max of 50)
        for i in range(55):
            MonitorCheck.objects.create(
                monitor=mock_monitor,
                state="UP",
                response_time_ms=200 + i,
                checked_at=datetime(2026, 7, 25, 10, i, 0, tzinfo=timezone.utc),
            )

        with patch("checks.tasks.settings") as mock_settings:
            mock_settings.MONITOR_HISTORY_MAX = 50
            _prune_history(mock_monitor.monitor_id)

        remaining = MonitorCheck.objects.filter(monitor=mock_monitor).count()
        assert remaining == 50

    def test_keeps_most_recent(self, mock_monitor):
        """Pruning keeps the newest entries, drops the oldest."""
        for i in range(10):
            MonitorCheck.objects.create(
                monitor=mock_monitor,
                state="UP",
                response_time_ms=i,
                checked_at=datetime(2026, 7, 25, 10, i, 0, tzinfo=timezone.utc),
            )

        with patch("checks.tasks.settings") as mock_settings:
            mock_settings.MONITOR_HISTORY_MAX = 5
            _prune_history(mock_monitor.monitor_id)

        remaining = MonitorCheck.objects.filter(monitor=mock_monitor).order_by("-checked_at")
        assert remaining.count() == 5
        # Most recent should be minute 9
        assert remaining.first().response_time_ms == 9


@pytest.mark.django_db
class TestMonitorAlertsView:
    """Tests for GET /api/monitors/alerts."""

    def test_get_alerts(self, client, mock_monitor):
        # Set mock_monitor to DOWN state
        mock_monitor.state = "DOWN"
        mock_monitor.save()

        response = client.get(
            "/api/monitors/alerts",
            HTTP_X_CLIENT_KEY="test-key",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["active_alert_count"] == 1
        assert data["data"]["alerts"][0]["monitor_id"] == mock_monitor.monitor_id
        assert data["data"]["alerts"][0]["state"] == "DOWN"
