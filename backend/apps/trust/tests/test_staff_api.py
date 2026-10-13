from datetime import timedelta

import pytest
from django.utils import timezone

from apps.deals import services as deal_services
from apps.deals.models import Deal
from apps.deals.tests.test_services import listing_for, verified_user
from apps.listings.models import Listing
from apps.trust.models import EvidenceAccess, ModerationAction, Report, UserRestriction
from apps.trust.tests.test_moderation import report_listing, staff


def act(client, case_id, **body):
    return client.post(
        f"/api/moderation/cases/{case_id}/actions/", body, content_type="application/json"
    )


@pytest.mark.django_db
def test_students_get_403_on_every_moderation_endpoint(client):
    case = report_listing(verified_user("s403-reporter"), listing_for(verified_user("s403-s"))).case
    client.force_login(verified_user("s403-student"))

    for url in (
        "/api/moderation/cases/",
        "/api/moderation/summary/",
        f"/api/moderation/cases/{case.pk}/",
    ):
        assert client.get(url).status_code == 403
    assert act(client, case.pk, action="dismiss", reason="x").status_code == 403
    assert (
        client.post(
            "/api/moderation/restrictions/1/lift/", {"reason": "x"}, content_type="application/json"
        ).status_code
        == 403
    )
    assert client.get("/api/me/").json()["is_moderator"] is False


@pytest.mark.django_db
def test_queue_counts_reports_and_flags_repeat_subjects(client):
    moderator = staff("q-mod")
    seller = verified_user("q-seller")
    first = listing_for(seller)
    report_listing(verified_user("q-a"), first, prohibited_category="weapon")
    report_listing(verified_user("q-b"), first, prohibited_category="weapon")
    report_listing(verified_user("q-c"), listing_for(seller), reason=Report.Reason.SPAM)
    client.force_login(moderator)

    rows = client.get("/api/moderation/cases/").json()
    assert [row["priority_label"] for row in rows] == ["Urgent", "Normal"]
    assert rows[0]["report_count"] == 2
    assert rows[0]["reporter_count"] == 2
    assert rows[0]["prior_case_count"] == 1
    assert client.get("/api/moderation/cases/?priority=3").json()[0]["reasons"] == ["spam"]
    assert len(client.get("/api/moderation/cases/?repeat=true").json()) == 2
    summary = client.get("/api/moderation/summary/").json()
    assert summary == {"open": 2, "urgent": 1, "assigned_to_me": 0, "escalated": 0}
    assert client.get("/api/me/").json()["is_moderator"] is True


@pytest.mark.django_db
def test_case_detail_shows_evidence_and_history_and_logs_the_view(client):
    moderator = staff("d-mod")
    listing = listing_for(verified_user("d-seller"))
    report = report_listing(verified_user("d-reporter"), listing, details="Sharp blade")
    client.force_login(moderator)

    detail = client.get(f"/api/moderation/cases/{report.case_id}/").json()
    assert detail["reports"][0]["details"] == "Sharp blade"
    assert detail["reports"][0]["evidence"][0]["data"]["title"] == listing.title
    assert detail["subject"]["user"]["username"] == "d-seller"
    assert detail["viewer"] == {
        "can_act": True,
        "is_senior": False,
        "conflict": None,
        "conflict_overridable": False,
    }
    assert {u["username"] for u in detail["involved_users"]} == {"d-seller", "d-reporter"}
    assert EvidenceAccess.objects.filter(staff=moderator, case=report.case).exists()


@pytest.mark.django_db
def test_actions_through_the_api_are_checked_and_recorded(client):
    moderator = staff("a-mod")
    senior = staff("a-senior", senior=True)
    seller = verified_user("a-seller")
    listing = listing_for(seller)
    case = report_listing(verified_user("a-reporter"), listing).case
    client.force_login(moderator)

    missing_reason = act(client, case.pk, action="warn", reason="")
    assert missing_reason.status_code == 400
    assert act(client, case.pk, action="warn", reason="First warning").status_code == 200
    restricted = act(
        client,
        case.pk,
        action="restrict",
        restriction_kind="selling",
        reason="Prohibited items",
        until=(timezone.now() + timedelta(days=3)).isoformat(),
    )
    assert restricted.status_code == 200
    assert restricted.json()["subject"]["active_restrictions"][0]["kind"] == "selling"

    suspend = act(
        client,
        case.pk,
        action="suspend",
        reason="Scam",
        until=(timezone.now() + timedelta(days=7)).isoformat(),
    )
    assert suspend.status_code == 403
    assert "senior" in suspend.json()["detail"]

    assert act(client, case.pk, action="remove_listing", reason="Weapon").status_code == 200
    assert Listing.objects.get(pk=listing.pk).status == Listing.Status.REMOVED
    kinds = list(case.actions.values_list("kind", flat=True))
    assert kinds == ["warn", "restrict", "remove_listing"]

    restriction = UserRestriction.objects.get(user=seller)
    client.force_login(senior)
    lifted = client.post(
        f"/api/moderation/restrictions/{restriction.pk}/lift/",
        {"reason": "Appeal accepted", "case_id": case.pk},
        content_type="application/json",
    )
    assert lifted.status_code == 200
    assert act(client, case.pk, action="dismiss", reason="Done").json()["case"]["status"] == (
        "resolved"
    )


@pytest.mark.django_db
def test_conflicts_show_in_the_portal_and_seniors_can_override_with_a_reason(client):
    senior = staff("c-senior", senior=True)
    seller = verified_user("c-seller")
    deal_services.create_deal(listing=listing_for(seller), buyer=senior, kind=Deal.Kind.BUY_NOW)
    case = report_listing(verified_user("c-reporter"), listing_for(seller)).case
    client.force_login(senior)

    viewer = client.get(f"/api/moderation/cases/{case.pk}/").json()["viewer"]
    assert viewer["can_act"] is False
    assert viewer["conflict_overridable"] is True
    blocked = act(client, case.pk, action="warn", reason="Warning")
    assert blocked.status_code == 403
    assert "had a deal" in blocked.json()["detail"]

    allowed = act(
        client, case.pk, action="warn", reason="Warning", override_reason="Only one on shift"
    )
    assert allowed.status_code == 200
    assert ModerationAction.objects.filter(
        case=case, kind=ModerationAction.Kind.CONFLICT_OVERRIDE
    ).exists()
