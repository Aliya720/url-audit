# Rate Limiting — TRD §8
# DRF SimpleRateThrottle subclass, keyed on X-Client-Key or client IP, Redis-backed

import time

from django.conf import settings
from django.core.cache import cache
from rest_framework.throttling import BaseThrottle


class PulseWatchThrottle(BaseThrottle):
    """
    Token-bucket-style throttle backed by Redis (TRD §8).

    - Keyed on X-Client-Key header if present, else client IP
    - RATE_LIMIT_BURST tokens max in bucket
    - RATE_LIMIT_MAX_REQUESTS tokens refilled per RATE_LIMIT_WINDOW_SECONDS
    - Returns Retry-After on breach

    Uses Redis via Django's cache framework (same instance as audit cache).
    """

    scope = "pulsewatch"

    def get_ident(self, request):
        """
        Key by X-Client-Key if present, else by client IP (TRD §8).
        Same key used for both throttling and Monitor ownership.
        """
        client_key = request.META.get("HTTP_X_CLIENT_KEY")
        if client_key:
            return f"key:{client_key}"
        # Fall back to IP
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return f"ip:{xff.split(',')[0].strip()}"
        return f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"

    def allow_request(self, request, view):
        """Token bucket rate limiting."""
        try:
            ident = self.get_ident(request)
            cache_key = f"throttle:{ident}"
            now = time.time()

            max_requests = settings.RATE_LIMIT_MAX_REQUESTS
            window = settings.RATE_LIMIT_WINDOW_SECONDS
            burst = settings.RATE_LIMIT_BURST

            # Rate at which tokens are refilled (tokens per second)
            refill_rate = max_requests / window

            # Get current bucket state from cache
            bucket = cache.get(cache_key)
            if bucket is None:
                # First request — start with a full bucket
                bucket = {"tokens": burst - 1, "last_refill": now}
                cache.set(cache_key, bucket, timeout=window * 2)
                return True

            tokens = bucket.get("tokens", burst)
            last_refill = bucket.get("last_refill", now)

            # Calculate tokens to add since last request
            elapsed = now - last_refill
            tokens_to_add = elapsed * refill_rate
            tokens = min(burst, tokens + tokens_to_add)

            if tokens >= 1:
                # Consume a token
                bucket["tokens"] = tokens - 1
                bucket["last_refill"] = now
                cache.set(cache_key, bucket, timeout=window * 2)
                return True

            # No tokens available — calculate wait time
            self.wait_time = (1 - tokens) / refill_rate
            return False
        except Exception:
            return True

    def wait(self):
        """Return seconds until next token is available (for Retry-After header)."""
        return getattr(self, "wait_time", None)
