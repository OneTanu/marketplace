import pytest
from django.core import mail

from apps.deals.tests.test_services import verified_user
from apps.notifications import services
from apps.notifications.models import Notification


@pytest.mark.django_db
def test_list_count_and_mark_read(client):
    me = verified_user("notify-me")
    other = verified_user("notify-other")
    first = services.notify(me, kind=Notification.Kind.DEAL, title="One", link="/deals")
    services.notify(me, kind=Notification.Kind.DEAL, title="Two")
    services.notify(other, kind=Notification.Kind.DEAL, title="Not mine")
    client.force_login(me)

    assert [row["title"] for row in client.get("/api/notifications/").json()] == ["Two", "One"]
    assert client.get("/api/notifications/unread-count/").json() == {"unread": 2}
    marked = client.post(
        "/api/notifications/read/", {"ids": [first.pk]}, content_type="application/json"
    )
    assert marked.json() == {"unread": 1}
    assert client.post("/api/notifications/read/", {}, content_type="application/json").json() == {
        "unread": 0
    }


@pytest.mark.django_db
def test_email_job_sends_the_notification_with_its_link():
    me = verified_user("notify-email")
    notification = services.notify(
        me, kind=Notification.Kind.MODERATION_NOTICE, title="Heads up", body="Body", link="/x"
    )

    services.send_email(notification_id=notification.pk)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Tanu: Heads up"
    assert mail.outbox[0].to == [me.email]
    assert "/x" in mail.outbox[0].body
