from datetime import time

import pytest

from apps.deals import services
from apps.deals.models import Deal, MeetupProposal
from apps.deals.tests.test_services import listing_for, verified_user
from apps.schools.models import MeetingSpot


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


@pytest.mark.django_db
def test_meetup_preferences_feed_buy_now_options_and_acceptance(client):
    seller = verified_user("meetup-seller")
    buyer = verified_user("meetup-buyer")
    listing = listing_for(seller)
    spot = MeetingSpot.objects.create(
        school=seller.school,
        name="Library entrance",
        directions="Meet by the staffed desk.",
        is_indoor=True,
    )

    client.force_login(seller)
    saved = client.put(
        "/api/meetup-preferences/",
        {
            "meeting_spot_ids": [spot.pk],
            "windows": [
                {"weekday": weekday, "start_time": time(0, 0), "end_time": time(23, 59)}
                for weekday in range(7)
            ],
            "overrides": [],
        },
        content_type="application/json",
    )
    assert saved.status_code == 200
    assert saved.json()["meeting_spots"][0]["id"] == spot.pk

    client.force_login(buyer)
    options = client.get(f"/api/listings/{listing.pk}/meetup-options/")
    assert options.status_code == 200
    assert options.json()["seller_configured"] is True
    starts_at = options.json()["slots"][0]["starts_at"]

    created = client.post(
        f"/api/listings/{listing.pk}/deals/",
        {
            "kind": "buy_now",
            "meeting_spot_id": spot.pk,
            "proposed_starts_at": [starts_at],
        },
        content_type="application/json",
    )
    assert created.status_code == 201
    proposal = created.json()["meetup_proposals"][0]
    assert proposal["status"] == MeetupProposal.Status.PENDING

    client.force_login(seller)
    accepted = client.post(
        f"/api/deals/{created.json()['id']}/accept/",
        {"meetup_proposal_id": proposal["id"]},
        content_type="application/json",
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == Deal.Status.PENDING
    assert accepted.json()["meetup_proposals"][0]["status"] == MeetupProposal.Status.ACCEPTED

    late = client.post(
        f"/api/deals/{created.json()['id']}/meetup-status/",
        {"kind": "running_late", "minutes_late": 10},
        content_type="application/json",
    )
    assert late.status_code == 201
    assert late.json()["minutes_late"] == 10


@pytest.mark.django_db
def test_meetup_reschedule_requires_other_party_to_accept(client):
    seller = verified_user("reschedule-seller")
    buyer = verified_user("reschedule-buyer")
    listing = listing_for(seller)
    spot = MeetingSpot.objects.create(
        school=seller.school,
        name="Student union desk",
        directions="Meet inside by the information desk.",
    )
    client.force_login(seller)
    client.put(
        "/api/meetup-preferences/",
        {
            "meeting_spot_ids": [spot.pk],
            "windows": [
                {"weekday": weekday, "start_time": "00:00", "end_time": "23:59"}
                for weekday in range(7)
            ],
            "overrides": [],
        },
        content_type="application/json",
    )
    client.force_login(buyer)
    starts = client.get(f"/api/listings/{listing.pk}/meetup-options/").json()["slots"]
    created = client.post(
        f"/api/listings/{listing.pk}/deals/",
        {"kind": "buy_now"},
        content_type="application/json",
    ).json()
    client.force_login(seller)
    client.post(f"/api/deals/{created['id']}/accept/", {}, content_type="application/json")
    client.force_login(buyer)
    proposal = client.post(
        f"/api/deals/{created['id']}/meetup-proposals/",
        {"meeting_spot_id": spot.pk, "starts_at": starts[0]["starts_at"]},
        content_type="application/json",
    )
    assert proposal.status_code == 201
    own_accept = client.post(
        f"/api/deals/{created['id']}/meetup-proposals/accept/",
        {"proposal_id": proposal.json()["id"]},
        content_type="application/json",
    )
    assert own_accept.status_code == 403

    client.force_login(seller)
    accepted = client.post(
        f"/api/deals/{created['id']}/meetup-proposals/accept/",
        {"proposal_id": proposal.json()["id"]},
        content_type="application/json",
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == MeetupProposal.Status.ACCEPTED


@pytest.mark.django_db
def test_sellers_can_split_a_day_into_several_ranges_but_not_overlap_them(client):
    seller = verified_user("split-seller")
    spot = MeetingSpot.objects.create(
        school=seller.school, name="Split desk", directions="Inside by the desk."
    )
    client.force_login(seller)

    def save(windows):
        return client.put(
            "/api/meetup-preferences/",
            {"meeting_spot_ids": [spot.pk], "windows": windows, "overrides": []},
            content_type="application/json",
        )

    split_day = [
        {"weekday": weekday, "start_time": start, "end_time": end}
        for weekday in range(7)
        for start, end in [("10:00", "11:00"), ("15:00", "16:00")]
    ]
    saved = save(split_day)
    assert saved.status_code == 200
    assert len(saved.json()["availability_windows"]) == 14

    local_hours = {
        slot.astimezone(services._local_zone()).hour
        for slot in services.meetup_slots(seller=seller)
    }
    assert local_hours == {10, 15}

    overlapping = save(
        [
            {"weekday": 2, "start_time": "10:00", "end_time": "12:00"},
            {"weekday": 2, "start_time": "11:30", "end_time": "13:00"},
        ]
    )
    assert overlapping.status_code == 400
    assert "Wednesday" in str(overlapping.json())
