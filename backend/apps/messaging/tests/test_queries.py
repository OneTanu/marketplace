"""The messaging endpoints the web app polls must cost a fixed number of queries, however many
conversations and messages a student has."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.messaging.services import send_message, start_direct_conversation

from .test_api import verified_user


def add_conversations(alex, count, *, start):
    """Give alex `count` more conversations, each with a few messages in both directions."""
    conversations = []
    for number in range(start, start + count):
        other = verified_user(f"student{number}")
        conversation = start_direct_conversation(sender=alex, recipient=other)
        for _ in range(3):
            send_message(conversation=conversation, sender=other, body="Still available?")
            send_message(conversation=conversation, sender=alex, body="Yes")
        send_message(conversation=conversation, sender=other, body="On my way")
        conversations.append(conversation)
    return conversations


def query_count(client, url):
    with CaptureQueriesContext(connection) as queries:
        response = client.get(url)
    assert response.status_code == 200
    return len(queries)


# Each bound includes the 2 queries that load the session and the signed-in user.
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("url", "max_queries"),
    [
        ("/api/conversations/", 7),
        ("/api/conversations/unread-count/", 3),
        ("/api/conversations/{id}/", 7),
        ("/api/conversations/{id}/messages/", 5),
    ],
)
def test_polled_endpoints_use_constant_queries(
    client, django_assert_max_num_queries, url, max_queries
):
    alex = verified_user("alex")
    (first,) = add_conversations(alex, 1, start=1)
    url = url.format(id=first.pk)
    client.force_login(alex)

    with django_assert_max_num_queries(max_queries):
        few = query_count(client, url)
    add_conversations(alex, 4, start=2)
    other = first.participants.exclude(pk=alex.pk).get()
    for _ in range(5):
        send_message(conversation=first, sender=other, body="Hello?")
    many = query_count(client, url)

    assert many == few
