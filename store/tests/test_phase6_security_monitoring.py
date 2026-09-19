import json
import logging
import re
from io import StringIO
from unittest.mock import patch

from django.db.utils import OperationalError
from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from buglessfit.monitoring import RequestContextFilter, SafeJsonFormatter


class SecurityHeaderTests(TestCase):
    def test_public_and_error_responses_receive_security_headers(self):
        for path in (reverse("store:home"), "/missing-page/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                policy = response["Content-Security-Policy"]
                self.assertIn("default-src 'self'", policy)
                self.assertIn("object-src 'none'", policy)
                self.assertIn("frame-ancestors 'none'", policy)
                self.assertEqual(
                    response["Permissions-Policy"],
                    "camera=(), geolocation=(), microphone=()",
                )
                self.assertEqual(response["X-Frame-Options"], "DENY")
                self.assertEqual(response["X-Content-Type-Options"], "nosniff")
                self.assertEqual(response["Referrer-Policy"], "same-origin")
                self.assertEqual(response["Cross-Origin-Opener-Policy"], "same-origin")
                self.assertNotIn("'unsafe-inline'", policy.split("script-src", 1)[1].split(";", 1)[0])

    def test_request_id_is_generated_and_untrusted_header_is_not_reflected(self):
        supplied = "attacker-controlled\r\nX-Injected: true"
        response = self.client.get(
            reverse("store:about"),
            HTTP_X_REQUEST_ID=supplied,
        )

        generated = response["X-Request-ID"]
        self.assertRegex(
            generated,
            re.compile(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
            ),
        )
        self.assertNotEqual(generated, supplied)


class HealthCheckTests(TestCase):
    def test_health_check_is_database_aware_and_not_cached(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True, "database": "ok"})
        self.assertIn("no-cache", response["Cache-Control"])
        self.assertIn("X-Request-ID", response)

    def test_health_check_returns_generic_failure_without_exception_details(self):
        with patch(
            "buglessfit.monitoring.connection.cursor",
            side_effect=OperationalError("password=secret database host leaked"),
        ):
            response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 503)
        body = response.content.decode()
        self.assertEqual(response.json(), {"ok": False, "database": "unavailable"})
        self.assertNotIn("secret", body)
        self.assertNotIn("host", body)

    def test_health_check_rejects_unsafe_methods(self):
        response = self.client.post(reverse("health"))

        self.assertEqual(response.status_code, 405)


class ThreatBoundaryTests(TestCase):
    def test_sensitive_and_source_paths_are_not_public_routes(self):
        for path in (
            "/frontend/index.html",
            "/templates/store/checkout.html",
            "/db.sqlite3",
            "/.env",
            "/requirements.txt",
            "/static/home.css",
            "/static/product-data.js",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)

    def test_checkout_transport_rejects_wrong_method_and_media_type(self):
        create_url = reverse("store:create_order")
        quote_url = reverse("store:quote_order")

        self.assertEqual(self.client.get(create_url).status_code, 405)
        self.assertEqual(self.client.get(quote_url).status_code, 405)
        response = self.client.post(create_url, data="{}", content_type="text/plain")
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["error"]["code"], "invalid_content_type")

    def test_csrf_is_enforced_at_each_anonymous_write_boundary(self):
        csrf_client = Client(enforce_csrf_checks=True)

        self.assertEqual(
            csrf_client.post(
                reverse("store:create_order"),
                data="{}",
                content_type="application/json",
            ).status_code,
            403,
        )
        self.assertEqual(
            csrf_client.post(reverse("store:contact"), data={}).status_code,
            403,
        )
        self.assertEqual(
            csrf_client.post(reverse("accounts:register"), data={}).status_code,
            403,
        )

    def test_session_and_csrf_cookies_use_safe_local_flags(self):
        password = "Cookie-test-password-829!"
        user = get_user_model().objects.create_user(
            email="cookie-test@example.com",
            password=password,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": user.email, "password": password},
        )
        self.assertEqual(response.status_code, 302)
        self.client.get(reverse("store:contact"))

        session_cookie = self.client.cookies[settings.SESSION_COOKIE_NAME]
        csrf_cookie = self.client.cookies[settings.CSRF_COOKIE_NAME]
        self.assertTrue(session_cookie["httponly"])
        self.assertEqual(session_cookie["samesite"], "Lax")
        self.assertTrue(csrf_cookie["httponly"])
        self.assertEqual(csrf_cookie["samesite"], "Lax")

    def test_unapproved_host_is_rejected(self):
        response = self.client.get(reverse("store:home"), HTTP_HOST="evil.example")

        self.assertEqual(response.status_code, 400)


class SafeLoggingTests(SimpleTestCase):
    def test_formatter_uses_allow_list_and_discards_message_and_unknown_extras(self):
        record = logging.LogRecord(
            name="store.services.checkout",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg="password=%s token=%s email=learner@example.com",
            args=("SuperSecret!", "private-token"),
            exc_info=None,
        )
        record.event = "checkout_rejected"
        record.code = "invalid_payload"
        record.address = "1 Private Street"
        record.message_body = "do not log this"
        record.request_id = "f70a6d4d-296f-4eb2-88c6-0bdd16094924"

        serialized = SafeJsonFormatter().format(record)
        payload = json.loads(serialized)

        self.assertEqual(payload["event"], "checkout_rejected")
        self.assertEqual(payload["code"], "invalid_payload")
        self.assertEqual(
            payload["request_id"],
            "f70a6d4d-296f-4eb2-88c6-0bdd16094924",
        )
        for protected in (
            "SuperSecret",
            "private-token",
            "learner@example.com",
            "Private Street",
            "do not log this",
        ):
            self.assertNotIn(protected, serialized)

    def test_django_response_log_cannot_serialize_a_private_url(self):
        record = logging.LogRecord(
            name="django.server",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg='"GET /order/BF-PRIVATE/private-token/?email=user@example.com" 404',
            args=(),
            exc_info=None,
        )
        record.status_code = 404
        RequestContextFilter().filter(record)

        serialized = SafeJsonFormatter().format(record)

        self.assertIn('"event":"django_http_response"', serialized)
        self.assertIn('"status_code":404', serialized)
        self.assertNotIn("BF-PRIVATE", serialized)
        self.assertNotIn("private-token", serialized)
        self.assertNotIn("user@example.com", serialized)

    def test_request_log_uses_route_name_not_query_string(self):
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(RequestContextFilter())
        handler.setFormatter(SafeJsonFormatter())
        logger = logging.getLogger("buglessfit.requests")
        previous_handlers = logger.handlers[:]
        previous_level = logger.level
        previous_propagate = logger.propagate
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False
        try:
            Client().get("/about/?q=learner%40example.com&token=private-token")
        finally:
            logger.handlers = previous_handlers
            logger.setLevel(previous_level)
            logger.propagate = previous_propagate

        serialized = stream.getvalue()
        payload = json.loads(serialized)
        self.assertEqual(payload["route"], "store:about")
        self.assertNotIn("learner@example.com", serialized)
        self.assertNotIn("private-token", serialized)
