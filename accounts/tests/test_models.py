from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, transaction
from django.test import TestCase


class UserModelTests(TestCase):
    def test_email_is_the_login_identity_and_is_normalized(self):
        User = get_user_model()

        user = User.objects.create_user(
            email="  Ada@Example.COM ",
            password="Useful-test-password-938!",
        )

        self.assertEqual(user.email, "ada@example.com")
        self.assertEqual(User.USERNAME_FIELD, "email")
        with self.assertRaises(FieldDoesNotExist):
            User._meta.get_field("username")
        self.assertTrue(user.check_password("Useful-test-password-938!"))

    def test_email_uniqueness_is_case_insensitive(self):
        User = get_user_model()
        User.objects.create_user("ada@example.com", "Useful-test-password-938!")

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("ADA@EXAMPLE.COM", "Another-password-742!")

    def test_superuser_factory_enforces_staff_permissions(self):
        User = get_user_model()

        user = User.objects.create_superuser(
            "admin@example.com",
            "Useful-admin-password-194!",
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
