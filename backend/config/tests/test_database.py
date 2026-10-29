import pytest
from django.core.exceptions import ImproperlyConfigured

from config import database

POOLED = "postgresql://postgres.abc:p%40ss%2Fword@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
DIRECT = "postgresql://postgres.abc:p%40ss%2Fword@aws-0-us-east-1.pooler.supabase.com:5432/postgres"


def test_pooled_urls_are_safe_for_a_transaction_pooler():
    config = database.parse_database_url(POOLED, pooled=True)

    assert config["PASSWORD"] == "p@ss/word"  # percent-encoding undone
    assert (config["USER"], config["HOST"], config["PORT"], config["NAME"]) == (
        "postgres.abc",
        "aws-0-us-east-1.pooler.supabase.com",
        "6543",
        "postgres",
    )
    assert config["OPTIONS"] == {"sslmode": "require", "prepare_threshold": None}
    assert config["DISABLE_SERVER_SIDE_CURSORS"] is True
    assert config["CONN_MAX_AGE"] == 0


def test_direct_urls_keep_prepared_statements_and_an_explicit_sslmode():
    config = database.parse_database_url(f"{DIRECT}?sslmode=verify-full", pooled=False)

    assert config["OPTIONS"] == {"sslmode": "verify-full"}
    assert config["DISABLE_SERVER_SIDE_CURSORS"] is False


def test_migrations_and_the_worker_use_the_direct_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", POOLED)
    monkeypatch.setenv("DIRECT_DATABASE_URL", DIRECT)
    monkeypatch.delenv("DATABASE_CONNECTION", raising=False)

    for command, port in [("migrate", "5432"), ("procrastinate", "5432"), ("runserver", "6543")]:
        monkeypatch.setattr(database.sys, "argv", ["manage.py", command])
        assert database.database_from_environment()["PORT"] == port
    monkeypatch.setenv("DATABASE_CONNECTION", "direct")
    assert database.database_from_environment()["PORT"] == "5432"


def test_no_url_means_local_settings(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DIRECT_DATABASE_URL", raising=False)
    assert database.database_from_environment() is None


def test_bad_urls_are_refused():
    for url in ("mysql://u:p@h/db", "postgresql://u:p@host"):
        with pytest.raises(ImproperlyConfigured):
            database.parse_database_url(url, pooled=True)
