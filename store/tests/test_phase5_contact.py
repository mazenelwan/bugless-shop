import uuid
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from store.models import ContactMessage, ContactMessageEvent


class ContactSubmissionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("store:contact")

    def tearDown(self):
        cache.clear()

    def payload(self, **overrides):
        data = {
            "submission_id": str(uuid.uuid4()),
            "name": "  Ada Lovelace  ",
            "email": "  ADA@Example.COM  ",
            "phone": "+20 (100) 000-0000",
            "subject": "  Sizing question  ",
            "message": "  Please help with sizing.  ",
            "website": "",
        }
        data.update(overrides)
        return data

    def test_get_renders_uuid_idempotency_field(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        submission_id = response.context["contact_submission_id"]
        self.assertContains(response, f'value="{submission_id}"')
        self.assertContains(response, 'name="website"')

    def test_valid_submission_normalizes_persists_audits_and_uses_prg(self):
        response = self.client.post(self.url, self.payload())

        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        message = ContactMessage.objects.get()
        self.assertEqual(message.name, "Ada Lovelace")
        self.assertEqual(message.email, "ada@example.com")
        self.assertEqual(message.phone, "+20 (100) 000-0000")
        self.assertEqual(message.subject, "Sizing question")
        self.assertEqual(message.message, "Please help with sizing.")
        self.assertEqual(len(message.request_fingerprint), 64)
        event = message.events.get()
        self.assertEqual(event.event_type, ContactMessageEvent.EventType.SUBMITTED)

        success = self.client.get(self.url)
        self.assertContains(success, "Your message has been sent successfully")

    def test_invalid_fields_bind_safe_errors_and_do_not_persist(self):
        response = self.client.post(
            self.url,
            self.payload(
                name=" ",
                email="not-an-email",
                phone="123",
                message=" ",
                subject="<script>alert(1)</script>",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, "Enter a valid email address")
        self.assertContains(response, "Enter a phone number containing 7 to 15 digits")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_honeypot_rejects_without_persistence(self):
        response = self.client.post(self.url, self.payload(website="https://spam.test"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "We could not send your message")
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_identical_submission_id_replays_without_second_write_or_event(self):
        payload = self.payload()

        first = self.client.post(self.url, payload)
        second = self.client.post(self.url, payload)

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(ContactMessageEvent.objects.count(), 1)

    def test_changed_reuse_of_submission_id_conflicts(self):
        payload = self.payload()
        self.client.post(self.url, payload)

        response = self.client.post(self.url, {**payload, "message": "Different message"})

        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "already used for a different message", status_code=409)
        self.assertEqual(ContactMessage.objects.count(), 1)

    @override_settings(CONTACT_RATE_LIMIT=1, CONTACT_RATE_LIMIT_WINDOW=300)
    def test_rate_limit_rejects_new_submission_without_mutation(self):
        first = self.client.post(self.url, self.payload())
        second = self.client.post(self.url, self.payload(email="other@example.com"))

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 429)
        self.assertContains(response=second, text="Too many messages", status_code=429)
        self.assertEqual(ContactMessage.objects.count(), 1)

    @patch("store.services.contact.cache.add", return_value=True)
    def test_rate_limit_cache_keys_do_not_contain_raw_identifiers(self, cache_add):
        response = self.client.post(self.url, self.payload())

        self.assertEqual(response.status_code, 302)
        keys = [call.args[0] for call in cache_add.call_args_list]
        self.assertEqual(len(keys), 2)
        self.assertTrue(all(key.startswith("buglessfit:contact:") for key in keys))
        self.assertTrue(all("ada@example.com" not in key for key in keys))
        self.assertTrue(all("127.0.0.1" not in key for key in keys))

    @override_settings(CONTACT_MAX_BODY_BYTES=200)
    def test_oversize_body_is_rejected_without_parsing_or_persistence(self):
        response = self.client.post(self.url, self.payload(message="x" * 500))

        self.assertEqual(response.status_code, 413)
        self.assertContains(response, "message is too large", status_code=413)
        self.assertEqual(ContactMessage.objects.count(), 0)

    @override_settings(
        CONTACT_NOTIFICATION_EMAIL="staff@example.com",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_notification_is_sent_after_commit_and_audited(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, self.payload())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["staff@example.com"])
        self.assertTrue(
            ContactMessageEvent.objects.filter(
                event_type=ContactMessageEvent.EventType.NOTIFICATION_SENT
            ).exists()
        )

    @override_settings(CONTACT_NOTIFICATION_EMAIL="staff@example.com")
    @patch("store.services.contact.send_mail", side_effect=RuntimeError("provider down"))
    def test_notification_failure_does_not_rollback_message(self, mocked_send):
        with self.assertLogs("store.services.contact", level="WARNING") as logs:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(self.url, self.payload())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(mocked_send.call_count, 1)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertNotIn("Please help with sizing", " ".join(logs.output))
        self.assertNotIn("ada@example.com", " ".join(logs.output).casefold())
        self.assertTrue(
            ContactMessageEvent.objects.filter(
                event_type=ContactMessageEvent.EventType.NOTIFICATION_FAILED
            ).exists()
        )

    def test_csrf_is_required(self):
        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.post(self.url, self.payload())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_non_get_or_post_method_is_rejected(self):
        response = self.client.put(self.url, data="")

        self.assertEqual(response.status_code, 405)
