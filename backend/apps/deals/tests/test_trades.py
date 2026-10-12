import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.deals import services
from apps.deals.models import Deal, DealOffer
from apps.deals.tests.test_services import listing_for, verified_user
from apps.listings.models import Listing
from apps.messaging.models import Message


def trade_request(seller_name="trade-seller", buyer_name="trade-buyer", **kwargs):
    seller = verified_user(seller_name)
    buyer = verified_user(buyer_name)
    listing = listing_for(seller, price_cents=6000)
    deal = services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.TRADE, **kwargs)
    return seller, buyer, listing, deal


def status_of(*listings):
    return [Listing.objects.get(pk=listing.pk).status for listing in listings]


@pytest.mark.django_db
def test_seller_builds_the_package_and_buyer_acceptance_locks_every_item():
    seller, buyer, listing, deal = trade_request()
    jacket = listing_for(buyer, price_cents=4000)
    boots = listing_for(buyer, price_cents=3000)
    assert deal.status == Deal.Status.AWAITING_SELLER
    assert deal.offers.count() == 0

    with pytest.raises(ValidationError, match="Choose items"):
        services.accept_deal(deal=deal, actor=seller)

    services.counter_trade(
        deal=deal,
        actor=seller,
        item_ids=[jacket.pk, boots.pk],
        cash_cents=1500,
        cash_payer=DealOffer.CashPayer.BUYER,
    )
    deal.refresh_from_db()
    assert deal.status == Deal.Status.AWAITING_BUYER
    assert {item.pk for item in services.trade_items(deal)} == {jacket.pk, boots.pk}

    services.accept_deal(deal=deal, actor=buyer)
    deal.refresh_from_db()
    assert deal.status == Deal.Status.PENDING
    assert deal.agreed_amount_cents == 1500
    assert status_of(listing, jacket, boots) == [Listing.Status.PENDING] * 3

    services.confirm_handoff(deal=deal, actor=buyer)
    services.confirm_handoff(deal=deal, actor=seller)
    assert status_of(listing, jacket, boots) == [Listing.Status.SOLD] * 3


@pytest.mark.django_db
def test_buyer_can_counter_with_a_different_package_and_the_seller_accepts_it():
    seller, buyer, listing, deal = trade_request()
    jacket = listing_for(buyer)
    boots = listing_for(buyer)
    services.counter_trade(deal=deal, actor=seller, item_ids=[jacket.pk, boots.pk])

    services.counter_trade(
        deal=deal,
        actor=buyer,
        item_ids=[jacket.pk],
        cash_cents=500,
        cash_payer=DealOffer.CashPayer.BUYER,
    )
    deal.refresh_from_db()
    assert deal.status == Deal.Status.AWAITING_SELLER

    with pytest.raises(PermissionDenied):
        services.counter_trade(deal=deal, actor=buyer, item_ids=[boots.pk])

    services.accept_deal(deal=deal, actor=seller)
    assert status_of(jacket, boots) == [Listing.Status.PENDING, Listing.Status.AVAILABLE]


@pytest.mark.django_db
def test_packages_only_take_the_buyers_available_items_and_explicit_cash():
    seller, buyer, listing, deal = trade_request()
    stranger = verified_user("trade-stranger")
    mine = listing_for(buyer)
    sellers_own = listing_for(seller)
    someone_elses = listing_for(stranger)
    many = [listing_for(buyer).pk for _ in range(6)]

    for item_ids in ([sellers_own.pk], [someone_elses.pk], [listing.pk], many, []):
        with pytest.raises(ValidationError):
            services.counter_trade(deal=deal, actor=seller, item_ids=item_ids)
    with pytest.raises(ValidationError, match="who adds the cash"):
        services.counter_trade(deal=deal, actor=seller, item_ids=[mine.pk], cash_cents=100)
    with pytest.raises(ValidationError, match="new trade offer"):
        services.counter_offer(deal=deal, actor=seller, amount_cents=5000)


@pytest.mark.django_db
def test_an_item_that_sold_elsewhere_blocks_acceptance():
    seller, buyer, listing, deal = trade_request()
    jacket = listing_for(buyer)
    services.counter_trade(deal=deal, actor=seller, item_ids=[jacket.pk])

    other_buyer = verified_user("trade-other-buyer")
    elsewhere = services.create_deal(listing=jacket, buyer=other_buyer, kind=Deal.Kind.BUY_NOW)
    services.accept_deal(deal=elsewhere, actor=buyer)

    with pytest.raises(ValidationError, match="no longer available"):
        services.accept_deal(deal=deal, actor=buyer)
    assert status_of(listing) == [Listing.Status.AVAILABLE]


@pytest.mark.django_db
def test_accepting_a_trade_makes_other_requests_for_the_buyers_items_backups():
    seller, buyer, listing, deal = trade_request()
    jacket = listing_for(buyer)
    other_buyer = verified_user("trade-backup-buyer")
    other_request = services.create_deal(
        listing=jacket, buyer=other_buyer, kind=Deal.Kind.OFFER, amount_cents=2000
    )
    services.counter_trade(deal=deal, actor=seller, item_ids=[jacket.pk])
    services.accept_deal(deal=deal, actor=buyer)

    other_request.refresh_from_db()
    assert other_request.status == Deal.Status.BACKUP


@pytest.mark.django_db
def test_either_side_can_cancel_and_every_item_comes_back():
    seller, buyer, listing, deal = trade_request()
    jacket = listing_for(buyer)
    services.counter_trade(deal=deal, actor=seller, item_ids=[jacket.pk])
    services.accept_deal(deal=deal, actor=buyer)

    services.cancel_deal(deal=deal, actor=seller)
    assert status_of(listing, jacket) == [Listing.Status.AVAILABLE] * 2


@pytest.mark.django_db
def test_asap_requests_are_flagged_for_the_seller():
    seller, buyer, listing, deal = trade_request(asap=True)

    assert deal.asap is True
    assert (
        "as soon as possible" in Message.objects.filter(conversation=deal.conversation).last().body
    )
