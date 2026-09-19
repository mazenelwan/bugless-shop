import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from accounts.throttling import rate_limit_key
from store.models import Order


class AccountFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.User = get_user_model()

    def tearDown(self):
        cache.clear()

    def create_user(self, email="ada@example.com", password="Strong-pass-728!"):
        return self.User.objects.create_user(email=email, password=password)

    def registration_payload(self, **overrides):
        values = {
            "email": "  ADA@Example.COM ",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "password1": "Strong-pass-728!",
            "password2": "Strong-pass-728!",
        }
        values.update(overrides)
        return values

    def make_order(self, email, customer=None):
        return Order.objects.create(
            customer=customer,
            customer_name="Ada Lovelace",
            email=email,
            phone="01000000000",
            address="Cairo",
        )

    def test_registration_normalizes_email_signs_in_and_uses_safe_default(self):
        response = self.client.post(
            reverse("accounts:register"),
            self.registration_payload(),
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        user = self.User.objects.get()
        self.assertEqual(user.email, "ada@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_registration_rejects_case_insensitive_duplicate(self):
        self.create_user("ada@example.com")

        response = self.client.post(
            reverse("accounts:register"),
            self.registration_payload(email="ADA@EXAMPLE.COM"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")
        self.assertEqual(self.User.objects.count(), 1)

    def test_registration_ignores_an_external_next_target(self):
        response = self.client.post(
            reverse("accounts:register"),
            self.registration_payload(next="https://attacker.example/steal"),
        )

        self.assertRedirects(response, reverse("accounts:profile"))

    def test_login_normalizes_email_and_rejects_external_next(self):
        user = self.create_user()

        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "ADA@EXAMPLE.COM",
                "password": "Strong-pass-728!",
                "next": "https://attacker.example/steal",
            },
        )

        self.assertRedirects(response, reverse("store:home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_logout_is_post_only_and_clears_authentication(self):
        user = self.create_user()
        self.client.force_login(user)

        self.assertEqual(
            self.client.get(reverse("accounts:logout")).status_code,
            405,
        )
        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("store:home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_requires_login_and_normalizes_updates(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertRedirects(
            response,
            f'{reverse("accounts:login")}?next={reverse("accounts:profile")}',
        )

        user = self.create_user()
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "email": "  NEW@Example.COM ",
                "first_name": "New",
                "last_name": "Name",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.get_full_name(), "New Name")

    def test_profile_rejects_another_users_email(self):
        user = self.create_user()
        self.create_user("other@example.com", "Other-pass-928!")
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:profile"),
            {"email": "OTHER@EXAMPLE.COM", "first_name": "", "last_name": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")
        user.refresh_from_db()
        self.assertEqual(user.email, "ada@example.com")

    def test_password_change_keeps_the_current_session_authenticated(self):
        user = self.create_user()
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "Strong-pass-728!",
                "new_password1": "Changed-pass-829!",
                "new_password2": "Changed-pass-829!",
            },
        )

        self.assertRedirects(response, reverse("accounts:password_change_done"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        user.refresh_from_db()
        self.assertTrue(user.check_password("Changed-pass-829!"))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_password_reset_is_enumeration_safe_and_single_use(self):
        user = self.create_user()
        reset_url = reverse("accounts:password_reset")

        existing = self.client.post(reset_url, {"email": "ADA@EXAMPLE.COM"})
        self.assertRedirects(existing, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        match = re.search(r"http://testserver(?P<path>/accounts/reset/\S+)", mail.outbox[0].body)
        self.assertIsNotNone(match)

        token_response = self.client.get(match.group("path"))
        self.assertEqual(token_response.status_code, 302)
        set_password_url = token_response.headers["Location"]
        completed = self.client.post(
            set_password_url,
            {
                "new_password1": "Reset-pass-930!",
                "new_password2": "Reset-pass-930!",
            },
        )
        self.assertRedirects(
            completed,
            reverse("accounts:password_reset_complete"),
        )
        user.refresh_from_db()
        self.assertTrue(user.check_password("Reset-pass-930!"))
        self.assertContains(self.client.get(match.group("path")), "invalid or has already been used")

        cache.clear()
        missing = self.client.post(reset_url, {"email": "missing@example.com"})
        self.assertRedirects(missing, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)

    def test_account_order_pages_are_owner_filtered(self):
        owner = self.create_user()
        other = self.create_user("other@example.com", "Other-pass-928!")
        owned_order = self.make_order(owner.email, owner)
        other_order = self.make_order(other.email, other)
        guest_order = self.make_order(owner.email)
        self.client.force_login(owner)

        response = self.client.get(reverse("accounts:order_list"))
        self.assertContains(response, owned_order.number)
        self.assertNotContains(response, other_order.number)
        self.assertNotContains(response, guest_order.number)
        self.assertEqual(
            self.client.get(
                reverse("accounts:order_detail", args=(owned_order.number,))
            ).status_code,
            200,
        )
        for hidden_order in (other_order, guest_order):
            with self.subTest(order=hidden_order.number):
                self.assertEqual(
                    self.client.get(
                        reverse("accounts:order_detail", args=(hidden_order.number,))
                    ).status_code,
                    404,
                )

    @override_settings(ACCOUNT_LOGIN_RATE_LIMIT=1, ACCOUNT_RATE_LIMIT_WINDOW=300)
    def test_login_rate_limit_returns_429_and_success_clears_the_bucket(self):
        self.create_user()
        login_url = reverse("accounts:login")
        valid = {"username": "ada@example.com", "password": "Strong-pass-728!"}
        invalid = {"username": "ada@example.com", "password": "wrong"}

        self.assertEqual(self.client.post(login_url, valid).status_code, 302)
        self.client.post(reverse("accounts:logout"))
        self.assertEqual(self.client.post(login_url, invalid).status_code, 200)
        limited = self.client.post(login_url, invalid)
        self.assertEqual(limited.status_code, 429)
        self.assertContains(
            limited,
            "Too many attempts. Please try again later.",
            status_code=429,
        )

    def test_rate_limit_cache_key_contains_no_raw_identifier(self):
        request = RequestFactory().post(
            reverse("accounts:login"),
            REMOTE_ADDR="203.0.113.10",
        )
        key = rate_limit_key(request, "login", "ada@example.com")

        self.assertNotIn("ada@example.com", key)
        self.assertNotIn("203.0.113.10", key)

    def test_registration_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse("accounts:register"),
            self.registration_payload(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.User.objects.exists())
