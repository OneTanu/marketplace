"""The database table behind production's cache (config/settings/prod.py), which holds rate-limit
counters: allauth's login, signup and password-reset limits and DRF throttles. Every web process
shares it, unlike a per-process memory cache, so limits hold however many processes run."""

from django.core.management import call_command
from django.db import migrations

CACHE_TABLE = "tanu_cache"


def create_cache_table(apps, schema_editor):
    call_command("createcachetable", CACHE_TABLE, database=schema_editor.connection.alias)


def drop_cache_table(apps, schema_editor):
    schema_editor.execute(f"DROP TABLE IF EXISTS {CACHE_TABLE}")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_user_deactivation"),
    ]

    operations = [migrations.RunPython(create_cache_table, drop_cache_table)]
