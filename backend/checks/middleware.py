# Request ID Middleware — TRD §9
# Generates/extracts request_id, stores via contextvars for structured logging

import contextvars
import logging
import secrets
import time

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("checks")

# Context variable for request_id — accessible from any code in the request lifecycle
# without threading it through function signatures (TRD §9)
request_id_var = contextvars.ContextVar("request_id", default=None)


def generate_request_id():
    """Generate a prefixed request ID: req_ + 8 hex chars."""
    return f"req_{secrets.token_hex(8)}"


def get_current_request_id():
    """Retrieve the current request ID from context."""
    return request_id_var.get(None)


class RequestIDMiddleware(MiddlewareMixin):
    """
    Middleware that generates or extracts a request_id for every request.
    - Passthrough: if X-Request-Id header is present, reuse it
    - Otherwise: generate a new req_XXXX ID
    - Stores in contextvars so all downstream code (views, utils, logging) can access it
    - Logs request start and outcome with structured fields (TRD §9)
    """

    def process_request(self, request):
        # Extract or generate request_id
        incoming_id = request.META.get("HTTP_X_REQUEST_ID")
        rid = incoming_id if incoming_id else generate_request_id()
        request_id_var.set(rid)
        request.request_id = rid
        request._start_time = time.monotonic()

        logger.info(
            "request_started",
            extra={
                "request_id": rid,
                "method": request.method,
                "path": request.path,
                "client_key": request.META.get("HTTP_X_CLIENT_KEY", "anonymous"),
            },
        )

    def process_response(self, request, response):
        rid = getattr(request, "request_id", None)
        if rid:
            response["X-Request-Id"] = rid

        duration_ms = None
        if hasattr(request, "_start_time"):
            duration_ms = round((time.monotonic() - request._start_time) * 1000, 2)

        logger.info(
            "request_completed",
            extra={
                "request_id": rid,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_key": request.META.get("HTTP_X_CLIENT_KEY", "anonymous"),
            },
        )

        return response
