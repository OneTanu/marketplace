import os
from urllib.parse import urlsplit

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

# Email goes through Postmark (transactional only: verification, password resets, deal
# notifications), behind django-anymail so the provider can change without code changes.
# The sender's domain must be verified in Postmark, with its SPF/DKIM records in DNS.
MAILERS = {
    "default": {
        "BACKEND": "anymail.backends.postmark.EmailBackend",
        "OPTIONS": {"server_token": os.environ["POSTMARK_SERVER_TOKEN"]},
    }
}
DEFAULT_FROM_EMAIL = os.environ["DEFAULT_FROM_EMAIL"]
SERVER_EMAIL = DEFAULT_FROM_EMAIL

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30

# Static files are collected into the image at build time (see the Dockerfile) and served by
# WhiteNoise with hashed, compressed, long-cached names. Only production collects them, so
# STATIC_ROOT lives here (elsewhere WhiteNoise would warn that the folder is missing).
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
# Uploads go to Cloudflare R2 (S3-compatible), because Heroku wipes its disk on every restart
# and deploy. Listing photos live in a public bucket served from MEDIA_PUBLIC_URL (an R2
# custom domain); report evidence lives in a private bucket and is only reachable through
# signed links that expire after a few minutes.
_R2_ENDPOINT = urlsplit(os.environ["R2_ENDPOINT_URL"])
# Cloudflare shows the S3 URL with the bucket name appended. With that path in the endpoint,
# every upload lands in a folder named after it instead of at the bucket root.
if _R2_ENDPOINT.path.strip("/"):
    raise RuntimeError(
        "R2_ENDPOINT_URL must be just https://<account-id>.r2.cloudflarestorage.com, "
        "without a bucket name or other path"
    )
_R2_OPTIONS = {
    "endpoint_url": os.environ["R2_ENDPOINT_URL"],
    "access_key": os.environ["R2_ACCESS_KEY_ID"],
    "secret_key": os.environ["R2_SECRET_ACCESS_KEY"],
    "region_name": "auto",
    "signature_version": "s3v4",
    # Uploads get unique names; never replace an existing object.
    "file_overwrite": False,
    # R2 has no per-object ACLs; access is decided per bucket.
    "default_acl": None,
}
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_R2_OPTIONS,
            "bucket_name": os.environ["R2_PUBLIC_BUCKET"],
            "custom_domain": urlsplit(os.environ["MEDIA_PUBLIC_URL"]).netloc,
            "querystring_auth": False,
        },
    },
    "private": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_R2_OPTIONS,
            "bucket_name": os.environ["R2_PRIVATE_BUCKET"],
            "querystring_auth": True,
            "querystring_expire": 300,
        },
    },
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
