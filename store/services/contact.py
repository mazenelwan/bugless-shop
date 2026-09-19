import hashlib
import json
import logging
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.utils.crypto import salted_hmac

from store.models import ContactMessage, ContactMessageEvent


logger = logging.getLogger(__name__)


class ContactSubmissionError(Exception):
    def __init__(self, message, *, code, status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


class ContactRateLimited(ContactSubmissionError):
    def __init__(self):
        super().__init__(
            "Too many messages were submitted. Please wait and try again.",
            code="rate_limited",
            status=429,
        )


class ContactSubmissionConflict(ContactSubmissionError):
    def __init__(self):
        super().__init__(
            "This form was already used for a different message. Refresh the page and try again.",
            code="submission_conflict",
            status=409,
        )


@dataclass(frozen=True)
class ContactSubmissionResult:
    message: ContactMessage
    created: bool


def contact_fingerprint(cleaned_data):
    semantic_data = {
        field: cleaned_data[field]
        for field in ("name", "email", "phone", "subject", "message")
    }
    encoded = json.dumps(
        semantic_data,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _rate_limit_key(scope, identity):
    digest = salted_hmac("store.contact-rate-limit", f"{scope}|{identity}").hexdigest()
    return f"buglessfit:contact:{scope}:{digest}"


def _counter_exceeded(key, limit, window):
    if cache.add(key, 1, timeout=window):
        return False
    return cache.incr(key) > limit


def contact_rate_limited(request, email):
    limit = settings.CONTACT_RATE_LIMIT
    if limit <= 0 or settings.CONTACT_RATE_LIMIT_WINDOW <= 0:
        return False

    remote_address = str(request.META.get("REMOTE_ADDR") or "unknown")
    identities = (
        ("peer", remote_address),
        ("email", email.casefold()),
    )
    try:
        limited = any(
            _counter_exceeded(
                _rate_limit_key(scope, identity),
                limit,
                settings.CONTACT_RATE_LIMIT_WINDOW,
            )
            for scope, identity in identities
        )
        if limited:
            logger.warning(
                "Contact rate limit exceeded.",
                extra={"event": "contact_rate_limit_exceeded", "scope": "submission"},
            )
        return limited
    except Exception:
        logger.warning(
            "Contact rate-limit cache failed.",
            exc_info=True,
            extra={"event": "contact_rate_limit_cache_failed", "scope": "submission"},
        )
        return False


def _record_notification_event(message_id, event_type):
    try:
        ContactMessageEvent.objects.create(
            contact_message_id=message_id,
            event_type=event_type,
        )
    except Exception:
        logger.warning(
            "Could not record contact notification audit event for message %s.",
            message_id,
            exc_info=True,
            extra={
                "event": "contact_notification_audit_failed",
                "object_type": "contact_message",
                "object_id": message_id,
            },
        )


def send_staff_contact_notification(message_id):
    recipient = settings.CONTACT_NOTIFICATION_EMAIL
    if not recipient:
        return

    try:
        message = ContactMessage.objects.get(pk=message_id)
        body = "\n".join(
            (
                f"Contact message: {message.pk}",
                f"Name: {message.name}",
                f"Email: {message.email}",
                f"Phone: {message.phone or '-'}",
                f"Subject: {message.subject or '-'}",
                "",
                message.message,
            )
        )
        send_mail(
            subject=f"New Bugless Fit contact message #{message.pk}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as error:
        _record_notification_event(
            message_id,
            ContactMessageEvent.EventType.NOTIFICATION_FAILED,
        )
        logger.warning(
            "Contact notification failed for message %s (%s).",
            message_id,
            type(error).__name__,
            extra={
                "event": "contact_notification_failed",
                "object_type": "contact_message",
                "object_id": message_id,
                "exception_type": type(error).__name__,
            },
        )
        return

    _record_notification_event(
        message_id,
        ContactMessageEvent.EventType.NOTIFICATION_SENT,
    )
    logger.info(
        "Contact notification sent.",
        extra={
            "event": "contact_notification_sent",
            "object_type": "contact_message",
            "object_id": message_id,
        },
    )


def submit_contact(cleaned_data, request):
    submission_id = cleaned_data["submission_id"]
    fingerprint = contact_fingerprint(cleaned_data)
    existing = ContactMessage.objects.filter(submission_id=submission_id).first()
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            logger.warning(
                "Contact idempotency conflict.",
                extra={
                    "event": "contact_idempotency_conflict",
                    "object_type": "contact_message",
                    "object_id": existing.pk,
                },
            )
            raise ContactSubmissionConflict
        logger.info(
            "Contact submission replayed.",
            extra={
                "event": "contact_submission_replayed",
                "object_type": "contact_message",
                "object_id": existing.pk,
            },
        )
        return ContactSubmissionResult(message=existing, created=False)

    if contact_rate_limited(request, cleaned_data["email"]):
        raise ContactRateLimited

    defaults = {
        field: cleaned_data[field]
        for field in ("name", "email", "phone", "subject", "message")
    }
    defaults["request_fingerprint"] = fingerprint

    with transaction.atomic():
        message, created = ContactMessage.objects.get_or_create(
            submission_id=submission_id,
            defaults=defaults,
        )
        if not created and message.request_fingerprint != fingerprint:
            logger.warning(
                "Contact idempotency conflict.",
                extra={
                    "event": "contact_idempotency_conflict",
                    "object_type": "contact_message",
                    "object_id": message.pk,
                },
            )
            raise ContactSubmissionConflict
        if created:
            ContactMessageEvent.objects.create(
                contact_message=message,
                event_type=ContactMessageEvent.EventType.SUBMITTED,
            )
            transaction.on_commit(
                lambda message_id=message.pk: send_staff_contact_notification(message_id),
                robust=True,
            )
            transaction.on_commit(
                lambda message_id=message.pk: logger.info(
                    "Contact submission created.",
                    extra={
                        "event": "contact_submission_created",
                        "object_type": "contact_message",
                        "object_id": message_id,
                    },
                ),
                robust=True,
            )
        else:
            logger.info(
                "Contact submission replayed.",
                extra={
                    "event": "contact_submission_replayed",
                    "object_type": "contact_message",
                    "object_id": message.pk,
                },
            )

    return ContactSubmissionResult(message=message, created=created)
