from datetime import timedelta

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts import services
from apps.accounts.models import Follow
from apps.deals import services as deal_services
from apps.deals.models import Deal
from apps.deals.tests.test_services import PASSWORD, listing_for, verified_user
from apps.listings.models import Listing
from apps.messaging.services import send_message, start_direct_conversation
from apps.notifications.models import Notification
from apps.trust import services as trust_services
from apps.trust.models import Report
from apps.trust.tests.test_moderation import report_listing, staff


def status_of(*listings):
    return [Listing.objects.get(pk=listing.pk).status for listing in listings]


@pytest.mark.django_db
def test_deactivating_withdraws_from_deals_hides_listings_and_signs_out():
    me = verified_user("closing-me")
    buyer = verified_user("closing-buyer")
    seller = verified_user("closing-seller")
    available = listing_for(me)
    pending = listing_for(me)
    sold = listing_for(me)
    Listing.objects.filter(pk=sold.pk).update(status=Listing.Status.SOLD)
    sale = deal_services.create_deal(listing=pending, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    deal_services.accept_deal(deal=sale, actor=me)
    request = deal_services.create_deal(
        listing=listing_for(seller), buyer=me, kind=Deal.Kind.BUY_NOW
    )

    with pytest.raises(ValidationError, match="password"):
        services.deactivate_account(user=me, password="wrong")
    services.deactivate_account(user=me, password=PASSWORD, reason="Graduating")

    me.refresh_from_db()
    assert me.is_active is False
    assert me.deactivated_at is not None
    assert me.deactivation_reason == "Graduating"
    sale.refresh_from_db()
    request.refresh_from_db()
    assert (sale.status, request.status) == (Deal.Status.CANCELED, Deal.Status.CANCELED)
    assert status_of(available, pending, sold) == [
        Listing.Status.REMOVED,
        Listing.Status.REMOVED,
        Listing.Status.SOLD,
    ]
    assert Listing.objects.get(pk=available.pk).removed_by == Listing.RemovedBy.ACCOUNT
    assert Notification.objects.filter(user=me, kind=Notification.Kind.ACCOUNT).exists()


@pytest.mark.django_db
def test_backup_buyers_promoted_during_deactivation_are_withdrawn_too():
    me = verified_user("promote-me")
    first = verified_user("promote-first")
    second = verified_user("promote-second")
    listing = listing_for(me)
    primary = deal_services.create_deal(listing=listing, buyer=first, kind=Deal.Kind.BUY_NOW)
    backup = deal_services.create_deal(listing=listing, buyer=second, kind=Deal.Kind.BUY_NOW)
    deal_services.accept_deal(deal=primary, actor=me)

    services.deactivate_account(user=me, password=PASSWORD)

    assert not Deal.objects.filter(
        pk__in=[primary.pk, backup.pk], status__in=deal_services.OPEN_STATUSES
    ).exists()
    assert status_of(listing) == [Listing.Status.REMOVED]


@pytest.mark.django_db
def test_a_confirmed_handoff_blocks_deactivation_until_settled():
    me = verified_user("blocked-me")
    buyer = verified_user("blocked-buyer")
    listing = listing_for(me)
    deal = deal_services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    deal_services.accept_deal(deal=deal, actor=me)
    deal_services.confirm_handoff(deal=deal, actor=buyer)

    assert [d.pk for d in services.deactivation_preview(me)["blockers"]] == [deal.pk]
    with pytest.raises(ValidationError, match="confirmed or disputed"):
        services.deactivate_account(user=me, password=PASSWORD)
    me.refresh_from_db()
    assert me.is_active is True
    assert status_of(listing) == [Listing.Status.PENDING]

    deal_services.confirm_handoff(deal=deal, actor=me)
    services.deactivate_account(user=me, password=PASSWORD)


@pytest.mark.django_db
def test_logging_back_in_reactivates_and_restores_listings():
    me = verified_user("return-me")
    listing = listing_for(me)
    services.deactivate_account(user=me, password=PASSWORD)

    for email, password in [("return-me@umd.edu", "wrong"), ("nobody@umd.edu", PASSWORD)]:
        with pytest.raises(ValidationError, match="couldn't reactivate"):
            services.reactivate_account(email=email, password=password)

    services.reactivate_account(email="Return-Me@umd.edu", password=PASSWORD)
    me.refresh_from_db()
    assert (me.is_active, me.deactivated_at) == (True, None)
    assert status_of(listing) == [Listing.Status.AVAILABLE]
    assert Listing.objects.get(pk=listing.pk).removed_by == ""


@pytest.mark.django_db
def test_moderation_keeps_suspended_and_banned_accounts_off():
    senior = staff("close-senior", senior=True)
    suspended = verified_user("close-suspended")
    banned = verified_user("close-banned")
    for user in (suspended, banned):
        case = report_listing(verified_user(f"{user.username}-r"), listing_for(user)).case
        if user is suspended:
            trust_services.suspend_user(
                staff=senior,
                case=case,
                user=user,
                reason="Scam",
                until=timezone.now() + timedelta(days=3),
            )
        else:
            trust_services.ban_user(staff=senior, case=case, user=user, reason="Weapons")
        with pytest.raises(ValidationError, match="can't be reactivated"):
            services.reactivate_account(email=user.email, password=PASSWORD)


@pytest.mark.django_db
def test_a_suspension_ending_does_not_undo_a_deactivation():
    senior = staff("undo-senior", senior=True)
    me = verified_user("undo-me")
    case = report_listing(
        verified_user("undo-reporter"), listing_for(me), reason=Report.Reason.SPAM
    ).case
    services.deactivate_account(user=me, password=PASSWORD)
    restriction = trust_services.suspend_user(
        staff=senior, case=case, user=me, reason="Spam", until=timezone.now() + timedelta(days=1)
    )
    restriction.expires_at = timezone.now() - timedelta(seconds=1)
    restriction.save(update_fields=["expires_at"])

    trust_services.end_expired_suspension(restriction_id=restriction.pk)

    me.refresh_from_db()
    assert me.is_active is False


@pytest.mark.django_db
def test_conversations_turn_read_only_and_follows_stop_counting(client):
    me = verified_user("quiet-me")
    friend = verified_user("quiet-friend")
    conversation = start_direct_conversation(sender=friend, recipient=me)
    send_message(conversation=conversation, sender=me, body="see you at the library")
    Follow.objects.create(follower=me, following=friend)
    services.deactivate_account(user=me, password=PASSWORD)

    with pytest.raises(ValidationError, match="isn't available"):
        send_message(conversation=conversation, sender=friend, body="hello?")
    client.force_login(friend)
    other = client.get(f"/api/conversations/{conversation.pk}/").json()["other_user"]
    assert other["is_available"] is False
    assert client.get(f"/api/users/{friend.username}/").json()["follower_count"] == 0
    assert client.get(f"/api/users/{me.username}/").status_code == 404


@pytest.mark.django_db
def test_deactivate_and_reactivate_through_the_api(client):
    cache.clear()
    me = verified_user("api-close-me")
    listing_for(me)
    client.force_login(me)

    preview = client.get("/api/me/deactivation/").json()
    assert preview == {"blockers": [], "open_deals": 0, "listings_to_hide": 1}
    wrong = client.post(
        "/api/me/deactivate/", {"password": "nope"}, content_type="application/json"
    )
    assert wrong.status_code == 400
    assert "password" in wrong.json()
    closed = client.post(
        "/api/me/deactivate/", {"password": PASSWORD}, content_type="application/json"
    )
    assert closed.status_code == 204
    assert client.get("/api/me/").status_code == 403

    back = client.post(
        "/api/account/reactivate/",
        {"email": me.email, "password": PASSWORD},
        content_type="application/json",
    )
    assert back.status_code == 204
    assert client.login(username=me.email, password=PASSWORD)


@pytest.mark.django_db
def test_reactivation_is_rate_limited(client):
    cache.clear()
    for _ in range(10):
        client.post(
            "/api/account/reactivate/",
            {"email": "guess@umd.edu", "password": "guess"},
            content_type="application/json",
        )
    limited = client.post(
        "/api/account/reactivate/",
        {"email": "guess@umd.edu", "password": "guess"},
        content_type="application/json",
    )
    assert limited.status_code == 429
    cache.clear()
