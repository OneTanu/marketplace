"""Settings shared by every environment. Environment-specific files import from here."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "drf_spectacular",
    "allauth",
    "allauth.account",
    "allauth.headless",
    "procrastinate.contrib.django",
    # Tanu
    "apps.accounts",
    "apps.listings",
    "apps.bookings",
    "apps.payments",
    "apps.reviews",
    "apps.trust",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Defaults match docker-compose.yml; the db container is published on host port 5433.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "tanu"),
        "USER": os.environ.get("POSTGRES_USER", "tanu"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "tanu"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5433"),
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Store UTC, display in the campus time zone.
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Accounts (django-allauth, headless) ---
# Signup is limited to verified UMD email addresses.
TANU_ALLOWED_EMAIL_DOMAINS = ["umd.edu", "terpmail.umd.edu"]

ACCOUNT_ADAPTER = "apps.accounts.adapter.AccountAdapter"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# Caution: enabling ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED lets a pending signup change its
# email through a form that skips AccountAdapter.clean_email. Re-check the UMD restriction first.
ACCOUNT_UNIQUE_EMAIL = True

HEADLESS_ONLY = True
WEB_APP_URL = os.environ.get("WEB_APP_URL", "http://localhost:3000")
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": f"{WEB_APP_URL}/account/verify-email/{{key}}",
    "account_reset_password_from_key": f"{WEB_APP_URL}/account/password/reset/{{key}}",
    "account_signup": f"{WEB_APP_URL}/account/signup",
}

# --- API ---
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Tanu API",
    "DESCRIPTION": "Marketplace API shared by the Tanu web and mobile apps.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
