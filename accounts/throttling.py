import logging

from django.conf import settings
from django.core.cache import cache
from django.utils.crypto import salted_hmac

from .managers import normalize_customer_email


logger = logging.getLogger(__name__)


def rate_limit_key(request, scope, identity=""):
    remote_address = str(request.META.get("REMOTE_ADDR") or "unknown")
    normalized_identity = normalize_customer_email(identity) if identity else ""
    fingerprint = f"{scope}|{remote_address}|{normalized_identity}"
    digest = salted_hmac("accounts.rate-limit", fingerprint).hexdigest()
    return f"buglessfit:accounts:{scope}:{digest}"


def consume_rate_limit(request, scope, identity, limit, window):
    if limit <= 0:
        return False

    key = rate_limit_key(request, scope, identity)
    try:
        if cache.add(key, 1, timeout=window):
            return False
        attempts = cache.incr(key)
    except Exception:
        logger.warning(
            "Authentication rate-limit cache failed for scope %s.",
            scope,
            exc_info=True,
            extra={"event": "auth_rate_limit_cache_failed", "scope": scope},
        )
        return False
    limited = attempts > limit
    if limited:
        logger.warning(
            "Authentication rate limit exceeded.",
            extra={"event": "auth_rate_limit_exceeded", "scope": scope},
        )
    return limited


def clear_rate_limit(request, scope, identity=""):
    try:
        cache.delete(rate_limit_key(request, scope, identity))
    except Exception:
        logger.warning(
            "Authentication rate-limit cache clear failed for scope %s.",
            scope,
            exc_info=True,
            extra={"event": "auth_rate_limit_cache_clear_failed", "scope": scope},
        )


def configured_limit(name):
    return getattr(settings, name)
