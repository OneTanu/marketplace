from .base import *  # noqa: F403

SECRET_KEY = "test-only-insecure-secret-key"  # noqa: S105
# Tests always use the local database, never a hosted DATABASE_URL that happens to be set.
DATABASES = {"default": LOCAL_DATABASE}  # noqa: F405
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast tests only
