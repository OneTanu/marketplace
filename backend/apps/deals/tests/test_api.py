import pytest

from apps.deals.models import Deal
from apps.deals.tests.test_services import listing_for, verified_user


@pytest.mark.django_db
def test_deal_endpoints_are_private_and_walk_through_handoff(client):
    seller = verified_user("seller")
    buyer = verified_user("buyer")
    outsider = verified_user("outsider")
    listing = listing_for(seller)

    client.force_login(buyer)
    created = client.post(
        f"/api/listings/{listing.pk}/deals/",
        {"kind": "offer", "amount_cents": 4200},
        content_type="application/json",
    )
    assert created.status_code == 201
    deal_id = created.json()["id"]
    assert created.json()["my_role"] == "buyer"
    assert created.json()["awaiting_me"] is False

    client.force_login(seller)
    assert client.get("/api/conversations/unread-count/").json() == {"unread_count": 1}

    client.force_login(outsider)
    assert client.get(f"/api/deals/{deal_id}/").status_code == 404

    client.force_login(seller)
    accepted = client.post(f"/api/deals/{deal_id}/accept/")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == Deal.Status.PENDING

    seller_confirmation = client.post(f"/api/deals/{deal_id}/confirm-handoff/")
    assert seller_confirmation.json()["seller_confirmed"] is True
    assert seller_confirmation.json()["status"] == Deal.Status.PENDING

    client.force_login(buyer)
    completed = client.post(f"/api/deals/{deal_id}/confirm-handoff/")
    assert completed.status_code == 200
    assert completed.json()["status"] == Deal.Status.COMPLETED
    assert completed.json()["listing"]["status"] == "sold"


@pytest.mark.django_db
def test_conversation_filter_returns_only_its_deals(client):
    seller = verified_user("seller")
    buyer = verified_user("buyer")
    other_seller = verified_user("other")
    first = listing_for(seller)
    second = listing_for(other_seller)
    client.force_login(buyer)
    first_deal = client.post(
        f"/api/listings/{first.pk}/deals/", {"kind": "buy_now"}, content_type="application/json"
    ).json()
    client.post(
        f"/api/listings/{second.pk}/deals/",
        {"kind": "buy_now"},
        content_type="application/json",
    )

    response = client.get("/api/deals/", {"conversation": first_deal["conversation"]})

    assert response.status_code == 200
    assert [deal["id"] for deal in response.json()] == [first_deal["id"]]
