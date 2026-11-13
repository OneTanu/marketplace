import pytest
from allauth.account.models import EmailAddress
from django.core.exceptions import ValidationError

from apps.accounts.models import Follow, User
from apps.accounts.services import follow_user
from apps.schools.models import School
from apps.trust.models import Block
from apps.trust.services import block_user

PASSWORD = "pw-123456789"


def verified_user(username, first_name, email=None, school=None):
    school = school or School.objects.get(slug="umd")
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
def test_user_search_defaults_to_viewers_school_and_can_explicitly_search_all(client):
    umd = School.objects.get(slug="umd")
    towson = School.objects.create(
        name="Towson University",
        short_name="Towson",
        slug="towson",
        signup_is_open=True,
        marketplace_status="open",
    )
    viewer = verified_user("viewer", "Viewer", school=umd)
    verified_user("umd.seller", "Jordan", school=umd)
    verified_user("towson.seller", "Jordan", email="towson@example.edu", school=towson)
    client.force_login(viewer)

    home_results = client.get("/api/users/?q=jordan")
    all_results = client.get("/api/users/?q=jordan&school=all")
    towson_results = client.get("/api/users/?q=jordan&school=towson")

    assert [user["username"] for user in home_results.json()] == ["umd.seller"]
    assert {user["username"] for user in all_results.json()} == {
        "umd.seller",
        "towson.seller",
    }
    assert [user["username"] for user in towson_results.json()] == ["towson.seller"]


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
def test_public_profile_shows_follow_counts_and_viewers_follow_state(client):
    viewer = verified_user("viewer", "Viewer")
    target = verified_user("maya", "Maya")
    fan = verified_user("fan", "Fan")
    Follow.objects.create(follower=fan, following=target)
    Follow.objects.create(follower=target, following=fan)
    client.force_login(viewer)

    before = client.get("/api/users/maya/").json()
    Follow.objects.create(follower=viewer, following=target)
    after = client.get("/api/users/maya/").json()
    client.force_login(target)
    own = client.get("/api/users/maya/").json()

    assert (before["follower_count"], before["following_count"]) == (1, 1)
    assert before["is_following"] is False
    assert (after["follower_count"], after["following_count"]) == (2, 1)
    assert after["is_following"] is True
    assert own["is_self"] is True
    assert own["is_following"] is False


@pytest.mark.django_db
def test_user_cannot_follow_self(client):
    viewer = verified_user("viewer", "Viewer")
    client.force_login(viewer)

    response = client.post("/api/users/viewer/follow/")

    assert response.status_code == 400
    assert not Follow.objects.exists()


def follow_usernames(client, url):
    response = client.get(url)
    assert response.status_code == 200
    return [row["username"] for row in response.json()["results"]]


@pytest.mark.django_db
def test_followers_and_following_lists_newest_first_with_viewer_follow_state(client):
    maya = verified_user("maya", "Maya")
    first = verified_user("first", "First")
    second = verified_user("second", "Second")
    viewer = verified_user("viewer", "Viewer")
    Follow.objects.create(follower=first, following=maya)
    Follow.objects.create(follower=second, following=maya)
    Follow.objects.create(follower=maya, following=first)
    Follow.objects.create(follower=viewer, following=second)
    client.force_login(viewer)

    followers = client.get("/api/users/maya/followers/").json()["results"]
    assert [row["username"] for row in followers] == ["second", "first"]
    assert [row["is_following"] for row in followers] == [True, False]
    assert "email" not in followers[0] and "last_name" not in followers[0]
    assert follow_usernames(client, "/api/users/MAYA/following/") == ["first"]


@pytest.mark.django_db
def test_follow_lists_hide_inactive_and_blocked_students(client):
    maya = verified_user("maya", "Maya")
    gone = verified_user("gone", "Gone")
    blocker = verified_user("blocker", "Blocker")
    fan = verified_user("fan", "Fan")
    viewer = verified_user("viewer", "Viewer")
    for follower in (gone, blocker, fan):
        Follow.objects.create(follower=follower, following=maya)
    gone.is_active = False
    gone.save()
    Block.objects.create(blocker=blocker, blocked=viewer)
    client.force_login(viewer)

    assert follow_usernames(client, "/api/users/maya/followers/") == ["fan"]


@pytest.mark.django_db
def test_follow_list_of_unknown_or_unverified_user_is_404(client):
    client.force_login(verified_user("viewer", "Viewer"))
    unverified = User.objects.create_user("new@umd.edu", PASSWORD, username="newbie")

    assert client.get("/api/users/nobody/followers/").status_code == 404
    assert client.get(f"/api/users/{unverified.username}/following/").status_code == 404


@pytest.mark.django_db
def test_follow_lists_page_with_a_cursor(client):
    maya = verified_user("maya", "Maya")
    for number in range(30):
        Follow.objects.create(follower=verified_user(f"fan{number}", "Fan"), following=maya)
    client.force_login(maya)

    first_page = client.get("/api/users/maya/followers/").json()
    second_page = client.get(
        "/api/users/maya/followers/", {"cursor": first_page["next_cursor"]}
    ).json()

    assert len(first_page["results"]) == 24
    assert len(second_page["results"]) == 6
    assert second_page["next_cursor"] is None
    seen = [row["username"] for row in first_page["results"] + second_page["results"]]
    assert seen == [f"fan{number}" for number in reversed(range(30))]
    # A cursor from one list doesn't work on the other.
    other_list = client.get("/api/users/maya/following/", {"cursor": first_page["next_cursor"]})
    assert other_list.status_code == 400


@pytest.mark.django_db
def test_follow_lists_require_sign_in(client):
    verified_user("maya", "Maya")
    assert client.get("/api/users/maya/followers/").status_code in (401, 403)


@pytest.mark.django_db
def test_blocking_ends_follows_both_ways_and_stops_new_ones(client):
    me = verified_user("me", "Me")
    other = verified_user("other", "Other")
    Follow.objects.create(follower=me, following=other)
    Follow.objects.create(follower=other, following=me)

    block_user(blocker=me, blocked=other)

    assert not Follow.objects.exists()
    client.force_login(other)
    # Blocked students are hidden from each other, so the profile is "not found".
    assert client.post("/api/users/me/follow/").status_code == 404
    assert not Follow.objects.exists()
    with pytest.raises(ValidationError, match="isn't available"):
        follow_user(follower=other, following=me)


@pytest.mark.django_db
def test_my_follow_counts_skip_deactivated_students(client):
    me = verified_user("me", "Me")
    fan = verified_user("fan", "Fan")
    gone = verified_user("gone", "Gone")
    Follow.objects.create(follower=fan, following=me)
    Follow.objects.create(follower=gone, following=me)
    Follow.objects.create(follower=me, following=gone)
    gone.is_active = False
    gone.save()
    client.force_login(me)

    data = client.get("/api/me/").json()
    assert (data["follower_count"], data["following_count"]) == (1, 0)
