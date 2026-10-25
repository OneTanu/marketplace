import os

from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = "dev-only-insecure-secret-key"  # noqa: S105
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Print emails (e.g. verification links) to the console instead of sending them.
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}

# E2E runs (backend/scripts/e2e_server.sh) sign the same test students in from many parallel
# tests at once, which trips allauth's per-email login limit. Only that throwaway server sets
# this; never set it anywhere else.
if os.environ.get("E2E_DISABLE_RATE_LIMITS") == "1":
    ACCOUNT_RATE_LIMITS = False

# E2E runs read emails (e.g. password reset links) from files instead of the console. Only
# backend/scripts/e2e_server.sh sets this.
if os.environ.get("E2E_EMAIL_DIR"):
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.filebased.EmailBackend",
            "OPTIONS": {"file_path": os.environ["E2E_EMAIL_DIR"]},
        }
    }
