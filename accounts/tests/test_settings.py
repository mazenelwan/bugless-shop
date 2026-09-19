import os
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from buglessfit import settings as project_settings


class EnvironmentSettingsTests(SimpleTestCase):
    def test_boolean_environment_values_are_strict(self):
        with patch.dict(os.environ, {"BUGLESS_TEST_BOOLEAN": "maybe"}):
            with self.assertRaises(ImproperlyConfigured):
                project_settings.env_bool("BUGLESS_TEST_BOOLEAN")

    def test_postgresql_url_is_decoded_and_preserves_driver_options(self):
        config = project_settings.database_from_url(
            "postgresql://shop%40user:p%2Fword@db.example:5433/bugless%20fit"
            "?sslmode=require&conn_max_age=120"
        )

        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["NAME"], "bugless fit")
        self.assertEqual(config["USER"], "shop@user")
        self.assertEqual(config["PASSWORD"], "p/word")
        self.assertEqual(config["HOST"], "db.example")
        self.assertEqual(config["PORT"], 5433)
        self.assertEqual(config["CONN_MAX_AGE"], 120)
        self.assertEqual(config["OPTIONS"], {"sslmode": "require"})
        self.assertTrue(config["CONN_HEALTH_CHECKS"])

    def test_invalid_database_connection_age_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            project_settings.database_from_url(
                "postgresql://user:password@localhost/database?conn_max_age=-1"
            )

    def test_nonnegative_integer_parser_rejects_invalid_values(self):
        for value in ("not-a-number", "-1", None):
            with self.subTest(value=value):
                with self.assertRaises(ImproperlyConfigured):
                    project_settings.parse_nonnegative_int("TEST_SETTING", value)
