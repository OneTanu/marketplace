"""Database settings from connection URLs, for hosted Postgres such as Supabase.

Two URLs, because a transaction-mode pooler can't run everything:

- DATABASE_URL: the pooled connection (Supabase's transaction pooler, port 6543), for the API.
- DIRECT_DATABASE_URL: a direct or session-mode connection (Supabase's session pooler, port
  5432), for migrations and the Procrastinate worker. The worker uses LISTEN/NOTIFY and
  advisory locks, and migrations hold locks across statements; a transaction pooler breaks
  both.

Without DATABASE_URL, the separate POSTGRES_* variables are used (local Docker, CI, E2E).
"""

import os
import sys
from urllib.parse import parse_qsl, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

# manage.py commands that must not go through a transaction pooler.
DIRECT_COMMANDS = {
    "migrate",
    "makemigrations",
    "showmigrations",
    "sqlmigrate",
    "dbshell",
    "procrastinate",
    "createsuperuser",
    "create_verified_user",
}


def parse_database_url(url: str, *, pooled: bool) -> dict:
    """A Django DATABASES entry from a postgres:// URL. Passwords may be percent-encoded.
    SSL is required unless the URL says otherwise. `pooled` makes the connection safe for a
    transaction-mode pooler: no server-side prepared statements or cursors, no persistent
    connections."""
    parts = urlsplit(url)
    if parts.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("Database URLs must start with postgres:// or postgresql://")
    name = unquote(parts.path.lstrip("/"))
    if not (parts.hostname and name):
        raise ImproperlyConfigured("The database URL needs a host and a database name.")
    query = dict(parse_qsl(parts.query))
    options = {"sslmode": query.get("sslmode", "require")}
    if pooled:
        # psycopg prepares repeated queries on the server by default; a transaction pooler
        # may hand the next query to a different server connection, which won't have them.
        options["prepare_threshold"] = None
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "USER": unquote(parts.username or ""),
        "PASSWORD": unquote(parts.password or ""),
        "HOST": parts.hostname,
        "PORT": str(parts.port or 5432),
        "OPTIONS": options,
        # The pooler keeps server connections open; Django holding its own adds nothing.
        "CONN_MAX_AGE": 0 if pooled else 60,
        "CONN_HEALTH_CHECKS": True,
        "DISABLE_SERVER_SIDE_CURSORS": pooled,
    }


def wants_direct_connection(argv: list[str] | None = None) -> bool:
    """Whether this process should skip the pooler: a migration or worker command, or
    DATABASE_CONNECTION=direct."""
    if os.environ.get("DATABASE_CONNECTION") == "direct":
        return True
    argv = sys.argv if argv is None else argv
    return len(argv) > 1 and argv[1] in DIRECT_COMMANDS


def database_from_environment() -> dict | None:
    """The default database from DATABASE_URL / DIRECT_DATABASE_URL, or None when neither is
    set (then settings use the POSTGRES_* variables)."""
    pooled_url = os.environ.get("DATABASE_URL", "")
    direct_url = os.environ.get("DIRECT_DATABASE_URL", "")
    if not (pooled_url or direct_url):
        return None
    if direct_url and (wants_direct_connection() or not pooled_url):
        return parse_database_url(direct_url, pooled=False)
    return parse_database_url(pooled_url, pooled=True)
