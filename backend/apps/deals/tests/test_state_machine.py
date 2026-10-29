"""The deal state machine: transitions, authorization, idempotency, deadlines, backups,
handoffs, disputes, problem reports, notifications and activity sections."""

from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.utils import timezone

from apps.deals import services
from apps.deals.models import (
    Deal,
    DealDispute,
    DealEvent,
    DealProblem,
    HandoffConfirmation,
)
from apps.deals.tests.test_services import listing_for, verified_user
from apps.listings.models import Listing
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.trust import services as trust_services
from apps.trust.models import Block, ModerationAction, Report, UserRestriction
from apps.trust.tests.test_moderation import staff

S = Deal.Status
ALL_STATUSES = list(S.values)


@pytest.fixture
def seller():
    return verified_user("seller")


@pytest.fixture
def buyer():
    return verified_user("buyer")


@pytest.fixture
def listing(seller):
    return listing_for(seller)


def request(listing, buyer, kind=Deal.Kind.OFFER, amount=4000):
    if kind == Deal.Kind.OFFER:
        return services.create_deal(listing=listing, buyer=buyer, kind=kind, amount_cents=amount)
    return services.create_deal(listing=listing, buyer=buyer, kind=kind)


def pending(listing, buyer, seller):
    deal = request(listing, buyer, Deal.Kind.BUY_NOW)
    services.accept_deal(deal=deal, actor=seller)
    deal.refresh_from_db()
    return deal


def status(obj):
    obj.refresh_from_db()
    return obj.status


def events(deal, event_type=None):
    found = DealEvent.objects.filter(deal=deal)
    return found.filter(event_type=event_type) if event_type else found


def deal_notifications(user):
    return Notification.objects.filter(user=user, kind=Notification.Kind.DEAL)


def past(**kwargs):
    return timezone.now() - timedelta(seconds=1, **kwargs)


# --- The transition table ---


@pytest.mark.django_db
@pytest.mark.parametrize("from_status", ALL_STATUSES)
@pytest.mark.parametrize("to_status", ALL_STATUSES)
def test_only_listed_transitions_are_allowed(listing, buyer, from_status, to_status):
    deal = request(listing, buyer)
    Deal.objects.filter(pk=deal.pk).update(status=from_status)
    deal.refresh_from_db()
    allowed = to_status in services.TRANSITIONS[from_status]

    with transaction.atomic():
        if allowed:
            event = services._transition(deal, to_status, "test_move")
            assert (event.from_status, event.to_status) == (from_status, to_status)
            transaction.set_rollback(True)
        else:
            with pytest.raises(services.DealStateError):
                services._transition(deal, to_status, "test_move")
    assert status(deal) == from_status  # refused, or rolled back


def test_final_statuses_have_no_way_out():
    for final in (S.COMPLETED, S.CANCELED, S.DECLINED, S.EXPIRED):
        assert services.TRANSITIONS[final] == set()


@pytest.mark.django_db
def test_every_status_change_records_actor_time_and_from_to(listing, buyer, seller):
    deal = request(listing, buyer)
    services.counter_offer(deal=deal, actor=seller, amount_cents=4500)
    services.accept_deal(deal=deal, actor=buyer)
    services.confirm_handoff(deal=deal, actor=buyer)
    services.confirm_handoff(deal=deal, actor=seller)

    moves = list(events(deal).exclude(to_status="").values_list("event_type", "actor", "to_status"))
    assert moves == [
        ("request_created", buyer.pk, S.AWAITING_SELLER),
        ("countered", seller.pk, S.AWAITING_BUYER),
        ("accepted", buyer.pk, S.PENDING),
        ("completed", None, S.COMPLETED),
    ]
    deal.refresh_from_db()
    assert deal.accepted_by == buyer
    assert deal.accepted_at is not None
    assert deal.completed_at is not None
    assert all(e.created_at for e in events(deal))


# --- Authorization ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action",
    ["accept", "decline", "cancel", "counter", "confirm", "report", "archive"],
)
def test_unrelated_students_and_moderators_cant_act_on_a_deal(listing, buyer, seller, action):
    deal = request(listing, buyer)
    outsiders = [verified_user("outsider"), staff("moderator")]
    calls = {
        "accept": lambda user: services.accept_deal(deal=deal, actor=user),
        "decline": lambda user: services.decline_deal(deal=deal, actor=user),
        "cancel": lambda user: services.cancel_deal(deal=deal, actor=user),
        "counter": lambda user: services.counter_offer(deal=deal, actor=user, amount_cents=1),
        "confirm": lambda user: services.confirm_handoff(deal=deal, actor=user),
        "report": lambda user: services.report_problem(deal=deal, actor=user, kind="no_show"),
        "archive": lambda user: services.set_archived(deal=deal, actor=user, archived=True),
    }
    for user in outsiders:
        with pytest.raises(PermissionDenied):
            calls[action](user)
    assert status(deal) == S.AWAITING_SELLER


