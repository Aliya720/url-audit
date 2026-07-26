# Custom Exception Handler + Error Catalog — TRD §5
# Coerces ALL errors to: {success, request_id, error: {code, message}, timestamp}
# Sentry only gets genuinely unhandled exceptions (not expected error codes)

import logging
from datetime import datetime, timezone

from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .middleware import get_current_request_id

logger = logging.getLogger("checks")


# ---- Custom API Exceptions (TRD §5 Error Code Catalog) ----


class InvalidURL(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Malformed URL or unsupported scheme."
    default_code = "INVALID_URL"


class URLNotAllowed(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "URL resolves to a private or internal address."
    default_code = "URL_NOT_ALLOWED"


class IntervalTooShort(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Monitor interval is below the configured minimum."
    default_code = "INTERVAL_TOO_SHORT"


class AuditNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Audit not found."
    default_code = "AUDIT_NOT_FOUND"


class MonitorNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Monitor not found."
    default_code = "MONITOR_NOT_FOUND"


class RateLimited(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Too many requests."
    default_code = "RATE_LIMITED"


class TargetUnreachable(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Target site is unreachable."
    default_code = "TARGET_UNREACHABLE"


class TargetTimeout(APIException):
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_detail = "Target site timed out."
    default_code = "TARGET_TIMEOUT"


class ServiceBusy(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service is at capacity. Try again shortly."
    default_code = "SERVICE_BUSY"


class InternalError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "An internal error occurred."
    default_code = "INTERNAL_ERROR"


def _build_error_response(code, message, http_status, retry_after=None):
    """Build a structured error response per TRD §5."""
    request_id = get_current_request_id()
    body = {
        "success": False,
        "request_id": request_id,
        "error": {
            "code": code,
            "message": str(message),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = Response(body, status=http_status)
    if retry_after is not None:
        response["Retry-After"] = str(int(retry_after))
    return response


def pulsewatch_exception_handler(exc, context):
    """
    DRF custom exception handler — TRD §5.
    Coerces ALL errors into the documented shape so Django's default HTML
    error pages never leak through.
    """
    request_id = get_current_request_id()

    # Handle DRF Throttled specially to extract Retry-After
    if isinstance(exc, Throttled):
        logger.warning(
            "rate_limited",
            extra={
                "request_id": request_id,
                "error_code": "RATE_LIMITED",
                "retry_after": exc.wait,
            },
        )
        return _build_error_response(
            "RATE_LIMITED",
            "Too many requests. Please slow down.",
            status.HTTP_429_TOO_MANY_REQUESTS,
            retry_after=exc.wait,
        )

    # Handle DRF ValidationError (from serializer validation)
    if isinstance(exc, ValidationError):
        logger.warning(
            "validation_error",
            extra={
                "request_id": request_id,
                "error_code": "INVALID_URL",
                "detail": str(exc.detail),
            },
        )
        if isinstance(exc.detail, dict):
            messages = []
            for field, errors in exc.detail.items():
                for error in errors:
                    messages.append(f"{field}: {error}")
            message = "; ".join(messages)
        elif isinstance(exc.detail, list):
            message = "; ".join(str(e) for e in exc.detail)
        else:
            message = str(exc.detail)
        return _build_error_response(
            "INVALID_URL", message, status.HTTP_400_BAD_REQUEST
        )

    # Handle our custom API exceptions
    if isinstance(exc, APIException):
        code = getattr(exc, "default_code", "INTERNAL_ERROR")
        logger.warning(
            "api_error",
            extra={
                "request_id": request_id,
                "error_code": code,
                "detail": str(exc.detail),
            },
        )
        return _build_error_response(code, exc.detail, exc.status_code)

    # Fallback: let DRF handle it first
    response = exception_handler(exc, context)
    if response is not None:
        return _build_error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
            response.status_code,
        )

    # Genuinely unhandled — this is what Sentry should capture
    logger.exception(
        "unhandled_exception",
        extra={
            "request_id": request_id,
            "error_code": "INTERNAL_ERROR",
            "exception_type": type(exc).__name__,
        },
    )
    return _build_error_response(
        "INTERNAL_ERROR",
        "Something went wrong on our end.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
