from datetime import timedelta

import pytest
from allauth.account.models import EmailAddress
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.listings.models import Category, Listing
from apps.messaging.models import Conversation, ConversationParticipant, Message
from apps.messaging.services import mark_conversation_read, send_message, start_direct_conversation
from apps.schools.models import School

PASSWORD = "pw-123456789"


def verified_user(username):
    school = School.objects.get(slug="umd")
    email = f"{username}@umd.edu"
    user = User.objects.create_user(
        email,
        PASSWORD,
        username=username,
        first_name=username.title(),
        school=school,
    )
    EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
    return user


@pytest.mark.django_db
def test_conversations_require_authentication(client):
    assert client.get("/api/conversations/").status_code == 403


@pytest.mark.django_db
def test_start_conversation_is_idempotent_and_private(client):
    alex = verified_user("alex")
    verified_user("maya")
    outsider = verified_user("outsider")
    client.force_login(alex)

    first = client.post("/api/conversations/", {"username": "maya"})
    second = client.post("/api/conversations/", {"username": "MAYA"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert Conversation.objects.count() == 1
    assert ConversationParticipant.objects.count() == 2

    client.force_login(outsider)
    assert client.get(f"/api/conversations/{first.json()['id']}/").status_code == 404


@pytest.mark.django_db
def test_listing_is_attached_to_a_message_in_the_existing_conversation(client):
    buyer = verified_user("buyer")
    seller = verified_user("seller")
    category = Category.objects.get(slug="men-jeans")
    first_listing = Listing.objects.create(
        school=seller.school,
        seller=seller,
        category=category,
        title="Levi's jeans",
        price_cents=3000,
    )
    client.force_login(buyer)

    conversation = client.post("/api/conversations/", {"username": seller.username})
    message = client.post(
        f"/api/conversations/{conversation.json()['id']}/messages/",
        {"body": "Is this still available?", "listing_id": first_listing.pk},
    )
    repeated = client.post("/api/conversations/", {"username": seller.username})

    assert message.status_code == 201
    assert message.json()["listing"] == {
        "id": first_listing.pk,
        "title": "Levi's jeans",
        "status": "available",
    }
    assert message.json()["body"] == "Is this still available?"
    assert repeated.json()["id"] == conversation.json()["id"]
    assert Conversation.objects.count() == 1


@pytest.mark.django_db
def test_listing_attachment_requires_the_seller_in_the_conversation(client):
    buyer = verified_user("buyer")
    seller = verified_user("seller")
    other = verified_user("other")
    listing = Listing.objects.create(
        school=seller.school,
        seller=seller,
        category=Category.objects.get(slug="men-jeans"),
        title="Levi's jeans",
        price_cents=3000,
    )
    client.force_login(buyer)

    conversation = client.post("/api/conversations/", {"username": other.username})
    response = client.post(
        f"/api/conversations/{conversation.json()['id']}/messages/",
        {"body": "Wrong conversation", "listing_id": listing.pk},
    )

    assert response.status_code == 400
    assert not Message.objects.exists()


@pytest.mark.django_db
def test_user_cannot_message_self(client):
    alex = verified_user("alex")
    client.force_login(alex)

    response = client.post("/api/conversations/", {"username": "alex"})

    assert response.status_code == 400
    assert not Conversation.objects.exists()


@pytest.mark.django_db
def test_unverified_users_cannot_start_conversation(client):
    alex = User.objects.create_user("alex@umd.edu", PASSWORD, username="alex", first_name="Alex")
    verified_user("maya")
    client.force_login(alex)

    response = client.post("/api/conversations/", {"username": "maya"})

    assert response.status_code == 400


@pytest.mark.django_db
def test_send_list_and_read_messages(client):
    alex = verified_user("alex")
    maya = verified_user("maya")
    client.force_login(alex)
    conversation_id = client.post("/api/conversations/", {"username": "maya"}).json()["id"]

    sent = client.post(
        f"/api/conversations/{conversation_id}/messages/",
        {"body": "  Is this available?  "},
    )

    assert sent.status_code == 201
    assert sent.json()["body"] == "Is this available?"
    assert sent.json()["is_mine"] is True

    client.force_login(maya)
    assert client.get("/api/conversations/unread-count/").json() == {"unread_count": 1}
    listed = client.get(f"/api/conversations/{conversation_id}/messages/")
    assert listed.status_code == 200
    assert listed.json()["messages"][0]["body"] == "Is this available?"
    assert listed.json()["messages"][0]["is_mine"] is False
    assert listed.json()["has_more"] is False

    read = client.post(
        f"/api/conversations/{conversation_id}/read/",
        {"message_id": sent.json()["id"]},
    )
    assert read.status_code == 204
    assert client.get("/api/conversations/unread-count/").json() == {"unread_count": 0}


@pytest.mark.django_db
def test_non_participant_cannot_send_message(client):
    alex = verified_user("alex")
    maya = verified_user("maya")
    outsider = verified_user("outsider")
    client.force_login(alex)
    conversation_id = client.post("/api/conversations/", {"username": maya.username}).json()["id"]

    client.force_login(outsider)
    response = client.post(f"/api/conversations/{conversation_id}/messages/", {"body": "Hello"})

    assert response.status_code == 404
    assert not Message.objects.exists()


@pytest.mark.django_db
def test_empty_message_is_rejected(client):
    alex = verified_user("alex")
    maya = verified_user("maya")
    client.force_login(alex)
    conversation_id = client.post("/api/conversations/", {"username": maya.username}).json()["id"]

    response = client.post(f"/api/conversations/{conversation_id}/messages/", {"body": "   "})

    assert response.status_code == 400
    assert not Message.objects.exists()


@pytest.mark.django_db
def test_message_history_can_load_pages_older_than_fifty(client):
    alex = verified_user("alex")
    maya = verified_user("maya")
    client.force_login(alex)
    conversation_id = client.post("/api/conversations/", {"username": maya.username}).json()["id"]
    conversation = Conversation.objects.get(pk=conversation_id)
    Message.objects.bulk_create(
        [
            Message(conversation=conversation, sender=alex, body=f"Message {number}")
            for number in range(55)
        ]
    )

    newest = client.get(f"/api/conversations/{conversation_id}/messages/").json()
    older = client.get(
        f"/api/conversations/{conversation_id}/messages/",
        {"before_id": newest["messages"][0]["id"]},
    ).json()

    assert len(newest["messages"]) == 50
    assert newest["has_more"] is True
    assert [message["body"] for message in older["messages"]] == [
        f"Message {number}" for number in range(5)
    ]
    assert older["has_more"] is False


@pytest.mark.django_db
def test_message_poll_can_request_only_messages_after_known_id(client):
    alex = verified_user("alex")
    maya = verified_user("maya")
    client.force_login(alex)
    conversation_id = client.post("/api/conversations/", {"username": maya.username}).json()["id"]
    first = client.post(f"/api/conversations/{conversation_id}/messages/", {"body": "First"}).json()
    client.post(f"/api/conversations/{conversation_id}/messages/", {"body": "Second"})

    response = client.get(
        f"/api/conversations/{conversation_id}/messages/", {"after_id": first["id"]}
    )

    assert [message["body"] for message in response.json()["messages"]] == ["Second"]


@pytest.mark.django_db
def test_unread_counts_skip_own_messages_and_start_after_last_read(client):
    alex = verified_user("alex")
    maya = verified_user("maya")
    sam = verified_user("sam")
    with_maya = start_direct_conversation(sender=alex, recipient=maya)
    with_sam = start_direct_conversation(sender=alex, recipient=sam)
    empty = start_direct_conversation(sender=alex, recipient=verified_user("jo"))
    first = send_message(conversation=with_maya, sender=maya, body="One")
    send_message(conversation=with_maya, sender=maya, body="Two")
    send_message(conversation=with_maya, sender=maya, body="Three")
    mark_conversation_read(conversation=with_maya, user=alex, message=first)
    send_message(conversation=with_sam, sender=sam, body="Hi")
    send_message(conversation=with_sam, sender=sam, body="Still there?")
    # Created directly so alex has no read position here (last_read is null); alex's own
    # message still doesn't count as unread.
    own = Message.objects.create(conversation=with_sam, sender=alex, body="Yes")
    client.force_login(alex)

    listed = client.get("/api/conversations/").json()
    inbox = {item["id"]: item for item in listed}
    detail = client.get(f"/api/conversations/{with_maya.pk}/").json()

    # Newest activity first; a conversation without messages stays out of the inbox, though it
    # still opens by its id.
    assert [item["id"] for item in listed] == [with_sam.pk, with_maya.pk]
    assert inbox[with_maya.pk]["unread_count"] == 2
    assert inbox[with_sam.pk]["unread_count"] == 2
    assert client.get(f"/api/conversations/{empty.pk}/").json()["unread_count"] == 0
    assert inbox[with_maya.pk]["latest_message"]["body"] == "Three"
    assert inbox[with_sam.pk]["latest_message"]["id"] == own.pk
    assert inbox[with_sam.pk]["latest_message"]["is_mine"] is True
    assert client.get(f"/api/conversations/{empty.pk}/").json()["latest_message"] is None
    assert detail["unread_count"] == 2
    assert detail["other_user"]["username"] == "maya"
    assert client.get("/api/conversations/unread-count/").json() == {"unread_count": 4}

    client.force_login(maya)
    assert client.get("/api/conversations/unread-count/").json() == {"unread_count": 0}
    client.force_login(verified_user("nobody"))
    assert client.get("/api/conversations/unread-count/").json() == {"unread_count": 0}


@pytest.mark.django_db
def test_sending_more_than_30_messages_a_minute_is_refused(client):
    from apps.messaging.services import MAX_MESSAGES_PER_MINUTE, TOO_FAST

    alex, maya = verified_user("fast-alex"), verified_user("fast-maya")
    chat = start_direct_conversation(sender=alex, recipient=maya)
    for number in range(MAX_MESSAGES_PER_MINUTE):
        send_message(conversation=chat, sender=alex, body=f"msg {number}")
    client.force_login(alex)

    response = client.post(
        f"/api/conversations/{chat.pk}/messages/",
        {"body": "one more"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == TOO_FAST
    # Older messages no longer count.
    Message.objects.filter(sender=alex).update(created_at=timezone.now() - timedelta(minutes=2))
    assert (
        client.post(
            f"/api/conversations/{chat.pk}/messages/",
            {"body": "later"},
            content_type="application/json",
        ).status_code
        == 201
    )


@pytest.mark.django_db
def test_messaging_more_than_20_new_people_an_hour_is_refused_but_ongoing_chats_continue():
    from apps.messaging.services import MAX_NEW_PEOPLE_PER_HOUR, TOO_MANY_NEW_PEOPLE

    alex = verified_user("wide-alex")
    chats = [
        start_direct_conversation(sender=alex, recipient=verified_user(f"wide-{number}"))
        for number in range(MAX_NEW_PEOPLE_PER_HOUR + 1)
    ]
    for chat in chats[:MAX_NEW_PEOPLE_PER_HOUR]:
        send_message(conversation=chat, sender=alex, body="Hey, interested in your item?")

    with pytest.raises(ValidationError, match="new people"):
        send_message(conversation=chats[-1], sender=alex, body="Hey, interested?")
    assert TOO_MANY_NEW_PEOPLE.startswith("You've messaged a lot of new people")

    # Students already messaged can still be written to.
    send_message(conversation=chats[0], sender=alex, body="Following up")
    # And after an hour the limit resets.
    Message.objects.filter(sender=alex).update(created_at=timezone.now() - timedelta(hours=2))
    send_message(conversation=chats[-1], sender=alex, body="Hey, interested?")


@pytest.mark.django_db
def test_replying_never_counts_toward_the_new_people_limit():
    from apps.messaging.services import MAX_NEW_PEOPLE_PER_HOUR

    alex = verified_user("busy-alex")
    for number in range(MAX_NEW_PEOPLE_PER_HOUR):
        chat = start_direct_conversation(sender=alex, recipient=verified_user(f"busy-{number}"))
        send_message(conversation=chat, sender=alex, body="Hi")
    # Alex has hit the limit for starting chats, but a student who asks first gets a reply.
    newcomer = verified_user("busy-newcomer")
    inbound = start_direct_conversation(sender=newcomer, recipient=alex)
    send_message(conversation=inbound, sender=newcomer, body="Is the lamp available?")

    send_message(conversation=inbound, sender=alex, body="Yes!")
