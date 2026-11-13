"""Students who've blocked each other (either way) look as if the other doesn't exist."""

import pytest

from apps.deals.tests.test_services import listing_for, verified_user
from apps.trust.services import block_user


@pytest.fixture
def blocked_pair():
    blocker = verified_user("vis-blocker")
    blocked = verified_user("vis-blocked")
    block_user(blocker=blocker, blocked=blocked)
    return blocker, blocked


@pytest.mark.django_db
@pytest.mark.parametrize("viewer_is_blocker", [True, False])
def test_blocked_students_cant_see_each_others_profile_or_listings(
    client, blocked_pair, viewer_is_blocker
):
    blocker, blocked = blocked_pair
    viewer, other = (blocker, blocked) if viewer_is_blocker else (blocked, blocker)
    listing = listing_for(other)
    client.force_login(viewer)

    assert client.get(f"/api/users/{other.username}/").status_code == 404
    assert client.get(f"/api/users/{other.username}/listings/").status_code == 404
    assert client.get(f"/api/users/{other.username}/followers/").status_code == 404
    assert client.post(f"/api/users/{other.username}/follow/").status_code == 404
    assert client.get("/api/users/", {"q": other.username}).json() == []
    assert client.get(f"/api/listings/{listing.pk}/").status_code == 404
    feed = client.get("/api/listings/").json()["results"]
    assert listing.pk not in [card["id"] for card in feed]


@pytest.mark.django_db
def test_other_students_still_see_both(client, blocked_pair):
    blocker, blocked = blocked_pair
    listing = listing_for(blocked)
    client.force_login(verified_user("vis-bystander"))

    assert client.get(f"/api/users/{blocked.username}/").status_code == 200
    assert client.get(f"/api/users/{blocker.username}/").status_code == 200
    assert client.get(f"/api/listings/{listing.pk}/").status_code == 200


@pytest.mark.django_db
def test_unblocking_makes_them_visible_again(client, blocked_pair):
    from apps.trust.services import unblock_user

    blocker, blocked = blocked_pair
    unblock_user(blocker=blocker, blocked=blocked)
    client.force_login(blocked)

    assert client.get(f"/api/users/{blocker.username}/").status_code == 200
