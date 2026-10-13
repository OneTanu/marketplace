from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.deals import services as deal_services
from apps.deals.models import Deal
from apps.deals.tests.test_services import listing_for, verified_user
from apps.listings.models import Listing
from apps.notifications.models import Notification
from apps.trust import checks, services
from apps.trust.models import Appeal, ModerationAction, ModerationCase, Report
from apps.trust.tests.test_moderation import report_listing, staff

Kind = services.Kind


def notices(user, kind=None):
    rows = Notification.objects.filter(user=user)
    return rows.filter(kind=kind) if kind else rows


@pytest.mark.django_db
def test_a_warning_tells_the_student_without_the_internal_reason():
    moderator = staff("n-mod")
    seller = verified_user("n-seller")
    case = report_listing(verified_user("n-reporter"), listing_for(seller)).case

    services.warn_user(staff=moderator, case=case, user=seller, reason="Internal: 3rd strike")

    notice = notices(seller, Notification.Kind.MODERATION_NOTICE).get()
    assert notice.title == "A warning from Tanu's moderators"
    assert "prohibited item" in notice.body
    assert "appeal within 14 days" in notice.body
    assert "3rd strike" not in notice.body
    assert notice.link == "/profile/standing"


@pytest.mark.django_db
def test_reporters_hear_the_outcome_when_a_case_closes():
    moderator = staff("o-mod")
    reporter = verified_user("o-reporter")
    seller = verified_user("o-seller")
    dismissed = report_listing(reporter, listing_for(seller)).case
    services.dismiss_case(staff=moderator, case=dismissed, reason="Fine")
    acted = report_listing(reporter, listing_for(seller), reason=Report.Reason.SPAM).case
    services.warn_user(staff=moderator, case=acted, user=seller, reason="Spam")
    services.resolve_case(staff=moderator, case=acted, reason="Warned")

    bodies = list(notices(reporter, Notification.Kind.REPORT_UPDATE).values_list("body", flat=True))
    assert any("took action" in body for body in bodies)
    assert any("didn't find a violation" in body for body in bodies)


