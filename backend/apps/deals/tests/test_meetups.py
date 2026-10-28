from datetime import time, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.deals import services
from apps.deals.models import Deal, MeetupProposal
from apps.deals.tests.test_services import listing_for, verified_user
from apps.schools.models import MeetingSpot


def seller_with_meetups(username):
    seller = verified_user(username)
    spot = MeetingSpot.objects.create(
        school=seller.school, name=f"{username} desk", directions="Inside by the desk."
    )
    services.update_meetup_preferences(
        user=seller,
        meeting_spot_ids=[spot.pk],
        windows=[
            {"weekday": weekday, "start_time": time(0, 0), "end_time": time(23, 59)}
            for weekday in range(7)
        ],
        overrides=[],
    )
    return seller, spot


def offer_with_times(seller, spot, buyer, count=2):
    slots = services.meetup_slots(seller=seller)
    return services.create_deal(
        listing=listing_for(seller),
        buyer=buyer,
        kind=Deal.Kind.OFFER,
        amount_cents=4000,
        meeting_spot=spot,
        proposed_starts_at=slots[:count],
    )


def statuses(deal):
    return sorted(deal.meetup_proposals.values_list("status", flat=True))


@pytest.mark.django_db
def test_seller_suggesting_another_time_hands_the_turn_to_the_buyer():
    seller, spot = seller_with_meetups("turn-seller")
    buyer = verified_user("turn-buyer")
    deal = offer_with_times(seller, spot, buyer)
    later = services.meetup_slots(seller=seller)[5]

    services.propose_meetup(deal=deal, actor=seller, meeting_spot=spot, starts_at=later)
    deal.refresh_from_db()
    assert deal.status == Deal.Status.AWAITING_BUYER

    services.accept_deal(deal=deal, actor=buyer)
    deal.refresh_from_db()
    assert deal.status == Deal.Status.PENDING
    accepted = deal.meetup_proposals.get(status=MeetupProposal.Status.ACCEPTED)
    assert accepted.starts_at == later


@pytest.mark.django_db
def test_buyer_replacing_their_own_times_keeps_the_turn_with_the_seller():
    seller, spot = seller_with_meetups("wait-seller")
    buyer = verified_user("wait-buyer")
    deal = offer_with_times(seller, spot, buyer)

    services.propose_meetup(
        deal=deal, actor=buyer, meeting_spot=spot, starts_at=services.meetup_slots(seller=seller)[4]
    )
    deal.refresh_from_db()
    assert deal.status == Deal.Status.AWAITING_SELLER
    assert statuses(deal).count(MeetupProposal.Status.PENDING) == 1


@pytest.mark.django_db
def test_price_counter_keeps_one_time_and_buyer_acceptance_confirms_it():
    seller, spot = seller_with_meetups("counter-seller")
    buyer = verified_user("counter-buyer")
    deal = offer_with_times(seller, spot, buyer)
    first, second = deal.meetup_proposals.order_by("starts_at")

    with pytest.raises(ValidationError):
        services.counter_offer(deal=deal, actor=seller, amount_cents=4500)

    services.counter_offer(deal=deal, actor=seller, amount_cents=4500, meetup_proposal=second)
    services.accept_deal(deal=deal, actor=buyer)

    deal.refresh_from_db()
    second.refresh_from_db()
    assert deal.status == Deal.Status.PENDING
    assert deal.agreed_amount_cents == 4500
    assert second.status == MeetupProposal.Status.ACCEPTED


@pytest.mark.django_db
def test_stale_times_must_be_replaced_before_accepting():
    seller, spot = seller_with_meetups("stale-seller")
    buyer = verified_user("stale-buyer")
    deal = offer_with_times(seller, spot, buyer, count=1)
    deal.meetup_proposals.update(starts_at=timezone.now() - timedelta(minutes=5))

    with pytest.raises(ValidationError, match="passed"):
        services.accept_deal(deal=deal, actor=seller)

    services.propose_meetup(
        deal=deal, actor=buyer, meeting_spot=spot, starts_at=services.meetup_slots(seller=seller)[0]
    )
    services.accept_deal(deal=deal, actor=seller)
    deal.refresh_from_db()
    assert deal.status == Deal.Status.PENDING
    assert deal.meetup_proposals.filter(status=MeetupProposal.Status.ACCEPTED).exists()


