from datetime import timedelta

import pytest
from allauth.account.models import EmailAddress
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.deals import services
from apps.deals.models import Deal, DealEvent, DealOffer, HandoffConfirmation
from apps.listings.models import Category, Listing
from apps.schools.models import School

PASSWORD = "pw-123456789"


def verified_user(username):
    school = School.objects.get(slug="umd")
    email = f"{username}@umd.edu"
    user = User.objects.create_user(email, PASSWORD, username=username, school=school)
    EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
    return user


def listing_for(seller, price_cents=5000):
    return Listing.objects.create(
        school=seller.school,
        seller=seller,
        category=Category.objects.get(slug="women-coats-jackets"),
        title="Puffer jacket",
        price_cents=price_cents,
    )


@pytest.mark.django_db
def test_offer_starts_awaiting_seller_with_conversation_and_event():
    seller = verified_user("seller")
    buyer = verified_user("buyer")
    listing = listing_for(seller)

    deal = services.create_deal(
        listing=listing, buyer=buyer, kind=Deal.Kind.OFFER, amount_cents=4200
    )

    assert deal.status == Deal.Status.AWAITING_SELLER
    assert deal.current_amount_cents == 4200
    assert deal.conversation.participants.count() == 2
    assert DealOffer.objects.get(deal=deal).offered_by == buyer
    assert DealEvent.objects.get(deal=deal).event_type == "request_created"
    assert deal.response_deadline > timezone.now()


@pytest.mark.django_db
def test_buy_now_uses_listing_price_and_duplicate_active_request_is_rejected():
    seller = verified_user("seller")
    buyer = verified_user("buyer")
    listing = listing_for(seller, price_cents=7300)

    deal = services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)

    assert deal.current_amount_cents == 7300
    with pytest.raises(ValidationError):
        services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)


@pytest.mark.django_db
def test_seller_can_counter_then_buyer_accepts_and_other_buyer_becomes_backup():
    seller = verified_user("seller")
    buyer = verified_user("buyer")
    backup = verified_user("backup")
    listing = listing_for(seller)
    deal = services.create_deal(
        listing=listing, buyer=buyer, kind=Deal.Kind.OFFER, amount_cents=3500
    )
    other = services.create_deal(
        listing=listing, buyer=backup, kind=Deal.Kind.OFFER, amount_cents=4000
    )

    services.counter_offer(deal=deal, actor=seller, amount_cents=4500)
    services.accept_deal(deal=deal, actor=buyer)

    deal.refresh_from_db()
    other.refresh_from_db()
    listing.refresh_from_db()
    assert deal.status == Deal.Status.PENDING
    assert deal.agreed_amount_cents == 4500
    assert listing.status == Listing.Status.PENDING
    assert other.status == Deal.Status.BACKUP


@pytest.mark.django_db
def test_wrong_party_cannot_accept_current_offer():
    seller = verified_user("seller")
    buyer = verified_user("buyer")
    deal = services.create_deal(
        listing=listing_for(seller), buyer=buyer, kind=Deal.Kind.OFFER, amount_cents=3500
    )

    with pytest.raises(PermissionDenied):
        services.accept_deal(deal=deal, actor=buyer)


@pytest.mark.django_db
def test_cancel_pending_returns_listing_to_available():
    seller = verified_user("seller")
    buyer = verified_user("buyer")
    listing = listing_for(seller)
    deal = services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    services.accept_deal(deal=deal, actor=seller)

    services.cancel_deal(deal=deal, actor=buyer)

    deal.refresh_from_db()
    listing.refresh_from_db()
    assert deal.status == Deal.Status.CANCELED
    assert listing.status == Listing.Status.AVAILABLE


@pytest.mark.django_db
def test_both_handoff_confirmations_complete_deal_and_mark_listing_sold():
    seller = verified_user("seller")
    buyer = verified_user("buyer")
    listing = listing_for(seller)
    deal = services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    services.accept_deal(deal=deal, actor=seller)

    services.confirm_handoff(deal=deal, actor=buyer)
    deal.refresh_from_db()
    listing.refresh_from_db()
    assert deal.status == Deal.Status.PENDING
    assert listing.status == Listing.Status.PENDING

    services.confirm_handoff(deal=deal, actor=seller)
    deal.refresh_from_db()
    listing.refresh_from_db()
    assert deal.status == Deal.Status.COMPLETED
    assert listing.status == Listing.Status.SOLD
    assert HandoffConfirmation.objects.filter(deal=deal).count() == 2


@pytest.mark.django_db
def test_expired_pending_deal_returns_listing_to_available():
    seller = verified_user("seller")
    buyer = verified_user("buyer")
    listing = listing_for(seller)
    deal = services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    services.accept_deal(deal=deal, actor=seller)
    Deal.objects.filter(pk=deal.pk).update(handoff_deadline=timezone.now() - timedelta(seconds=1))

    services.expire(deal_id=deal.pk, expected_status=Deal.Status.PENDING)

    deal.refresh_from_db()
    listing.refresh_from_db()
    assert deal.status == Deal.Status.EXPIRED
    assert listing.status == Listing.Status.AVAILABLE


@pytest.mark.django_db
def test_one_confirmation_prevents_cancel_and_automatic_release():
    seller = verified_user("seller")
    buyer = verified_user("buyer")
    listing = listing_for(seller)
    deal = services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    services.accept_deal(deal=deal, actor=seller)
    services.confirm_handoff(deal=deal, actor=buyer)

    with pytest.raises(ValidationError):
        services.cancel_deal(deal=deal, actor=seller)

    Deal.objects.filter(pk=deal.pk).update(handoff_deadline=timezone.now() - timedelta(seconds=1))
    services.expire(deal_id=deal.pk, expected_status=Deal.Status.PENDING)

    deal.refresh_from_db()
    listing.refresh_from_db()
    assert deal.status == Deal.Status.PENDING
    assert deal.handoff_deadline is None
    assert listing.status == Listing.Status.PENDING
    assert deal.events.filter(event_type="confirmation_stalled").exists()


@pytest.mark.django_db
def test_completion_closes_backup_requests():
    seller = verified_user("seller")
    buyer = verified_user("buyer")
    backup_buyer = verified_user("backup")
    listing = listing_for(seller)
    deal = services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    backup = services.create_deal(
        listing=listing, buyer=backup_buyer, kind=Deal.Kind.OFFER, amount_cents=4000
    )
    services.accept_deal(deal=deal, actor=seller)

    services.confirm_handoff(deal=deal, actor=buyer)
    services.confirm_handoff(deal=deal, actor=seller)

    backup.refresh_from_db()
    assert backup.status == Deal.Status.EXPIRED
    assert backup.events.filter(event_type="closed_listing_sold").exists()
