import pytest

from apps.deals.tests.test_services import listing_for, verified_user
from apps.messaging.services import send_message, start_direct_conversation
from apps.trust.models import Block, Report, UserRestriction


@pytest.mark.django_db
def test_a_report_returns_only_a_receipt(client):
    reporter = verified_user("api-reporter")
    listing = listing_for(verified_user("api-seller"))
    client.force_login(reporter)

    response = client.post(
        "/api/reports/",
        {
            "target_type": "listing",
            "target_id": listing.pk,
            "reason": "prohibited_item",
            "prohibited_category": "weapon",
            "details": "It's a knife",
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json()) == {"id", "created_at"}
    again = client.post(
        "/api/reports/",
        {"target_type": "listing", "target_id": listing.pk, "reason": "spam"},
        content_type="application/json",
    )
    assert again.status_code == 400
    assert "already reported" in again.json()["detail"]


@pytest.mark.django_db
def test_reporting_a_conversation_can_block_the_other_student(client):
    reporter = verified_user("api-convo-reporter")
    other = verified_user("api-convo-other")
    conversation = start_direct_conversation(sender=other, recipient=reporter)
    message = send_message(conversation=conversation, sender=other, body="threat")
    client.force_login(reporter)

    response = client.post(
        "/api/reports/",
        {
            "target_type": "conversation",
            "target_id": conversation.pk,
            "reason": "harassment",
            "message_ids": [message.pk],
            "block": True,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert Report.objects.get().reported_user == other
    assert Block.objects.filter(blocker=reporter, blocked=other).exists()


@pytest.mark.django_db
def test_block_list_block_and_unblock(client):
    me = verified_user("api-blocker")
    other = verified_user("api-blocked")
    client.force_login(me)

    created = client.post(
        "/api/blocks/", {"username": other.username}, content_type="application/json"
    )
    assert created.status_code == 201
    assert [row["username"] for row in client.get("/api/blocks/").json()] == [other.username]

    assert client.delete(f"/api/blocks/{other.username}/").status_code == 204
    assert client.get("/api/blocks/").json() == []


@pytest.mark.django_db
def test_my_restrictions_shows_what_is_paused_but_not_why(client):
    me = verified_user("api-restricted")
    client.force_login(me)
    assert client.get("/api/me/restrictions/").json() == []

    UserRestriction.objects.create(user=me, kind="selling", reason="internal note")
    rows = client.get("/api/me/restrictions/").json()
    assert rows == [{"kind": "selling", "kind_label": "Selling", "expires_at": None}]
