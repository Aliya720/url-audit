# Direct tests for the concurrency semaphore — Backend Schema §5.1
#
# Previously this module (checks/utils/concurrency.py) had only 24% real
# test coverage: every test that exercises the request/task flow mocks
# acquire_slot/release_slot out entirely, so the actual Redis sorted-set
# logic — including the self-healing stale-slot pruning, which is the whole
# point of using a sorted set instead of a plain INCR/DECR counter — was
# never verified against real Redis. These tests call it directly.
#
# Skipped automatically if no Redis is reachable (e.g. a bare local dev run
# with no REDIS_URL set, which falls back to LocMemCache). CI's workflow
# runs a real redis service, so this suite runs for real there.

import time

import pytest
from django.conf import settings
from django.test import override_settings

try:
    from django_redis import get_redis_connection

    _redis = get_redis_connection("default")
    _redis.ping()
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not REDIS_AVAILABLE,
    reason="No real Redis reachable — concurrency.py needs django_redis, not LocMemCache",
)

from checks.utils.concurrency import acquire_slot, release_slot, CONCURRENCY_KEY  # noqa: E402


@pytest.fixture(autouse=True)
def clean_concurrency_key():
    """Every test starts and ends with a clean slate in Redis."""
    redis = get_redis_connection("default")
    redis.delete(CONCURRENCY_KEY)
    yield
    redis.delete(CONCURRENCY_KEY)


class TestAcquireRelease:
    def test_acquire_then_release_round_trips_cleanly(self):
        redis = get_redis_connection("default")

        assert acquire_slot("req-1") is True
        assert redis.zcard(CONCURRENCY_KEY) == 1

        release_slot("req-1")
        assert redis.zcard(CONCURRENCY_KEY) == 0

    def test_multiple_slots_tracked_independently(self):
        redis = get_redis_connection("default")

        assert acquire_slot("req-1") is True
        assert acquire_slot("req-2") is True
        assert redis.zcard(CONCURRENCY_KEY) == 2

        release_slot("req-1")
        assert redis.zcard(CONCURRENCY_KEY) == 1
        assert redis.zscore(CONCURRENCY_KEY, "req-2") is not None


class TestCapacity:
    @override_settings(MAX_CONCURRENT_CHECKS=2)
    def test_rejects_once_at_capacity(self):
        assert acquire_slot("req-1") is True
        assert acquire_slot("req-2") is True
        assert acquire_slot("req-3") is False

    @override_settings(MAX_CONCURRENT_CHECKS=1)
    def test_slot_freed_by_release_is_immediately_reusable(self):
        assert acquire_slot("req-1") is True
        assert acquire_slot("req-2") is False  # at capacity

        release_slot("req-1")
        assert acquire_slot("req-2") is True  # slot freed, now succeeds


class TestStaleSlotPruning:
    """
    The whole reason this is a sorted set instead of a plain counter:
    a worker that crashes mid-check (never calls release_slot) shouldn't
    permanently leak a slot. acquire_slot self-heals by pruning anything
    older than 2 * FETCH_TIMEOUT_SECONDS on every call.
    """

    @override_settings(MAX_CONCURRENT_CHECKS=1, FETCH_TIMEOUT_SECONDS=1)
    def test_stale_slot_is_pruned_and_capacity_reclaimed(self):
        redis = get_redis_connection("default")

        stale_timestamp = time.time() - (2 * settings.FETCH_TIMEOUT_SECONDS) - 5
        redis.zadd(CONCURRENCY_KEY, {"crashed-req": stale_timestamp})

        # Naively, capacity looks full (MAX_CONCURRENT_CHECKS=1, 1 entry present).
        # acquire_slot should prune the stale entry first and succeed anyway.
        assert acquire_slot("new-req") is True
        assert redis.zscore(CONCURRENCY_KEY, "crashed-req") is None, "stale slot should have been pruned"
        assert redis.zscore(CONCURRENCY_KEY, "new-req") is not None

    @override_settings(FETCH_TIMEOUT_SECONDS=10)
    def test_recent_slot_is_not_pruned(self):
        redis = get_redis_connection("default")
        recent_timestamp = time.time() - 1  # well within the staleness window
        redis.zadd(CONCURRENCY_KEY, {"still-active-req": recent_timestamp})

        acquire_slot("another-req")

        assert redis.zscore(CONCURRENCY_KEY, "still-active-req") is not None
