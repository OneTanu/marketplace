import pytest
from django.core.cache import cache
from django.test import override_settings

# Production's cache (config/settings/prod.py): one table every web process shares.
DATABASE_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "tanu_cache",
    }
}


@pytest.mark.django_db
@override_settings(CACHES=DATABASE_CACHE)
def test_rate_limits_count_in_the_shared_database_cache(client):
    cache.clear()
    for _ in range(10):
        client.post(
            "/api/account/reactivate/",
            {"email": "guess@umd.edu", "password": "guess"},
            content_type="application/json",
        )
    limited = client.post(
        "/api/account/reactivate/",
        {"email": "guess@umd.edu", "password": "guess"},
        content_type="application/json",
    )
    assert limited.status_code == 429
    cache.clear()
