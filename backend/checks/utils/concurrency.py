# Concurrency Gate — Backend Schema §5.1
# Redis Sorted Set-based semaphore for cross-process concurrency limiting
# Self-healing: crashed slots reclaimed after 2 * FETCH_TIMEOUT_SECONDS

import logging
import time

from django.conf import settings
from django_redis import get_redis_connection

logger = logging.getLogger("checks")

CONCURRENCY_KEY = "concurrency:active_checks"


def acquire_slot(request_id: str) -> bool:
    """
    Acquire a concurrency slot — TRD §3 step 6 / Backend Schema §5.1.

    Uses a Redis Sorted Set where:
    - member = request_id (or monitor_id:timestamp for scheduled checks)
    - score = acquisition timestamp

    Before checking capacity, prunes stale entries (self-healing against
    crashed workers that never released their slot).

    Returns True if a slot was acquired, False if at capacity (→ 503).
    """
    try:
        redis = get_redis_connection("default")
        now = time.time()
        max_checks = settings.MAX_CONCURRENT_CHECKS
        fetch_timeout = settings.FETCH_TIMEOUT_SECONDS

        # Prune stale entries — self-healing (Backend Schema §5.1)
        stale_threshold = now - (2 * fetch_timeout)
        pruned = redis.zremrangebyscore(CONCURRENCY_KEY, "-inf", stale_threshold)
        if pruned:
            logger.warning(
                "concurrency_pruned_stale",
                extra={"pruned_count": pruned, "threshold": stale_threshold},
            )

        # Check current count
        current_count = redis.zcard(CONCURRENCY_KEY)

        if current_count >= max_checks:
            logger.warning(
                "concurrency_full",
                extra={
                    "request_id": request_id,
                    "current_count": current_count,
                    "max_checks": max_checks,
                },
            )
            return False

        # Acquire slot
        redis.zadd(CONCURRENCY_KEY, {request_id: now})
        logger.info(
            "concurrency_acquired",
            extra={
                "request_id": request_id,
                "current_count": current_count + 1,
                "max_checks": max_checks,
            },
        )
        return True
    except Exception as e:
        logger.warning(
            "concurrency_redis_fallback",
            extra={"error": str(e)[:200]},
        )
        return True


def release_slot(request_id: str) -> None:
    """
    Release a concurrency slot — called on completion (success or handled error).
    """
    try:
        redis = get_redis_connection("default")
        removed = redis.zrem(CONCURRENCY_KEY, request_id)
        logger.info(
            "concurrency_released",
            extra={"request_id": request_id, "was_present": bool(removed)},
        )
    except Exception:
        pass