@pytest.mark.django_db
def test_moderation_cancellations_are_announced_but_block_cancellations_are_not():
    moderator = staff("c-mod")
    seller = verified_user("cn-seller")
    buyer = verified_user("cn-buyer")
    listing = listing_for(seller)
    deal_services.create_deal(listing=listing, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    case = report_listing(verified_user("cn-reporter"), listing).case
    services.remove_listing(staff=moderator, case=case, listing=listing, reason="Weapon")
    assert notices(buyer, Notification.Kind.DEAL).get().title == "A deal was canceled by Tanu"

    other = listing_for(seller)
    deal_services.create_deal(listing=other, buyer=buyer, kind=Deal.Kind.BUY_NOW)
    services.block_user(blocker=seller, blocked=buyer)
    assert notices(buyer, Notification.Kind.DEAL).count() == 1


@pytest.mark.django_db
def test_moderators_can_ask_a_question_and_see_the_answer():
    moderator = staff("i-mod")
    reporter = verified_user("i-reporter")
    case = report_listing(reporter, listing_for(verified_user("i-seller"))).case

    info = services.request_info(
        staff=moderator, case=case, user=reporter, question="When did you see it?"
    )
    assert notices(reporter, Notification.Kind.INFO_REQUEST).exists()
    with pytest.raises(ValidationError):
        services.answer_info_request(
            user=verified_user("i-other"), info_request_id=info.pk, answer="x"
        )

    services.answer_info_request(user=reporter, info_request_id=info.pk, answer="Yesterday")
    with pytest.raises(ValidationError, match="already answered"):
        services.answer_info_request(user=reporter, info_request_id=info.pk, answer="Again")
    assert case.actions.filter(kind=ModerationAction.Kind.INFO_RECEIVED, actor=reporter).exists()
    assert notices(moderator, Notification.Kind.STAFF_ALERT).filter(body="Yesterday").exists()


@pytest.mark.django_db
def test_an_appeal_is_decided_by_someone_else_and_overturning_undoes_it():
    first = staff("ap-first")
    second = staff("ap-second")
    seller = verified_user("ap-seller")
    listing = listing_for(seller)
    case = report_listing(verified_user("ap-reporter"), listing).case
    restriction = services.restrict_user(
        staff=first, case=case, user=seller, kind=Kind.SELLING, reason="Prohibited"
    )
    removal = services.remove_listing(staff=first, case=case, listing=listing, reason="Weapon")

    appeal = services.file_appeal(user=seller, action_id=restriction.action_id, message="Mistake")
    case.refresh_from_db()
    assert case.status == ModerationCase.Status.APPEALED
    with pytest.raises(ValidationError, match="already appealed"):
        services.file_appeal(user=seller, action_id=restriction.action_id, message="Again")
    with pytest.raises(PermissionDenied, match="different moderator"):
        services.decide_appeal(staff=first, appeal=appeal, uphold=False, reason="x")

    services.decide_appeal(staff=second, appeal=appeal, uphold=False, reason="Agreed")
    checks.require_can(seller, Kind.SELLING)
    removal_appeal = services.file_appeal(user=seller, action_id=removal.pk, message="It's a toy")
    services.decide_appeal(staff=second, appeal=removal_appeal, uphold=False, reason="Toy")
    assert Listing.objects.get(pk=listing.pk).status == Listing.Status.AVAILABLE
    case.refresh_from_db()
    assert case.status == ModerationCase.Status.RESOLVED
    assert notices(seller, Notification.Kind.APPEAL_UPDATE).count() == 2


@pytest.mark.django_db
def test_appeals_close_after_14_days_and_only_cover_your_own_decisions():
    moderator = staff("w-mod")
    seller = verified_user("w-seller")
    case = report_listing(verified_user("w-reporter"), listing_for(seller)).case
    action = services.warn_user(staff=moderator, case=case, user=seller, reason="Warn")

    with pytest.raises(ValidationError, match="couldn't find"):
        services.file_appeal(user=verified_user("w-other"), action_id=action.pk, message="Hi")
    ModerationAction.objects.filter(pk=action.pk).update(
        created_at=timezone.now() - timedelta(days=15)
    )
    with pytest.raises(ValidationError, match="window has closed"):
        services.file_appeal(user=seller, action_id=action.pk, message="Late")
    assert not Appeal.objects.exists()


@pytest.mark.django_db
def test_urgent_reports_alert_moderators_without_a_conflict():
    free = staff("u-free")
    conflicted = staff("u-conflicted")
    seller = verified_user("u-seller")
    deal_services.create_deal(listing=listing_for(seller), buyer=conflicted, kind=Deal.Kind.BUY_NOW)

    report_listing(verified_user("u-reporter"), listing_for(seller), prohibited_category="weapon")

    assert notices(free, Notification.Kind.STAFF_ALERT).filter(title__startswith="Urgent").exists()
    assert not notices(conflicted, Notification.Kind.STAFF_ALERT).exists()


@pytest.mark.django_db
def test_my_standing_shows_decisions_and_lets_me_appeal(client):
    moderator = staff("st-mod")
    seller = verified_user("st-seller")
    case = report_listing(verified_user("st-reporter"), listing_for(seller)).case
    action = services.warn_user(
        staff=moderator, case=case, user=seller, reason="Internal note", user_message="Be careful."
    )
    client.force_login(seller)

    standing = client.get("/api/me/standing/").json()
    notice = standing["notices"][0]
    assert notice["message"] == "Be careful."
    assert notice["can_appeal"] is True
    assert "Internal note" not in str(standing)

    filed = client.post(
        "/api/me/appeals/",
        {"action_id": action.pk, "message": "I removed it"},
        content_type="application/json",
    )
    assert filed.status_code == 201
    assert client.get("/api/me/standing/").json()["notices"][0]["appeal"]["status"] == "pending"
