# Cache Wrapper — TRD §7 / FR-5, FR-6
# Redis-backed audit result cache using django-redis

import json
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("checks")

# Key pattern: cache:audit:{normalized_url} — Backend Schema §5
CACHE_KEY_PREFIX = "cache:audit:"


def _cache_key(normalized_url: str) -> str:
    """Build Redis cache key for an audit result."""
    return f"{CACHE_KEY_PREFIX}{normalized_url}"


def get_cached_audit(normalized_url: str) -> dict | None:
    """
    Retrieve a cached audit result — FR-5.

    Returns the cached result dict if found (cache HIT), None otherwise (cache MISS).
    """
    try:
        key = _cache_key(normalized_url)
        cached = cache.get(key)

        if cached is not None:
            logger.info(
                "cache_hit",
                extra={"normalized_url": normalized_url, "cache_key": key},
            )
            if isinstance(cached, str):
                return json.loads(cached)
            return cached

        logger.debug(
            "cache_miss",
            extra={"normalized_url": normalized_url, "cache_key": key},
        )
        return None
    except Exception as e:
        logger.warning("cache_get_error", extra={"error": str(e)[:200]})
        return None


def set_cached_audit(normalized_url: str, result: dict) -> None:
    """
    Store an audit result in cache — FR-5, FR-6.

    TTL is CACHE_TTL_SECONDS from settings (configurable via env, default 900s).
    """
    try:
        key = _cache_key(normalized_url)
        ttl = settings.CACHE_TTL_SECONDS

        cache.set(key, json.dumps(result), timeout=ttl)
        logger.info(
            "cache_set",
            extra={
                "normalized_url": normalized_url,
                "cache_key": key,
                "ttl_seconds": ttl,
            },
        )
    except Exception as e:
        logger.warning("cache_set_error", extra={"error": str(e)[:200]})
