from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.accounts.adapter import AccountAdapter
from apps.deals import services as deal_services
from apps.deals.models import Deal
from apps.deals.tests.test_services import listing_for, verified_user
from apps.listings import services as listing_services
from apps.listings.models import Listing
from apps.listings.services import FeedFilters, browse_listings
from apps.messaging.services import send_message, start_direct_conversation
from apps.schools.models import School
from apps.trust import checks, services
from apps.trust.models import ModerationAction, ModerationCase, ModeratorScope, Report

Kind = services.Kind
WEAPON = Report.ProhibitedCategory.WEAPON


def staff(username, *, senior=False):
    user = verified_user(username)
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    role = services.SENIOR_MODERATOR if senior else services.MODERATOR
    user.groups.add(Group.objects.get(name=role))
    return user


def report_listing(reporter, listing, reason=Report.Reason.PROHIBITED_ITEM, **kwargs):
    return services.create_report(
        reporter=reporter,
        target_type=Report.TargetType.LISTING,
        target_id=listing.pk,
        reason=reason,
        **kwargs,
    )


def status_of(listing):
    return Listing.objects.get(pk=listing.pk).status


# --- Reports ---


@pytest.mark.django_db
def test_reports_about_the_same_listing_share_one_case_with_a_snapshot():
    seller = verified_user("rep-seller")
    listing = listing_for(seller)
    first = report_listing(verified_user("rep-a"), listing, details="Looks fake")
    second = report_listing(verified_user("rep-b"), listing, reason=Report.Reason.COUNTERFEIT)

    assert first.case == second.case
    assert first.case.subject_user == seller
    assert first.case.priority == ModerationCase.Priority.HIGH
    snapshot = first.evidence.get()
    assert snapshot.kind == "listing"
    assert snapshot.data["title"] == listing.title


@pytest.mark.django_db
def test_students_cant_report_themselves_twice_or_endlessly(monkeypatch):
    seller = verified_user("limit-seller")
    reporter = verified_user("limit-reporter")
    listing = listing_for(seller)

    with pytest.raises(ValidationError, match="yourself"):
        report_listing(seller, listing)
    report_listing(reporter, listing)
    with pytest.raises(ValidationError, match="already reported"):
        report_listing(reporter, listing)

    monkeypatch.setattr(services, "REPORTS_PER_DAY", 1)
    with pytest.raises(ValidationError, match="Try again tomorrow"):
        report_listing(reporter, listing_for(seller))


@pytest.mark.django_db
def test_a_conversation_report_only_carries_the_chosen_messages():
    reporter = verified_user("convo-reporter")
    other = verified_user("convo-other")
    conversation = start_direct_conversation(sender=other, recipient=reporter)
    rude = send_message(conversation=conversation, sender=other, body="rude message")
    send_message(conversation=conversation, sender=other, body="harmless message")
    outsider = verified_user("convo-outsider")

    with pytest.raises(ValidationError):
        services.create_report(
            reporter=reporter,
            target_type=Report.TargetType.CONVERSATION,
            target_id=conversation.pk,
            reason=Report.Reason.HARASSMENT,
        )
    with pytest.raises(ValidationError, match="couldn't find"):
        services.create_report(
            reporter=outsider,
            target_type=Report.TargetType.CONVERSATION,
            target_id=conversation.pk,
            reason=Report.Reason.HARASSMENT,
            message_ids=[rude.pk],
        )

    report = services.create_report(
        reporter=reporter,
        target_type=Report.TargetType.CONVERSATION,
        target_id=conversation.pk,
        reason=Report.Reason.HARASSMENT,
        message_ids=[rude.pk],
    )
    assert report.reported_user == other
    assert list(report.evidence_messages.all()) == [rude]
    assert [s.data["body"] for s in report.evidence.all()] == ["rude message"]


@pytest.mark.django_db
def test_three_weapon_reports_hide_the_listing_and_cancel_its_pending_deal():
    seller = verified_user("hide-seller")
    buyer = verified_user("hide-buyer")
    listing = listing_for(seller)
    deal = deal_services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    deal_services.accept_deal(deal=deal, actor=seller)

    report_listing(verified_user("hide-a"), listing, prohibited_category=WEAPON)
    report_listing(verified_user("hide-b"), listing, prohibited_category=WEAPON)
    assert status_of(listing) == Listing.Status.PENDING

    report = report_listing(verified_user("hide-c"), listing, prohibited_category=WEAPON)
    assert status_of(listing) == Listing.Status.REMOVED
    deal.refresh_from_db()
    assert deal.status == Deal.Status.CANCELED
    action = report.case.actions.get()
    assert action.kind == ModerationAction.Kind.AUTO_HIDE_LISTING
    assert action.actor is None
    assert report.case.priority == ModerationCase.Priority.URGENT


# --- Blocking ---


