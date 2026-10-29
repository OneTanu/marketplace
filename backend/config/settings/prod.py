import os

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
ALLOWED_HOSTS = [h.strip() for h in os.environ["DJANGO_ALLOWED_HOSTS"].split(",") if h.strip()]

# Fail at startup rather than silently using the local dev database credentials: either
# DATABASE_URL (hosted Postgres, see config/database.py) or every POSTGRES_* variable.
if not (os.environ.get("DATABASE_URL") or os.environ.get("DIRECT_DATABASE_URL")):
    for _var in (
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
    ):
        if _var not in os.environ:
            raise RuntimeError(f"{_var} (or DATABASE_URL) must be set in production")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
