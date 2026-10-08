"""People search must cost a fixed number of queries, however many students it returns."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import Follow

from .test_social import verified_user


def add_students(viewer, count, *, start):
    """Add `count` students named maya<n>, each followed by the viewer and following them."""
    for number in range(start, start + count):
        student = verified_user(f"maya{number}", "Maya")
        Follow.objects.create(follower=viewer, following=student)
        Follow.objects.create(follower=student, following=viewer)


def search_query_count(client):
    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/users/?q=maya")
    assert response.status_code == 200
    return len(queries), response.json()


@pytest.mark.django_db
def test_user_search_uses_constant_queries(client, django_assert_max_num_queries):
    viewer = verified_user("viewer", "Viewer")
    add_students(viewer, 1, start=1)
    client.force_login(viewer)

    with django_assert_max_num_queries(4):
        few, _ = search_query_count(client)
    add_students(viewer, 4, start=2)
    many, results = search_query_count(client)

    assert many == few
    assert len(results) == 5
    assert all(user["is_following"] for user in results)
    assert {(user["follower_count"], user["following_count"]) for user in results} == {(1, 1)}