@pytest.mark.django_db
def test_deal_endpoints_are_404_for_outsiders_and_moderators(listing, buyer, seller):
    deal = request(listing, buyer)
    for outsider in (verified_user("outsider"), staff("moderator")):
        client = Client()
        client.force_login(outsider)
        assert client.get(f"/api/deals/{deal.pk}/").status_code == 404
        for action in ("accept", "decline", "cancel", "confirm-handoff", "archive"):
            assert client.post(f"/api/deals/{deal.pk}/{action}/").status_code == 404
    assert status(deal) == S.AWAITING_SELLER


@pytest.mark.django_db
def test_only_the_person_whose_turn_it_is_can_answer(listing, buyer, seller):
    deal = request(listing, buyer)
    for call in (
        lambda: services.accept_deal(deal=deal, actor=buyer),
        lambda: services.decline_deal(deal=deal, actor=buyer),
        lambda: services.counter_offer(deal=deal, actor=buyer, amount_cents=3000),
    ):
        with pytest.raises(PermissionDenied):
            call()
    services.counter_offer(deal=deal, actor=seller, amount_cents=4500)
    with pytest.raises(PermissionDenied):
        services.accept_deal(deal=deal, actor=seller)


@pytest.mark.django_db
def test_seller_answers_need_selling_privileges(listing, buyer, seller):
    deal = request(listing, buyer)
    UserRestriction.objects.create(user=seller, kind=UserRestriction.Kind.SELLING, reason="x")

    with pytest.raises(PermissionDenied):
        services.accept_deal(deal=deal, actor=seller)


# --- Invalid transitions by action ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("deal_status", "action"),
    [
        (S.PENDING, "counter"),
        (S.PENDING, "decline"),
        (S.COMPLETED, "cancel"),
        (S.COMPLETED, "counter"),
        (S.CANCELED, "accept"),
        (S.DECLINED, "confirm"),
        (S.EXPIRED, "cancel"),
        (S.DISPUTED, "cancel"),
        (S.DISPUTED, "confirm"),
        (S.BACKUP, "accept"),
        (S.BACKUP, "confirm"),
        (S.AWAITING_SELLER, "confirm"),
    ],
)
def test_actions_are_refused_in_the_wrong_status(listing, buyer, seller, deal_status, action):
    deal = request(listing, buyer)
    Deal.objects.filter(pk=deal.pk).update(status=deal_status, response_deadline=None)
    calls = {
        "counter": lambda: services.counter_offer(deal=deal, actor=seller, amount_cents=4100),
        "decline": lambda: services.decline_deal(deal=deal, actor=buyer),
        "cancel": lambda: services.cancel_deal(deal=deal, actor=buyer),
        "accept": lambda: services.accept_deal(deal=deal, actor=seller),
        "confirm": lambda: services.confirm_handoff(deal=deal, actor=buyer),
    }
    with pytest.raises((services.DealStateError, PermissionDenied)):
        calls[action]()
    assert status(deal) == deal_status


@pytest.mark.django_db
def test_a_second_buyer_cant_be_accepted_while_one_is_pending(listing, buyer, seller):
    other = request(listing, verified_user("other"))
    pending(listing, buyer, seller)

    # The other request is now a backup; even forced back to awaiting, acceptance fails.
    Deal.objects.filter(pk=other.pk).update(status=S.AWAITING_SELLER, backup_position=None)
    with pytest.raises(ValidationError, match="pending buyer"):
        services.accept_deal(deal=other, actor=seller)


