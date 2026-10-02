import pytest
from django.conf import settings
from django.test import Client

SIGNUP_URL = "/api/auth/browser/v1/auth/signup"


@pytest.mark.django_db
def test_browser_post_from_web_app_origin_passes_csrf():
    """The web app proxies /api to Django, so browser POSTs arrive with the web app's
    Origin while the Host is Django's. Django must trust that origin, or every browser
    form submission fails CSRF (403)."""
    client = Client(enforce_csrf_checks=True)
    client.get("/api/auth/browser/v1/config")
    token = client.cookies["csrftoken"].value
    response = client.post(
        SIGNUP_URL,
        {"email": "terp@gmail.com", "password": "a-long-test-password-123"},
        content_type="application/json",
        headers={"Origin": settings.WEB_APP_URL, "X-CSRFToken": token},
    )
    # 400 = reached the signup logic (rejected for the non-school email), not blocked by CSRF.
    assert response.status_code == 400