@pytest.mark.django_db
def test_blocking_cancels_open_deals_and_stops_messages_and_requests_both_ways():
    seller = verified_user("block-seller")
    buyer = verified_user("block-buyer")
    listing = listing_for(seller)
    conversation = start_direct_conversation(sender=buyer, recipient=seller)
    deal = deal_services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)

    services.block_user(blocker=seller, blocked=buyer)
    deal.refresh_from_db()
    assert deal.status == Deal.Status.CANCELED

    for sender in (buyer, seller):
        with pytest.raises(ValidationError, match="isn't available"):
            send_message(conversation=conversation, sender=sender, body="hi")
    with pytest.raises(ValidationError, match="isn't available"):
        deal_services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)

    services.unblock_user(blocker=seller, blocked=buyer)
    send_message(conversation=conversation, sender=buyer, body="hi again")


# --- Restrictions ---


@pytest.mark.django_db
def test_a_selling_restriction_hides_listings_but_lets_a_pending_sale_finish():
    moderator = staff("sell-mod")
    seller = verified_user("sell-seller")
    buyer = verified_user("sell-buyer")
    pending = listing_for(seller)
    other = listing_for(seller)
    deal = deal_services.create_deal(listing=pending, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    deal_services.accept_deal(deal=deal, actor=seller)
    late_request = deal_services.create_deal(
        listing=other, buyer=buyer, kind=Deal.Kind.OFFER, amount_cents=1000
    )
    case = report_listing(verified_user("sell-reporter"), other).case

    services.restrict_user(
        staff=moderator, case=case, user=seller, kind=Kind.SELLING, reason="Repeat prohibited posts"
    )

    assert other not in browse_listings(buyer, FeedFilters())
    with pytest.raises(checks.Restricted):
        deal_services.accept_deal(deal=late_request, actor=seller)
    with pytest.raises(checks.Restricted):
        listing_services.update_item_listing(other, seller, title="New title")
    deal_services.confirm_handoff(deal=deal, actor=buyer)
    deal_services.confirm_handoff(deal=deal, actor=seller)
    assert status_of(pending) == Listing.Status.SOLD


@pytest.mark.django_db
def test_a_messaging_restriction_still_lets_deal_requests_send_their_note(client):
    moderator = staff("msg-mod")
    buyer = verified_user("msg-buyer")
    seller = verified_user("msg-seller")
    conversation = start_direct_conversation(sender=buyer, recipient=seller)
    case = services.create_report(
        reporter=seller,
        target_type=Report.TargetType.USER,
        target_id=buyer.pk,
        reason=Report.Reason.SPAM,
    ).case
    until = timezone.now() + timedelta(days=3)
    services.restrict_user(
        staff=moderator, case=case, user=buyer, kind=Kind.MESSAGING, reason="Spam", expires_at=until
    )

    client.force_login(buyer)
    response = client.post(
        f"/api/conversations/{conversation.pk}/messages/",
        {"body": "buy my stuff"},
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json()["code"] == "restricted_messaging"
    assert response.json()["until"] is not None

    deal_services.create_deal(listing=listing_for(seller), buyer=buyer, kind=Deal.Kind.BUY_NOW)


@pytest.mark.django_db
def test_restrictions_end_on_their_own_when_they_expire():
    moderator = staff("expire-mod")
    buyer = verified_user("expire-buyer")
    case = services.create_report(
        reporter=verified_user("expire-reporter"),
        target_type=Report.TargetType.USER,
        target_id=buyer.pk,
        reason=Report.Reason.SCAM,
    ).case
    restriction = services.restrict_user(
        staff=moderator,
        case=case,
        user=buyer,
        kind=Kind.DEALS,
        reason="Cool off",
        expires_at=timezone.now() + timedelta(hours=1),
    )
    with pytest.raises(checks.Restricted):
        checks.require_can(buyer, Kind.DEALS)

    restriction.expires_at = timezone.now() - timedelta(seconds=1)
    restriction.save(update_fields=["expires_at"])
    checks.require_can(buyer, Kind.DEALS)


# --- Suspensions and bans ---


@pytest.mark.django_db
def test_only_seniors_suspend_and_a_suspension_cancels_pending_deals_then_ends():
    moderator = staff("susp-mod")
    senior = staff("susp-senior", senior=True)
    seller = verified_user("susp-seller")
    buyer = verified_user("susp-buyer")
    listing = listing_for(seller)
    deal = deal_services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    deal_services.accept_deal(deal=deal, actor=seller)
    case = report_listing(buyer, listing, reason=Report.Reason.SCAM).case
    until = timezone.now() + timedelta(days=7)

    with pytest.raises(PermissionDenied, match="senior"):
        services.suspend_user(staff=moderator, case=case, user=seller, reason="Scam", until=until)
    restriction = services.suspend_user(
        staff=senior, case=case, user=seller, reason="Scam", until=until
    )

    seller.refresh_from_db()
    deal.refresh_from_db()
    assert seller.is_active is False
    assert deal.status == Deal.Status.CANCELED
    assert status_of(listing) == Listing.Status.AVAILABLE
    assert listing not in browse_listings(buyer, FeedFilters())

    restriction.expires_at = timezone.now() - timedelta(seconds=1)
    restriction.save(update_fields=["expires_at"])
    services.end_expired_suspension(restriction_id=restriction.pk)
    seller.refresh_from_db()
    assert seller.is_active is True


@pytest.mark.django_db
def test_a_ban_removes_listings_and_refuses_signup_at_every_school_domain():
    senior = staff("ban-senior", senior=True)
    seller = verified_user("ban-seller")
    listing = listing_for(seller)
    case = report_listing(verified_user("ban-reporter"), listing).case

    services.ban_user(staff=senior, case=case, user=seller, reason="Selling weapons")

    assert status_of(listing) == Listing.Status.REMOVED
    adapter = AccountAdapter()
    for email in ("ban-seller@umd.edu", "ban-seller@terpmail.umd.edu"):
        with pytest.raises(ValidationError, match="can't be used"):
            adapter.clean_email(email)
    adapter.clean_email("someone-else@umd.edu")


# --- Staff rules ---


@pytest.mark.django_db
def test_students_and_out_of_scope_moderators_cant_act():
    student = verified_user("scope-student")
    moderator = staff("scope-mod")
    listing = listing_for(verified_user("scope-seller"))
    case = report_listing(verified_user("scope-reporter"), listing).case

    with pytest.raises(PermissionDenied, match="Only moderators"):
        services.dismiss_case(staff=student, case=case, reason="no")

    elsewhere = School.objects.create(name="Elsewhere University", short_name="EU", slug="eu")
    ModeratorScope.objects.create(user=moderator).schools.add(elsewhere)
    with pytest.raises(PermissionDenied, match="outside the schools"):
        services.dismiss_case(staff=moderator, case=case, reason="no")
    assert case not in services.visible_cases(moderator)


@pytest.mark.django_db
def test_conflicts_of_interest_block_moderators_and_only_seniors_override_some():
    moderator = staff("coi-mod")
    senior = staff("coi-senior", senior=True)
    seller = verified_user("coi-seller")
    listing = listing_for(seller)
    case = report_listing(verified_user("coi-reporter"), listing).case
    # Both moderators once bought from this seller.
    for staffer in (moderator, senior):
        deal_services.create_deal(
            listing=listing_for(seller), buyer=staffer, kind=Deal.Kind.BUY_NOW
        )

    with pytest.raises(PermissionDenied, match="had a deal"):
        services.warn_user(staff=moderator, case=case, user=seller, reason="Warning")
    with pytest.raises(PermissionDenied, match="had a deal"):
        services.warn_user(staff=senior, case=case, user=seller, reason="Warning")

    # A senior can step past a past-dealings conflict, with a reason on record.
    services._require_staff(senior, case, override_reason="No one else is on shift")
    assert case.actions.filter(kind=ModerationAction.Kind.CONFLICT_OVERRIDE).exists()

    own_case = report_listing(seller, listing_for(moderator)).case
    with pytest.raises(PermissionDenied, match="about you"):
        services.dismiss_case(staff=moderator, case=own_case, reason="Nothing here")
    assert own_case not in services.visible_cases(moderator)


@pytest.mark.django_db
def test_moderator_removal_releases_a_pending_trade_and_restore_brings_it_back():
    moderator = staff("trade-mod")
    seller = verified_user("mtrade-seller")
    buyer = verified_user("mtrade-buyer")
    listing = listing_for(seller)
    jacket = listing_for(buyer)
    deal = deal_services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.TRADE)
    deal_services.counter_trade(deal=deal, actor=seller, item_ids=[jacket.pk])
    deal_services.accept_deal(deal=deal, actor=buyer)
    case = report_listing(verified_user("mtrade-reporter"), jacket).case

    services.remove_listing(staff=moderator, case=case, listing=jacket, reason="Counterfeit")
    deal.refresh_from_db()
    assert deal.status == Deal.Status.CANCELED
    assert status_of(listing) == Listing.Status.AVAILABLE
    assert status_of(jacket) == Listing.Status.REMOVED

    services.restore_listing(staff=moderator, case=case, listing=jacket, reason="It was genuine")
    assert status_of(jacket) == Listing.Status.AVAILABLE


@pytest.mark.django_db
def test_every_action_needs_a_reason_and_the_audit_trail_cant_change():
    moderator = staff("audit-mod")
    case = report_listing(
        verified_user("audit-reporter"), listing_for(verified_user("audit-s"))
    ).case

    with pytest.raises(ValidationError, match="reason"):
        services.dismiss_case(staff=moderator, case=case, reason="  ")
    action = services.dismiss_case(staff=moderator, case=case, reason="Not prohibited")

    case.refresh_from_db()
    assert case.status == ModerationCase.Status.RESOLVED
    assert set(case.reports.values_list("status", flat=True)) == {Report.Status.RESOLVED}
    action.reason = "edited"
    with pytest.raises(RuntimeError):
        action.save()
    with pytest.raises(RuntimeError):
        action.delete()