@pytest.mark.django_db
def test_the_database_allows_one_holding_deal_per_listing(listing, buyer, seller):
    first = pending(listing, buyer, seller)
    second = Deal.objects.create(
        listing=listing,
        buyer=verified_user("other"),
        seller=seller,
        conversation=first.conversation,
        kind=Deal.Kind.BUY_NOW,
        status=S.AWAITING_SELLER,
        current_amount_cents=5000,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Deal.objects.filter(pk=second.pk).update(status=S.DISPUTED)


# --- Idempotency ---


@pytest.mark.django_db
def test_repeated_requests_change_nothing_the_second_time(listing, buyer, seller):
    deal = request(listing, buyer)
    assert request(listing, buyer).pk == deal.pk

    services.counter_offer(deal=deal, actor=seller, amount_cents=4500)
    services.counter_offer(deal=deal, actor=seller, amount_cents=4500)
    assert events(deal, "countered").count() == 1
    assert deal.offers.count() == 2

    services.accept_deal(deal=deal, actor=buyer)
    services.accept_deal(deal=deal, actor=buyer)
    assert events(deal, "accepted").count() == 1

    services.confirm_handoff(deal=deal, actor=buyer)
    services.confirm_handoff(deal=deal, actor=buyer)
    assert HandoffConfirmation.objects.filter(deal=deal).count() == 1
    assert events(deal, "handoff_confirmed").count() == 1

    services.confirm_handoff(deal=deal, actor=seller)
    services.confirm_handoff(deal=deal, actor=seller)
    assert status(deal) == S.COMPLETED
    assert events(deal, "completed").count() == 1


@pytest.mark.django_db
def test_repeated_decline_cancel_and_archive(listing, buyer, seller):
    declined = request(listing, buyer)
    services.decline_deal(deal=declined, actor=seller)
    services.decline_deal(deal=declined, actor=seller)
    assert events(declined, "declined").count() == 1

    canceled = request(listing, verified_user("second"))
    services.cancel_deal(deal=canceled, actor=canceled.buyer)
    services.cancel_deal(deal=canceled, actor=canceled.buyer)
    assert events(canceled, "canceled").count() == 1

    services.set_archived(deal=canceled, actor=canceled.buyer, archived=True)
    first = Deal.objects.get(pk=canceled.pk).buyer_archived_at
    services.set_archived(deal=canceled, actor=canceled.buyer, archived=True)
    assert Deal.objects.get(pk=canceled.pk).buyer_archived_at == first


@pytest.mark.django_db
def test_the_expiry_job_is_safe_to_run_again(listing, buyer, seller):
    deal = request(listing, buyer)
    Deal.objects.filter(pk=deal.pk).update(response_deadline=past())

    for _ in range(3):
        services.expire(deal_id=deal.pk, expected_status=S.AWAITING_SELLER)
        services.settle_due_deals()

    assert status(deal) == S.EXPIRED
    assert events(deal, "expired").count() == 1
    assert deal_notifications(buyer).filter(title__startswith="Deal expired").count() == 1


@pytest.mark.django_db
def test_an_early_expiry_job_does_nothing(listing, buyer):
    deal = request(listing, buyer)

    services.expire(deal_id=deal.pk, expected_status=S.AWAITING_SELLER)

    assert status(deal) == S.AWAITING_SELLER


# --- Deadlines at request time ---


@pytest.mark.django_db
@pytest.mark.parametrize("who", ["seller-accept", "seller-counter", "seller-decline"])
def test_a_late_answer_is_refused_and_the_request_expires(listing, buyer, seller, who):
    deal = request(listing, buyer)
    Deal.objects.filter(pk=deal.pk).update(response_deadline=past())
    call = {
        "seller-accept": lambda: services.accept_deal(deal=deal, actor=seller),
        "seller-counter": lambda: services.counter_offer(deal=deal, actor=seller, amount_cents=1),
        "seller-decline": lambda: services.decline_deal(deal=deal, actor=seller),
    }[who]

    with pytest.raises(services.DealStateError):
        call()

    # Settled for good even though the action was refused, before any job ran.
    assert status(deal) == S.EXPIRED
    assert status(listing) == Listing.Status.AVAILABLE


@pytest.mark.django_db
def test_a_late_handoff_confirmation_is_refused_and_the_listing_comes_back(listing, buyer, seller):
    deal = pending(listing, buyer, seller)
    Deal.objects.filter(pk=deal.pk).update(handoff_deadline=past())

    with pytest.raises(services.DealStateError):
        services.confirm_handoff(deal=deal, actor=buyer)

    assert status(deal) == S.EXPIRED
    assert status(listing) == Listing.Status.AVAILABLE
    assert not HandoffConfirmation.objects.filter(deal=deal).exists()


@pytest.mark.django_db
def test_the_sweep_settles_every_due_deal(listing, buyer, seller):
    late_request = request(listing_for(seller), buyer)
    late_handoff = pending(listing, verified_user("b2"), seller)
    on_time = request(listing_for(seller), verified_user("b3"))
    Deal.objects.filter(pk=late_request.pk).update(response_deadline=past())
    Deal.objects.filter(pk=late_handoff.pk).update(handoff_deadline=past())

    assert services.settle_due_deals() == 2

    assert status(late_request) == S.EXPIRED
    assert status(late_handoff) == S.EXPIRED
    assert status(on_time) == S.AWAITING_SELLER


# --- Cancellation at each stage ---


@pytest.mark.django_db
def test_cancel_before_acceptance(listing, buyer, seller):
    deal = request(listing, buyer)
    services.cancel_deal(deal=deal, actor=seller)
    deal.refresh_from_db()
    assert deal.status == S.CANCELED
    assert deal.closed_by == seller
    assert deal.closed_at is not None
    assert status(listing) == Listing.Status.AVAILABLE


@pytest.mark.django_db
def test_cancel_after_acceptance_releases_the_listing(listing, buyer, seller):
    deal = pending(listing, buyer, seller)
    services.cancel_deal(deal=deal, actor=buyer)
    assert status(deal) == S.CANCELED
    assert status(listing) == Listing.Status.AVAILABLE
    assert deal_notifications(seller).filter(title__startswith="Deal canceled").count() == 1


@pytest.mark.django_db
def test_cancel_after_one_confirmation_is_refused(listing, buyer, seller):
    deal = pending(listing, buyer, seller)
    services.confirm_handoff(deal=deal, actor=buyer)

    for actor in (buyer, seller):
        with pytest.raises(ValidationError, match="report a problem"):
            services.cancel_deal(deal=deal, actor=actor)
    assert status(deal) == S.PENDING
    assert status(listing) == Listing.Status.PENDING


@pytest.mark.django_db
def test_history_is_never_deleted(listing, buyer, seller):
    canceled = pending(listing, buyer, seller)
    services.cancel_deal(deal=canceled, actor=buyer)
    expired = request(listing, verified_user("late"))
    Deal.objects.filter(pk=expired.pk).update(response_deadline=past())
    services.settle_due_deals()

    for deal in (canceled, expired):
        assert Deal.objects.filter(pk=deal.pk).exists()
        assert events(deal).count() >= 2
        assert deal.offers.exists()


# --- Handoff ---


@pytest.mark.django_db
def test_one_confirmation_never_sells_the_listing(listing, buyer, seller):
    deal = pending(listing, buyer, seller)
    services.confirm_handoff(deal=deal, actor=seller)
    assert status(listing) == Listing.Status.PENDING
    assert status(deal) == S.PENDING
    services.confirm_handoff(deal=deal, actor=buyer)
    assert status(listing) == Listing.Status.SOLD
    assert status(deal) == S.COMPLETED


@pytest.mark.django_db
def test_a_reporter_cant_then_confirm(listing, buyer, seller):
    deal = pending(listing, buyer, seller)
    services.report_problem(deal=deal, actor=buyer, kind="not_as_described")

    with pytest.raises(ValidationError, match="reported a problem"):
        services.confirm_handoff(deal=deal, actor=buyer)


# --- Backup queue ---


@pytest.fixture
def queue(listing, buyer, seller):
    """A pending deal and three backups, queued in request order."""
    backups = [request(listing, verified_user(f"backup{i}")) for i in range(3)]
    primary = request(listing, buyer, Deal.Kind.BUY_NOW)
    services.accept_deal(deal=primary, actor=seller)
    for deal in backups:
        deal.refresh_from_db()
    return primary, backups


@pytest.mark.django_db
def test_backups_queue_in_request_order(queue):
    _, backups = queue
    assert [(b.status, b.backup_position) for b in backups] == [
        (S.BACKUP, 1),
        (S.BACKUP, 2),
        (S.BACKUP, 3),
    ]


@pytest.mark.django_db
def test_a_backup_cant_jump_the_queue(queue, seller):
    _, backups = queue
    with pytest.raises(services.DealStateError, match="in line"):
        services.accept_deal(deal=backups[1], actor=seller)


@pytest.mark.django_db
def test_when_the_primary_falls_through_only_the_first_backup_is_promoted(queue, buyer, listing):
    primary, backups = queue

    services.cancel_deal(deal=primary, actor=buyer)

    first, second, third = (Deal.objects.get(pk=b.pk) for b in backups)
    assert first.status == S.AWAITING_SELLER
    assert first.response_deadline > timezone.now()
    assert first.backup_position is None
    assert (second.status, second.backup_position) == (S.BACKUP, 2)
    assert (third.status, third.backup_position) == (S.BACKUP, 3)
    assert status(listing) == Listing.Status.AVAILABLE
    assert events(first, "promoted_from_backup").count() == 1
    assert deal_notifications(first.buyer).filter(title__startswith="Backup buyer").exists()


@pytest.mark.django_db
def test_the_next_backup_gets_a_turn_when_the_promoted_one_lapses(queue, buyer, seller):
    primary, backups = queue
    services.cancel_deal(deal=primary, actor=buyer)
    first = Deal.objects.get(pk=backups[0].pk)
    Deal.objects.filter(pk=first.pk).update(response_deadline=past())

    services.settle_due_deals()

    assert status(first) == S.EXPIRED
    assert status(backups[1]) == S.AWAITING_SELLER
    assert status(backups[2]) == S.BACKUP


@pytest.mark.django_db
def test_backups_who_cant_deal_any_more_are_skipped(queue, buyer, seller):
    primary, backups = queue
    Block.objects.create(blocker=seller, blocked=backups[0].buyer)
    UserRestriction.objects.create(
        user=backups[1].buyer, kind=UserRestriction.Kind.DEALS, reason="x"
    )

    services.cancel_deal(deal=primary, actor=buyer)

    assert status(backups[0]) == S.CANCELED
    assert status(backups[1]) == S.CANCELED
    assert status(backups[2]) == S.AWAITING_SELLER
    assert Deal.objects.get(pk=backups[0].pk).close_reason == "backup_ineligible"


@pytest.mark.django_db
def test_the_seller_can_take_a_backup_off_the_queue_but_not_the_buyer_for_them(queue, seller):
    _, backups = queue
    with pytest.raises(PermissionDenied):
        services.decline_deal(deal=backups[0], actor=backups[0].buyer)
    services.decline_deal(deal=backups[0], actor=seller)
    assert status(backups[0]) == S.DECLINED
    # A backup buyer can still withdraw.
    services.cancel_deal(deal=backups[1], actor=backups[1].buyer)
    assert status(backups[1]) == S.CANCELED


@pytest.mark.django_db
def test_completion_closes_the_queue(queue, buyer, seller):
    primary, backups = queue
    services.confirm_handoff(deal=primary, actor=buyer)
    services.confirm_handoff(deal=primary, actor=seller)
    for backup in backups:
        assert status(backup) == S.EXPIRED
        assert deal_notifications(backup.buyer).filter(title__endswith="sold").count() == 1


@pytest.mark.django_db
def test_an_expired_handoff_promotes_the_next_backup(queue):
    primary, backups = queue
    Deal.objects.filter(pk=primary.pk).update(handoff_deadline=past())

    services.expire(deal_id=primary.pk, expected_status=S.PENDING)

    assert status(primary) == S.EXPIRED
    assert status(backups[0]) == S.AWAITING_SELLER


# --- Problems, no-shows and disputes ---


@pytest.mark.django_db
def test_a_no_show_before_any_confirmation_frees_the_listing_and_reaches_moderation(
    queue, buyer, seller, listing
):
    primary, backups = queue

    problem = services.report_problem(
        deal=primary, actor=seller, kind="no_show", details="Waited 20 minutes."
    )

    assert status(primary) == S.CANCELED
    assert Deal.objects.get(pk=primary.pk).close_reason == "no_show_reported"
    assert status(listing) == Listing.Status.AVAILABLE
    assert status(backups[0]) == S.AWAITING_SELLER
    report = problem.report
    assert (report.reason, report.target_type, report.deal_id) == (
        Report.Reason.NO_SHOW,
        Report.TargetType.DEAL,
        primary.pk,
    )
    assert report.reported_user == buyer
    snapshot = report.evidence.get(kind="deal").data
    assert snapshot["status"] == S.PENDING
    assert problem.case == report.case
    # No one is punished by a report.
    assert not UserRestriction.objects.exists()
    assert not ModerationAction.objects.exclude(kind="note").exists()
    assert buyer.is_active


@pytest.mark.django_db
def test_a_problem_report_is_recorded_once(listing, buyer, seller):
    deal = pending(listing, buyer, seller)
    first = services.report_problem(deal=deal, actor=buyer, kind="not_as_described")
    again = services.report_problem(deal=deal, actor=buyer, kind="not_as_described")
    assert again.pk == first.pk
    assert DealProblem.objects.count() == 1
    assert Report.objects.count() == 1
    assert status(deal) == S.PENDING  # no confirmation yet; either side may still cancel


@pytest.mark.django_db
def test_problems_need_an_accepted_deal(listing, buyer):
    deal = request(listing, buyer)
    with pytest.raises(services.DealStateError):
        services.report_problem(deal=deal, actor=buyer, kind="no_show")


@pytest.mark.django_db
def test_conflicting_accounts_open_a_dispute_instead_of_guessing(listing, buyer, seller):
    deal = pending(listing, buyer, seller)
    services.confirm_handoff(deal=deal, actor=seller)  # seller says it happened

    services.report_problem(deal=deal, actor=buyer, kind="no_show")  # buyer says it didn't

    deal.refresh_from_db()
    assert deal.status == S.DISPUTED
    assert status(listing) == Listing.Status.PENDING
    dispute = deal.dispute
    assert dispute.reason == DealDispute.Reason.PROBLEM_AFTER_CONFIRMATION
    assert dispute.opened_by == buyer
    assert dispute.case.subject_user == seller
    assert dispute.snapshot["deal"]["status"] == S.PENDING
    assert dispute.snapshot["listing"]["title"] == listing.title
    assert [c["user_id"] for c in dispute.snapshot["deal"]["confirmed_by"]] == [seller.pk]
    for user in (buyer, seller):
        assert deal_notifications(user).filter(title__startswith="A moderator will").exists()
    with pytest.raises(services.DealStateError):
        services.confirm_handoff(deal=deal, actor=buyer)


@pytest.mark.django_db
def test_one_side_confirming_and_reporting_a_problem_opens_a_dispute(listing, buyer, seller):
    deal = pending(listing, buyer, seller)
    services.confirm_handoff(deal=deal, actor=buyer)
    services.report_problem(deal=deal, actor=buyer, kind="not_as_described")
    assert status(deal) == S.DISPUTED


@pytest.mark.django_db
def test_a_lapsed_one_sided_handoff_is_disputed_by_the_system(listing, buyer, seller):
    deal = pending(listing, buyer, seller)
    services.confirm_handoff(deal=deal, actor=buyer)
    Deal.objects.filter(pk=deal.pk).update(handoff_deadline=past())

    services.settle_due_deals()
    services.settle_due_deals()

    deal.refresh_from_db()
    assert deal.status == S.DISPUTED
    assert deal.dispute.opened_by is None
    assert deal.dispute.case.subject_user == seller
    assert DealDispute.objects.count() == 1


@pytest.fixture
def dispute(listing, buyer, seller):
    deal = pending(listing, buyer, seller)
    services.confirm_handoff(deal=deal, actor=buyer)
    services.report_problem(deal=deal, actor=seller, kind="payment")
    deal.refresh_from_db()
    return deal


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("outcome", "deal_status", "listing_status"),
    [
        ("completed", S.COMPLETED, Listing.Status.SOLD),
        ("canceled", S.CANCELED, Listing.Status.AVAILABLE),
    ],
)
def test_a_moderator_decides_a_dispute(dispute, listing, outcome, deal_status, listing_status):
    moderator = staff("moderator")
    case = dispute.dispute.case

    trust_services.resolve_deal_dispute(
        staff=moderator, case=case, deal=dispute, outcome=outcome, reason="Checked messages."
    )
    trust_services.resolve_deal_dispute(
        staff=moderator, case=case, deal=dispute, outcome=outcome, reason="Again."
    )

    assert status(dispute) == deal_status
    assert status(listing) == listing_status
    decided = DealDispute.objects.get(deal=dispute)
    assert (decided.outcome, decided.resolved_by) == (outcome, moderator)
    assert case.actions.filter(kind=ModerationAction.Kind.RESOLVE_DEAL_DISPUTE).count() == 1
    with pytest.raises(ValidationError):
        trust_services.resolve_deal_dispute(
            staff=moderator,
            case=case,
            deal=dispute,
            outcome="completed" if outcome == "canceled" else "canceled",
            reason="Changed my mind.",
        )


