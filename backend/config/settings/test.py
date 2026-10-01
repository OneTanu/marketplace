from .base import *  # noqa: F403

SECRET_KEY = "test-only-insecure-secret-key"  # noqa: S105
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast tests only
