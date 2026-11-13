import pytest
from django.core import mail
from procrastinate import testing
from procrastinate.contrib.django import app

from apps.deals.models import Deal
from apps.deals.services import create_deal
from apps.deals.tests.test_services import listing_for, verified_user
from apps.messaging.services import (
    mark_conversation_read,
    send_message,
    start_direct_conversation,
)
from apps.notifications.services import send_unread_message_email
from apps.trust.services import block_user

MESSAGE_EMAIL = "notifications.send_unread_message_email"


@pytest.fixture
def jobs():
    with app.replace_connector(testing.InMemoryConnector()) as in_memory_app:
        yield in_memory_app.connector


def queued(jobs, task_name):
    return [job for job in jobs.jobs.values() if job["task_name"] == task_name]


@pytest.mark.django_db
def test_only_the_first_unread_message_queues_an_email(jobs):
    alex, maya = verified_user("mail-alex"), verified_user("mail-maya")
    chat = start_direct_conversation(sender=alex, recipient=maya)

    first = send_message(conversation=chat, sender=alex, body="Is this still available?")
    send_message(conversation=chat, sender=alex, body="I can meet today")
    send_message(conversation=chat, sender=alex, body="Or tomorrow")
    emails = queued(jobs, MESSAGE_EMAIL)
    assert len(emails) == 1
    assert emails[0]["args"] == {"recipient_id": maya.pk, "message_id": first.pk}
    assert emails[0]["scheduled_at"] is not None  # sent a few minutes later, if still unread

    # Once Maya has read it, the next message starts a new unread stretch.
    mark_conversation_read(conversation=chat, user=maya)
    send_message(conversation=chat, sender=alex, body="Hello?")
    assert len(queued(jobs, MESSAGE_EMAIL)) == 2


@pytest.mark.django_db
def test_replying_doesnt_email_yourself_and_emails_the_other_side_once(jobs):
    alex, maya = verified_user("reply-alex"), verified_user("reply-maya")
    chat = start_direct_conversation(sender=alex, recipient=maya)
    send_message(conversation=chat, sender=alex, body="Hi")
    send_message(conversation=chat, sender=maya, body="Hey!")  # Maya replying reads Alex's

    emails = queued(jobs, MESSAGE_EMAIL)
    assert [job["args"]["recipient_id"] for job in emails] == [maya.pk, alex.pk]


@pytest.mark.django_db
def test_the_email_goes_out_only_if_still_unread(settings):
    alex, maya = verified_user("send-alex"), verified_user("send-maya")
    chat = start_direct_conversation(sender=alex, recipient=maya)
    message = send_message(conversation=chat, sender=alex, body="Private details here")

    send_unread_message_email(recipient_id=maya.pk, message_id=message.pk)
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == [maya.email]
    assert email.subject == "Tanu: New message from @send-alex"
    assert f"{settings.WEB_APP_URL}/inbox/{chat.pk}" in email.body
    assert "Private details" not in email.body  # the message stays in Tanu

    mail.outbox.clear()
    mark_conversation_read(conversation=chat, user=maya)
    send_unread_message_email(recipient_id=maya.pk, message_id=message.pk)
    assert mail.outbox == []


@pytest.mark.django_db
def test_no_email_for_blocked_or_deactivated_recipients():
    alex, maya, sam = (verified_user(n) for n in ("skip-alex", "skip-maya", "skip-sam"))
    to_maya = start_direct_conversation(sender=alex, recipient=maya)
    to_sam = start_direct_conversation(sender=alex, recipient=sam)
    for_maya = send_message(conversation=to_maya, sender=alex, body="Hi")
    for_sam = send_message(conversation=to_sam, sender=alex, body="Hi")
    block_user(blocker=maya, blocked=alex)
    sam.is_active = False
    sam.save()

    send_unread_message_email(recipient_id=maya.pk, message_id=for_maya.pk)
    send_unread_message_email(recipient_id=sam.pk, message_id=for_sam.pk)
    assert mail.outbox == []


@pytest.mark.django_db
def test_deal_moves_email_the_side_they_concern(jobs):
    seller, buyer = verified_user("deal-mail-seller"), verified_user("deal-mail-buyer")

    deal = create_deal(listing=listing_for(seller), buyer=buyer, kind=Deal.Kind.BUY_NOW)

    notice = seller.notifications.get()
    emails = queued(jobs, "notifications.send_email")
    assert [job["args"] for job in emails] == [{"notification_id": notice.pk}]
    assert not queued(jobs, MESSAGE_EMAIL)  # the request isn't a chat message
    assert deal.conversation.messages.count() == 0