@pytest.mark.django_db
def test_students_cant_decide_disputes(dispute, buyer):
    with pytest.raises(PermissionDenied):
        trust_services.resolve_deal_dispute(
            staff=buyer,
            case=dispute.dispute.case,
            deal=dispute,
            outcome="completed",
            reason="Mine now.",
        )
    assert status(dispute) == S.DISPUTED


@pytest.mark.django_db
def test_moderators_decide_disputes_through_the_case_api(dispute):
    client = Client()
    client.force_login(staff("moderator"))
    case = dispute.dispute.case

    detail = client.get(f"/api/moderation/cases/{case.pk}/").json()
    assert [d["deal_id"] for d in detail["deal_disputes"]] == [dispute.pk]

    response = client.post(
        f"/api/moderation/cases/{case.pk}/actions/",
        {
            "action": "resolve_deal_dispute",
            "deal_id": dispute.pk,
            "dispute_outcome": "canceled",
            "reason": "No handoff happened.",
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.json()
    assert response.json()["deal_disputes"][0]["outcome"] == "canceled"
    assert status(dispute) == S.CANCELED


# --- Notifications ---


@pytest.mark.django_db
def test_notify_with_a_key_sends_once(buyer):
    for _ in range(3):
        notify(buyer, kind="deal", title="Once", dedupe_key="test:1")
    assert Notification.objects.filter(user=buyer, dedupe_key="test:1").count() == 1


@pytest.mark.django_db
def test_each_transition_notifies_the_right_person_once(listing, buyer, seller):
    deal = request(listing, buyer)
    assert deal_notifications(seller).filter(title__startswith="New request").count() == 1
    assert not deal_notifications(buyer).exists()

    services.counter_offer(deal=deal, actor=seller, amount_cents=4500)
    services.counter_offer(deal=deal, actor=seller, amount_cents=4500)
    assert deal_notifications(buyer).filter(title__startswith="New counteroffer").count() == 1

    services.accept_deal(deal=deal, actor=buyer)
    assert deal_notifications(seller).filter(title__startswith="Deal accepted").count() == 1
    services.confirm_handoff(deal=deal, actor=seller)
    assert deal_notifications(buyer).filter(title__startswith="Confirm your handoff").count() == 1
    services.confirm_handoff(deal=deal, actor=buyer)
    # The completing confirmation doesn't also ask the seller to confirm.
    assert not deal_notifications(seller).filter(title__startswith="Confirm your").exists()
    for user in (buyer, seller):
        assert deal_notifications(user).filter(title__startswith="Handoff complete").count() == 1
        assert all(n.link == "/deals" for n in deal_notifications(user))


@pytest.mark.django_db
def test_quiet_block_cancellations_dont_notify(listing, buyer, seller):
    deal = request(listing, buyer)
    before = Notification.objects.count()
    trust_services.block_user(blocker=seller, blocked=buyer)
    assert status(deal) == S.CANCELED
    assert Notification.objects.count() == before


# --- Activity sections ---


@pytest.mark.django_db
def test_activity_sections(listing, buyer, seller):
    current = request(listing_for(seller), buyer)
    backup = request(listing, buyer)  # another buyer is accepted below, so this waits in line
    pending(listing, verified_user("holder"), seller)
    bought = pending(listing_for(seller), buyer, seller)
    services.confirm_handoff(deal=bought, actor=buyer)
    services.confirm_handoff(deal=bought, actor=seller)
    canceled = request(listing_for(seller), buyer)
    services.cancel_deal(deal=canceled, actor=buyer)
    archived_by_me = request(listing_for(seller), buyer)
    services.cancel_deal(deal=archived_by_me, actor=seller)
    services.set_archived(deal=archived_by_me, actor=buyer, archived=True)
    declined = request(listing_for(seller), buyer)
    services.decline_deal(deal=declined, actor=seller)
    expired = request(listing_for(seller), buyer)
    Deal.objects.filter(pk=expired.pk).update(response_deadline=past())
    services.settle_due_deals()
    disputed = pending(listing_for(seller), buyer, seller)
    services.confirm_handoff(deal=disputed, actor=buyer)
    services.report_problem(deal=disputed, actor=buyer, kind="other")

    client = Client()
    client.force_login(buyer)

    def ids(section):
        response = client.get("/api/deals/", {"section": section})
        assert response.status_code == 200
        found = {deal["id"]: deal["section"] for deal in response.json()}
        assert set(found.values()) <= {section}
        return set(found)

    # Backups and disputes under review stay current.
    assert ids("current") == {current.pk, backup.pk, disputed.pk}
    assert status(backup) == S.BACKUP
    # History is completed deals only: the backup that never happened isn't there.
    assert ids("history") == {bought.pk}
    assert ids("cancelled") == {canceled.pk}
    assert ids("archived") == {archived_by_me.pk, declined.pk, expired.pk}
    # Archiving is per person: the seller still sees it under Cancelled.
    assert services.section_for(Deal.objects.get(pk=archived_by_me.pk), seller) == "cancelled"


@pytest.mark.django_db
def test_only_canceled_deals_can_be_archived_by_hand(listing, buyer, seller):
    open_deal = request(listing, buyer)
    with pytest.raises(services.DealStateError):
        services.set_archived(deal=open_deal, actor=buyer, archived=True)
    services.decline_deal(deal=open_deal, actor=seller)
    with pytest.raises(services.DealStateError):  # already in Archived
        services.set_archived(deal=open_deal, actor=buyer, archived=True)
    completed = pending(listing_for(seller), verified_user("b2"), seller)
    services.confirm_handoff(deal=completed, actor=completed.buyer)
    services.confirm_handoff(deal=completed, actor=seller)
    with pytest.raises(services.DealStateError):
        services.set_archived(deal=completed, actor=seller, archived=True)


@pytest.mark.django_db
def test_the_deal_says_what_the_viewer_can_do(listing, buyer, seller):
    deal = pending(listing, buyer, seller)
    services.confirm_handoff(deal=deal, actor=buyer)
    client = Client()
    client.force_login(buyer)
    actions = client.get(f"/api/deals/{deal.pk}/").json()["actions"]
    assert actions == {
        "accept": False,
        "counter": False,
        "decline": False,
        "cancel": False,
        "confirm_handoff": False,
        "report_problem": True,
        "archive": False,
        "unarchive": False,
    }
    client.force_login(seller)
    assert client.get(f"/api/deals/{deal.pk}/").json()["actions"]["confirm_handoff"] is True


@pytest.mark.django_db
def test_report_problem_endpoint(listing, buyer, seller):
    deal = pending(listing, buyer, seller)
    client = Client()
    client.force_login(seller)

    response = client.post(
        f"/api/deals/{deal.pk}/report-problem/",
        {"kind": "no_show", "details": "Never came."},
        content_type="application/json",
    )

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["status"] == S.CANCELED
    assert body["my_problems"] == ["no_show"]
    assert body["section"] == "cancelled"
    bad = client.post(
        f"/api/deals/{deal.pk}/report-problem/", {"kind": "rude"}, content_type="application/json"
    )
    assert bad.status_code == 400


# --- Trades through the same rules ---


@pytest.fixture
def trade(seller, buyer, listing):
    """A pending trade: the seller's listing for two of the buyer's items, plus a backup for
    one of the buyer's items."""
    jacket, boots = listing_for(buyer), listing_for(buyer)
    jacket_fan = request(jacket, verified_user("jacketfan"))
    deal = services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.TRADE)
    services.counter_trade(deal=deal, actor=seller, item_ids=[jacket.pk, boots.pk])
    services.accept_deal(deal=deal, actor=buyer)
    deal.refresh_from_db()
    return deal, jacket, boots, jacket_fan


@pytest.mark.django_db
def test_a_trade_holds_every_item_and_queues_their_other_buyers(trade, listing):
    deal, jacket, boots, jacket_fan = trade
    assert deal.status == S.PENDING
    assert [status(x) for x in (listing, jacket, boots)] == [Listing.Status.PENDING] * 3
    jacket_fan.refresh_from_db()
    assert (jacket_fan.status, jacket_fan.backup_position) == (S.BACKUP, 1)


@pytest.mark.django_db
def test_a_canceled_trade_releases_every_item_and_promotes_their_backups(trade, buyer, listing):
    deal, jacket, boots, jacket_fan = trade
    services.cancel_deal(deal=deal, actor=buyer)
    assert [status(x) for x in (listing, jacket, boots)] == [Listing.Status.AVAILABLE] * 3
    assert status(jacket_fan) == S.AWAITING_SELLER


@pytest.mark.django_db
def test_a_disputed_trade_waits_and_a_completed_decision_sells_every_item(
    trade, buyer, seller, listing
):
    deal, jacket, boots, jacket_fan = trade
    services.confirm_handoff(deal=deal, actor=seller)
    services.report_problem(deal=deal, actor=buyer, kind="not_as_described")
    assert status(deal) == S.DISPUTED
    assert [status(x) for x in (listing, jacket, boots)] == [Listing.Status.PENDING] * 3

    trust_services.resolve_deal_dispute(
        staff=staff("moderator"),
        case=deal.dispute.case,
        deal=deal,
        outcome="completed",
        reason="Photos match the listing.",
    )

    assert [status(x) for x in (listing, jacket, boots)] == [Listing.Status.SOLD] * 3
    assert status(jacket_fan) == S.EXPIRED


@pytest.mark.django_db
def test_a_canceled_trade_decision_releases_every_item(trade, buyer, seller, listing):
    deal, jacket, boots, jacket_fan = trade
    services.confirm_handoff(deal=deal, actor=buyer)
    Deal.objects.filter(pk=deal.pk).update(handoff_deadline=past())
    services.settle_due_deals()
    assert status(deal) == S.DISPUTED

    trust_services.resolve_deal_dispute(
        staff=staff("moderator"),
        case=deal.dispute.case,
        deal=deal,
        outcome="canceled",
        reason="No sign the swap happened.",
    )

    assert [status(x) for x in (listing, jacket, boots)] == [Listing.Status.AVAILABLE] * 3
    assert status(jacket_fan) == S.AWAITING_SELLER


@pytest.mark.django_db
def test_an_inactive_backup_buyer_is_skipped(queue, buyer):
    primary, backups = queue
    first = backups[0].buyer
    first.is_active = False
    first.save(update_fields=["is_active"])

    services.cancel_deal(deal=primary, actor=buyer)

    assert status(backups[0]) == S.CANCELED
    assert status(backups[1]) == S.AWAITING_SELLER


@pytest.mark.django_db
def test_a_canceled_decision_promotes_at_most_one_backup(queue, buyer, seller):
    primary, backups = queue
    services.confirm_handoff(deal=primary, actor=buyer)
    services.report_problem(deal=primary, actor=seller, kind="no_show")
    assert status(primary) == S.DISPUTED

    trust_services.resolve_deal_dispute(
        staff=staff("moderator"),
        case=primary.dispute.case,
        deal=primary,
        outcome="canceled",
        reason="Buyer never came.",
    )

    assert [status(b) for b in backups] == [S.AWAITING_SELLER, S.BACKUP, S.BACKUP]


@pytest.mark.django_db
def test_the_admin_can_view_deals_but_not_change_or_delete_them(listing, buyer):
    deal = request(listing, buyer)
    superuser = verified_user("superuser")
    superuser.is_staff = superuser.is_superuser = True
    superuser.save(update_fields=["is_staff", "is_superuser"])
    admin_client = Client()
    admin_client.force_login(superuser)
    assert admin_client.get(f"/admin/deals/deal/{deal.pk}/change/").status_code == 200
    admin_client.post(f"/admin/deals/deal/{deal.pk}/change/", {"status": "completed"})
    admin_client.post(f"/admin/deals/deal/{deal.pk}/delete/", {"post": "yes"})
    assert status(deal) == S.AWAITING_SELLER
    assert admin_client.get("/admin/deals/deal/add/").status_code == 403


@pytest.mark.django_db
def test_backup_actions_differ_for_the_buyer_and_the_seller(queue, seller):
    _, backups = queue
    client = Client()
    client.force_login(seller)
    seller_view = client.get(f"/api/deals/{backups[0].pk}/").json()["actions"]
    client.force_login(backups[0].buyer)
    buyer_view = client.get(f"/api/deals/{backups[0].pk}/").json()["actions"]
    assert (seller_view["decline"], seller_view["cancel"], seller_view["accept"]) == (
        True,
        False,
        False,
    )
    assert (buyer_view["decline"], buyer_view["cancel"], buyer_view["accept"]) == (
        False,
        True,
        False,
    )
