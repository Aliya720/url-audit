# Django settings — PulseWatch
# TRD §11 — Configuration Reference

import environ
import os
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment parsing (TRD §1.1 — django-environ)
import sys

IS_TESTING = (
    "pytest" in sys.modules
    or "conftest" in sys.modules
    or any("pytest" in str(arg).lower() for arg in sys.argv)
    or os.environ.get("PYTEST_CURRENT_TEST") is not None
)

if IS_TESTING:
    os.environ["DATABASE_URL"] = ""

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
    CACHE_TTL_SECONDS=(int, 900),
    FETCH_TIMEOUT_SECONDS=(int, 10),
    MAX_CONCURRENT_CHECKS=(int, 50),
    RATE_LIMIT_MAX_REQUESTS=(int, 60),
    RATE_LIMIT_WINDOW_SECONDS=(int, 60),
    RATE_LIMIT_BURST=(int, 100),
    MONITOR_MIN_INTERVAL_SECONDS=(int, 60),
    MONITOR_HISTORY_MAX=(int, 50),
    LOG_LEVEL=(str, "INFO"),
    SENTRY_DSN=(str, ""),
    SENTRY_ENVIRONMENT=(str, "production"),
    PROMETHEUS_METRICS_ENABLED=(bool, True),
    MAX_REDIRECT_HOPS=(int, 5),
)

# Read .env file if it exists (check both backend dir and project root)
for env_path in [BASE_DIR / ".env", BASE_DIR.parent / ".env"]:
    if env_path.exists():
        environ.Env.read_env(str(env_path), overwrite=False)

if IS_TESTING:
    os.environ["DATABASE_URL"] = ""

# Security
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-pulsewatch-dev-secret-key-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Application definition
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "django_celery_beat",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.contrib.celery",
    "health_check.contrib.redis",
    "drf_spectacular",
    "django_prometheus",
    # Local
    "checks",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "checks.middleware.RequestIDMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "pulsewatch.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "pulsewatch.wsgi.application"

# Database — PostgreSQL in docker/prod, SQLite fallback for local dev/testing
import sys

IS_TESTING = "pytest" in sys.modules or "test" in sys.argv
db_url = os.environ.get("DATABASE_URL", "")
if db_url and not IS_TESTING:
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Redis — Cache + Throttle + Broker (TRD §1)
REDIS_URL = os.environ.get("REDIS_URL", "").strip()
if REDIS_URL and REDIS_URL.startswith("redis://") and not IS_TESTING:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "pulsewatch-cache",
        }
    }

# Celery — Task queue (TRD §10)
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)

# DRF (TRD §1)
REST_FRAMEWORK = {
    "UNAUTHENTICATED_USER": None,
    "UNAUTHENTICATED_TOKEN": None,
    "DEFAULT_THROTTLE_CLASSES": [
        "checks.throttling.PulseWatchThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {},
    "EXCEPTION_HANDLER": "checks.exceptions.pulsewatch_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# drf-spectacular (TRD §1.1)
SPECTACULAR_SETTINGS = {
    "TITLE": "PulseWatch API",
    "DESCRIPTION": "URL Health Audit & Monitoring Service",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Static files
STATIC_URL = "/url-audit-project/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Subpath deployment — tells Django it lives behind a prefix
FORCE_SCRIPT_NAME = "/url-audit-project"

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- PulseWatch Configuration (TRD §11) ----
CACHE_TTL_SECONDS = env("CACHE_TTL_SECONDS")
FETCH_TIMEOUT_SECONDS = env("FETCH_TIMEOUT_SECONDS")
MAX_CONCURRENT_CHECKS = env("MAX_CONCURRENT_CHECKS")
RATE_LIMIT_MAX_REQUESTS = env("RATE_LIMIT_MAX_REQUESTS")
RATE_LIMIT_WINDOW_SECONDS = env("RATE_LIMIT_WINDOW_SECONDS")
RATE_LIMIT_BURST = env("RATE_LIMIT_BURST")
MONITOR_MIN_INTERVAL_SECONDS = env("MONITOR_MIN_INTERVAL_SECONDS")
MONITOR_HISTORY_MAX = env("MONITOR_HISTORY_MAX")
MAX_REDIRECT_HOPS = env("MAX_REDIRECT_HOPS")

# Sentry (TRD §1.1 — only on live deploy, not in CI/local)
SENTRY_DSN = env("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        environment=env("SENTRY_ENVIRONMENT"),
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# Structured Logging (TRD §9)
LOG_LEVEL = env("LOG_LEVEL")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "checks": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}
