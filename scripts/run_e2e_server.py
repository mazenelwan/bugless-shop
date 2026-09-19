import os
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_ROOT = REPOSITORY_ROOT / ".phase6"
DATABASE_PATH = RUNTIME_ROOT / "e2e.sqlite3"

RUNTIME_ROOT.mkdir(exist_ok=True)
os.environ.pop("DATABASE_URL", None)
os.environ.update(
    {
        "DJANGO_SETTINGS_MODULE": "buglessfit.settings",
        "SQLITE_DATABASE_PATH": str(DATABASE_PATH),
        "SECRET_KEY": "phase6-local-browser-test-key",
        "DEBUG": "True",
        "ALLOWED_HOSTS": "127.0.0.1,localhost",
        "ACCOUNT_LOGIN_RATE_LIMIT": "0",
        "ACCOUNT_REGISTRATION_RATE_LIMIT": "0",
        "ACCOUNT_PASSWORD_RESET_RATE_LIMIT": "0",
        "CONTACT_RATE_LIMIT": "0",
        "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
        "APP_LOG_LEVEL": "WARNING",
    }
)

sys.path.insert(0, str(REPOSITORY_ROOT))

import django  # noqa: E402


django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.auth.models import Group  # noqa: E402
from django.core.management import call_command  # noqa: E402


call_command("migrate", interactive=False, verbosity=0)
call_command("flush", interactive=False, verbosity=0)
call_command("seed_catalog", verbosity=0)
call_command("configure_staff_roles", verbosity=0)

manager = get_user_model().objects.create_user(
    email="manager@e2e.local",
    password="Phase6-manager-password-829!",
    first_name="Local",
    last_name="Manager",
    is_staff=True,
)
manager.groups.add(Group.objects.get(name="Store Manager"))

call_command(
    "runserver",
    "127.0.0.1:8010",
    use_reloader=False,
    verbosity=1,
)
