#!/bin/sh
# Starts the Django API for Playwright end-to-end tests (started by web/playwright.config.ts).
# Recreates its own database on every run, so the dev database is never touched.
#
# Env: POSTGRES_DB (must end in "_e2e"), PORT, E2E_USER_EMAIL, E2E_BUYER_EMAIL, E2E_USER_PASSWORD,
# WEB_APP_URL (the E2E web app's origin, trusted for CSRF), plus the usual POSTGRES_* settings.
# E2E_DISABLE_RATE_LIMITS=1 turns off allauth login limits (see config/settings/dev.py).
set -eu

case "${POSTGRES_DB:-}" in
  *_e2e) ;;
  *) echo "e2e_server.sh: POSTGRES_DB must end in _e2e (got '${POSTGRES_DB:-}')" >&2; exit 1 ;;
esac
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.dev}"

python - <<'PY'
import psycopg
from django.conf import settings
from psycopg import sql

db = settings.DATABASES["default"]
assert db["NAME"].endswith("_e2e"), f"refusing to recreate database {db['NAME']!r}"
with psycopg.connect(
    host=db["HOST"], port=db["PORT"], user=db["USER"], password=db["PASSWORD"],
    dbname="postgres", autocommit=True,
) as conn:
    name = sql.Identifier(db["NAME"])
    conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(name))
    conn.execute(sql.SQL("CREATE DATABASE {}").format(name))
PY

python manage.py migrate --noinput --verbosity 0
python manage.py create_verified_user "$E2E_USER_EMAIL" --password "$E2E_USER_PASSWORD"
# A second student, for tests where one student looks at another's listing.
python manage.py create_verified_user "$E2E_BUYER_EMAIL" --password "$E2E_USER_PASSWORD"
exec python manage.py runserver "0.0.0.0:${PORT}" --noreload
