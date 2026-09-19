import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from django.db import connection
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


request_id_context = ContextVar("request_id", default="")

_SAFE_TOKEN = re.compile(r"[^a-zA-Z0-9_.:-]+")
_SAFE_STRING_FIELDS = (
    "scope",
    "method",
    "route",
    "result",
    "operation",
    "object_type",
    "from_state",
    "to_state",
    "code",
)
_SAFE_INTEGER_FIELDS = ("status_code", "duration_ms", "object_id")


def _safe_token(value, *, fallback="unknown", limit=80):
    normalized = _SAFE_TOKEN.sub("_", str(value or "")).strip("_.:-")
    return (normalized or fallback)[:limit]


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        request = getattr(record, "request", None)
        if request is not None:
            record.method = getattr(request, "method", "")
            match = getattr(request, "resolver_match", None)
            record.route = getattr(match, "view_name", "") or "unresolved"
            if not getattr(record, "request_id", ""):
                record.request_id = getattr(request, "request_id", "")
        if not getattr(record, "request_id", ""):
            record.request_id = request_id_context.get()
        if not getattr(record, "event", ""):
            if record.name.startswith("django.security"):
                record.event = "django_security_rejection"
            elif record.name in {"django.request", "django.server"}:
                record.event = "django_http_response"
        return True


class SafeJsonFormatter(logging.Formatter):
    """Serialize an allow-list only; never serialize record.msg or record.args."""

    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": _safe_token(record.name, limit=100),
            "event": _safe_token(getattr(record, "event", "application_log")),
        }
        request_id = str(getattr(record, "request_id", "") or "")
        try:
            payload["request_id"] = str(uuid.UUID(request_id))
        except (ValueError, TypeError, AttributeError):
            pass

        for field in _SAFE_STRING_FIELDS:
            value = getattr(record, field, None)
            if value not in (None, ""):
                payload[field] = _safe_token(value)
        for field in _SAFE_INTEGER_FIELDS:
            value = getattr(record, field, None)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                payload[field] = max(0, int(value))

        if record.exc_info and record.exc_info[0]:
            payload["exception_type"] = _safe_token(record.exc_info[0].__name__)
        elif getattr(record, "exception_type", ""):
            payload["exception_type"] = _safe_token(record.exception_type)
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


request_logger = logging.getLogger("buglessfit.requests")
health_logger = logging.getLogger("buglessfit.health")


class RequestMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())
        request.request_id = request_id
        context_token = request_id_context.set(request_id)
        started = time.monotonic()
        try:
            response = self.get_response(request)
        except Exception as error:
            request_logger.warning(
                "Request failed.",
                extra={
                    "event": "request_failed",
                    "method": request.method,
                    "route": self._route_name(request),
                    "status_code": 500,
                    "duration_ms": self._duration_ms(started),
                    "exception_type": type(error).__name__,
                },
            )
            raise
        else:
            response["X-Request-ID"] = request_id
            log = request_logger.warning if response.status_code >= 500 else request_logger.info
            log(
                "Request completed.",
                extra={
                    "event": "request_completed",
                    "method": request.method,
                    "route": self._route_name(request),
                    "status_code": response.status_code,
                    "duration_ms": self._duration_ms(started),
                },
            )
            return response
        finally:
            request_id_context.reset(context_token)

    @staticmethod
    def _duration_ms(started):
        return max(0, round((time.monotonic() - started) * 1000))

    @staticmethod
    def _route_name(request):
        match = getattr(request, "resolver_match", None)
        return getattr(match, "view_name", "") or "unresolved"


@require_GET
@never_cache
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError as error:
        health_logger.warning(
            "Database health check failed.",
            extra={
                "event": "health_check_failed",
                "result": "database_unavailable",
                "exception_type": type(error).__name__,
            },
        )
        return JsonResponse(
            {"ok": False, "database": "unavailable"},
            status=503,
        )
    return JsonResponse({"ok": True, "database": "ok"})
