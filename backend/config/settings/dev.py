from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = "dev-only-insecure-secret-key"  # noqa: S105
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Print emails (e.g. verification links) to the console instead of sending them.
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}
