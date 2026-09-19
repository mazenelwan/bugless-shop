import os
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(f"{name} must be a boolean value.")


def env_list(name, default=""):
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


def parse_nonnegative_int(name, raw_value):
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(f"{name} must be a non-negative integer.") from exc
    if value < 0:
        raise ImproperlyConfigured(f"{name} must be a non-negative integer.")
    return value


DEBUG = env_bool("DEBUG", True)
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "unsafe-development-key-change-before-production"
    else:
        raise ImproperlyConfigured("SECRET_KEY is required when DEBUG is false.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts.apps.AccountsConfig",
    "store.apps.StoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "buglessfit.monitoring.RequestMonitoringMiddleware",
    "buglessfit.security.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "buglessfit.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "buglessfit.wsgi.application"


def database_from_url(value):
    parsed = urlparse(value)
    engines = {
        "postgres": "django.db.backends.postgresql",
        "postgresql": "django.db.backends.postgresql",
        "postgresql+psycopg": "django.db.backends.postgresql",
    }
    try:
        engine = engines[parsed.scheme.lower()]
        port = parsed.port or 5432
    except (KeyError, ValueError) as exc:
        raise ImproperlyConfigured("DATABASE_URL must be a valid PostgreSQL URL.") from exc

    if not parsed.hostname or not parsed.path.lstrip("/"):
        raise ImproperlyConfigured("DATABASE_URL must include a host and database name.")

    query_options = dict(parse_qsl(parsed.query, keep_blank_values=False))
    conn_max_age = parse_nonnegative_int(
        "DB_CONN_MAX_AGE",
        query_options.pop("conn_max_age", os.getenv("DB_CONN_MAX_AGE", "60")),
    )
    config = {
        "ENGINE": engine,
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname,
        "PORT": port,
        "CONN_MAX_AGE": conn_max_age,
        "CONN_HEALTH_CHECKS": True,
    }
    if query_options:
        config["OPTIONS"] = query_options
    return config


database_url = os.getenv("DATABASE_URL", "").strip()
if database_url:
    DATABASES = {"default": database_from_url(database_url)}
else:
    sqlite_database_path = os.getenv("SQLITE_DATABASE_PATH", "").strip()
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": Path(sqlite_database_path) if sqlite_database_path else BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
ACCOUNT_LOGIN_RATE_LIMIT = parse_nonnegative_int(
    "ACCOUNT_LOGIN_RATE_LIMIT",
    os.getenv("ACCOUNT_LOGIN_RATE_LIMIT", "10"),
)
ACCOUNT_REGISTRATION_RATE_LIMIT = parse_nonnegative_int(
    "ACCOUNT_REGISTRATION_RATE_LIMIT",
    os.getenv("ACCOUNT_REGISTRATION_RATE_LIMIT", "5"),
)
ACCOUNT_PASSWORD_RESET_RATE_LIMIT = parse_nonnegative_int(
    "ACCOUNT_PASSWORD_RESET_RATE_LIMIT",
    os.getenv("ACCOUNT_PASSWORD_RESET_RATE_LIMIT", "5"),
)
ACCOUNT_RATE_LIMIT_WINDOW = parse_nonnegative_int(
    "ACCOUNT_RATE_LIMIT_WINDOW",
    os.getenv("ACCOUNT_RATE_LIMIT_WINDOW", "300"),
)
CHECKOUT_MAX_BODY_BYTES = parse_nonnegative_int(
    "CHECKOUT_MAX_BODY_BYTES",
    os.getenv("CHECKOUT_MAX_BODY_BYTES", "65536"),
)
CONTACT_MAX_BODY_BYTES = parse_nonnegative_int(
    "CONTACT_MAX_BODY_BYTES",
    os.getenv("CONTACT_MAX_BODY_BYTES", "16384"),
)
CONTACT_RATE_LIMIT = parse_nonnegative_int(
    "CONTACT_RATE_LIMIT",
    os.getenv("CONTACT_RATE_LIMIT", "5"),
)
CONTACT_RATE_LIMIT_WINDOW = parse_nonnegative_int(
    "CONTACT_RATE_LIMIT_WINDOW",
    os.getenv("CONTACT_RATE_LIMIT_WINDOW", "300"),
)
CONTACT_NOTIFICATION_EMAIL = os.getenv("CONTACT_NOTIFICATION_EMAIL", "").strip()
DATA_UPLOAD_MAX_MEMORY_SIZE = CHECKOUT_MAX_BODY_BYTES

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Cairo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Bugless Fit <noreply@localhost>")

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SECURE_HSTS_SECONDS = parse_nonnegative_int(
    "SECURE_HSTS_SECONDS",
    os.getenv("SECURE_HSTS_SECONDS", "0"),
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
if env_bool("TRUST_PROXY_SSL_HEADER", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

APP_LOG_LEVEL = os.getenv("APP_LOG_LEVEL", "INFO").strip().upper()
if APP_LOG_LEVEL not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
    raise ImproperlyConfigured("APP_LOG_LEVEL must be a standard logging level.")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_context": {"()": "buglessfit.monitoring.RequestContextFilter"},
    },
    "formatters": {
        "safe_json": {"()": "buglessfit.monitoring.SafeJsonFormatter"},
    },
    "handlers": {
        "safe_console": {
            "class": "logging.StreamHandler",
            "filters": ["request_context"],
            "formatter": "safe_json",
        },
    },
    "loggers": {
        **{
            name: {
                "handlers": ["safe_console"],
                "level": APP_LOG_LEVEL,
                "propagate": False,
            }
            for name in (
                "buglessfit.health",
                "buglessfit.requests",
                "accounts.throttling",
                "store.services.checkout",
                "store.services.contact",
                "store.services.operations",
                "store.views",
            )
        },
        "django.request": {
            "handlers": ["safe_console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["safe_console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["safe_console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