@pytest.mark.django_db
def test_a_reschedule_can_extend_the_handoff_once_and_only_so_far():
    seller, spot = seller_with_meetups("deadline-seller")
    buyer = verified_user("deadline-buyer")
    deal = offer_with_times(seller, spot, buyer, count=1)
    services.accept_deal(deal=deal, actor=seller)
    # A short deadline, so slots both inside and beyond the extension window exist.
    deadline = timezone.now() + timedelta(hours=2)
    Deal.objects.filter(pk=deal.pk).update(handoff_deadline=deadline)
    slots = services.meetup_slots(seller=seller)
    beyond = next(slot for slot in slots if slot > deadline + services.MAX_HANDOFF_EXTENSION)
    within = next(slot for slot in slots if deadline < slot <= deadline + timedelta(hours=24))
    later = next(slot for slot in slots if slot > within)

    # More than 48 hours past the deadline: refused outright.
    with pytest.raises(ValidationError, match="48 hours"):
        services.propose_meetup(deal=deal, actor=buyer, meeting_spot=spot, starts_at=beyond)

    # Within the window: allowed, and the old meetup stands until the seller accepts.
    accepted_before = deal.meetup_proposals.get(status=MeetupProposal.Status.ACCEPTED)
    proposal = services.propose_meetup(deal=deal, actor=buyer, meeting_spot=spot, starts_at=within)
    accepted_before.refresh_from_db()
    assert accepted_before.status == MeetupProposal.Status.ACCEPTED
    services.accept_meetup(deal=deal, actor=seller, proposal=proposal)
    deal.refresh_from_db()
    accepted_before.refresh_from_db()
    assert accepted_before.status == MeetupProposal.Status.SUPERSEDED
    assert deal.handoff_extensions == 1
    assert deal.handoff_deadline == within + services.HANDOFF_CONFIRM_GRACE
    assert deal.events.filter(event_type="handoff_extended").count() == 1

    # A second extension is refused, so rescheduling can't hold the listing indefinitely.
    if later > deal.handoff_deadline:
        with pytest.raises(ValidationError, match="already extended"):
            services.propose_meetup(deal=deal, actor=seller, meeting_spot=spot, starts_at=later)


@pytest.mark.django_db
def test_an_unanswered_reschedule_expires_and_the_confirmed_meetup_stands():
    seller, spot = seller_with_meetups("lapse-seller")
    buyer = verified_user("lapse-buyer")
    deal = offer_with_times(seller, spot, buyer, count=1)
    services.accept_deal(deal=deal, actor=seller)
    confirmed = deal.meetup_proposals.get(status=MeetupProposal.Status.ACCEPTED)
    slot = next(s for s in services.meetup_slots(seller=seller) if s != confirmed.starts_at)
    proposal = services.propose_meetup(deal=deal, actor=buyer, meeting_spot=spot, starts_at=slot)
    MeetupProposal.objects.filter(pk=proposal.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )

    with pytest.raises(ValidationError, match="expired"):
        services.accept_meetup(deal=deal, actor=seller, proposal=proposal)
    confirmed.refresh_from_db()
    assert confirmed.status == MeetupProposal.Status.ACCEPTED


@pytest.mark.django_db
def test_declining_withdraws_pending_times():
    seller, spot = seller_with_meetups("decline-seller")
    buyer = verified_user("decline-buyer")
    deal = offer_with_times(seller, spot, buyer)

    services.decline_deal(deal=deal, actor=seller)

    assert statuses(deal) == [MeetupProposal.Status.WITHDRAWN] * 2


@pytest.mark.django_db
def test_rescheduling_to_the_confirmed_meetup_is_refused():
    seller, spot = seller_with_meetups("same-seller")
    buyer = verified_user("same-buyer")
    deal = offer_with_times(seller, spot, buyer, count=1)
    services.accept_deal(deal=deal, actor=seller)
    confirmed = deal.meetup_proposals.get(status=MeetupProposal.Status.ACCEPTED)

    with pytest.raises(ValidationError, match="already the confirmed meetup"):
        services.propose_meetup(
            deal=deal, actor=buyer, meeting_spot=spot, starts_at=confirmed.starts_at
        )
