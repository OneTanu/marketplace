import pytest
from allauth.account.models import EmailAddress

from apps.accounts.models import Follow, User
from apps.schools.models import School

PASSWORD = "pw-123456789"


def verified_user(username, first_name, email=None):
    school = School.objects.get(slug="umd")
    email = email or f"{username}@umd.edu"
    user = User.objects.create_user(
        email,
        PASSWORD,
        username=username,
        first_name=first_name,
        last_name="Private",
        school=school,
    )
    EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
    return user


@pytest.mark.django_db
def test_user_search_requires_authentication(client):
    assert client.get("/api/users/?q=maya").status_code == 403


@pytest.mark.django_db
def test_user_search_finds_verified_users_without_private_fields(client):
    viewer = verified_user("viewer", "Viewer")
    verified_user("maya.closet", "Maya")
    unverified = User.objects.create_user(
        "hidden@umd.edu",
        PASSWORD,
        username="hiddenmaya",
        first_name="Maya",
        last_name="Secret",
    )
    client.force_login(viewer)

    response = client.get("/api/users/?q=maya")

    assert response.status_code == 200
    assert [user["username"] for user in response.json()] == ["maya.closet"]
    assert "last_name" not in response.json()[0]
    assert "email" not in response.json()[0]
    assert unverified.username not in [user["username"] for user in response.json()]


@pytest.mark.django_db
def test_exact_username_search_ranks_first(client):
    viewer = verified_user("viewer", "Viewer")
    verified_user("maya.closet", "Maya")
    verified_user("maya", "Another")
    client.force_login(viewer)

    response = client.get("/api/users/?q=maya")

    assert response.json()[0]["username"] == "maya"


@pytest.mark.django_db
def test_public_profile_is_case_insensitive_and_private_safe(client):
    viewer = verified_user("viewer", "Viewer")
    target = verified_user("maya.closet", "Maya")
    target.profile_description = "Vintage seller"
    target.instagram_handle = "maya"
    target.save()
    client.force_login(viewer)

    response = client.get("/api/users/MAYA.CLOSET/")

    assert response.status_code == 200
    assert response.json()["first_name"] == "Maya"
    assert response.json()["profile_description"] == "Vintage seller"
    assert "last_name" not in response.json()
    assert "email" not in response.json()


@pytest.mark.django_db
def test_follow_and_unfollow_user(client):
    viewer = verified_user("viewer", "Viewer")
    target = verified_user("maya", "Maya")
    client.force_login(viewer)

    followed = client.post("/api/users/maya/follow/")
    followed_again = client.post("/api/users/maya/follow/")

    assert followed.status_code == 200
    assert followed.json()["is_following"] is True
    assert followed.json()["follower_count"] == 1
    assert followed_again.status_code == 200
    assert Follow.objects.filter(follower=viewer, following=target).count() == 1

    unfollowed = client.delete("/api/users/maya/follow/")
    assert unfollowed.status_code == 204
    assert not Follow.objects.filter(follower=viewer, following=target).exists()


@pytest.mark.django_db
def test_user_cannot_follow_self(client):
    viewer = verified_user("viewer", "Viewer")
    client.force_login(viewer)

    response = client.post("/api/users/viewer/follow/")

    assert response.status_code == 400
    assert not Follow.objects.exists()
