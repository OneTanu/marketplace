import pytest

from apps.deals.tests.test_services import listing_for, verified_user
from apps.trust import services
from apps.trust.models import Report
from apps.trust.tests.test_moderation import report_listing, staff


@pytest.mark.django_db
def test_repeat_offenders_are_flagged_in_the_queue_and_case(client):
    moderator = staff("rs-mod")
    seller = verified_user("rs-seller")
    for index in range(2):
        case = report_listing(verified_user(f"rs-rep{index}"), listing_for(seller)).case
        services.warn_user(staff=moderator, case=case, user=seller, reason="Again")
    third = report_listing(verified_user("rs-rep-last"), listing_for(seller)).case
    client.force_login(moderator)

    row = next(r for r in client.get("/api/moderation/cases/").json() if r["id"] == third.pk)
    assert row["recent_consequences"] == 2
    subject = client.get(f"/api/moderation/cases/{third.pk}/").json()["subject"]
    assert subject["repeat_offender"] is True


@pytest.mark.django_db
def test_reporters_whose_reports_are_mostly_dismissed_are_flagged(client):
    moderator = staff("fr-mod")
    reporter = verified_user("fr-reporter")
    for index in range(3):
        case = report_listing(reporter, listing_for(verified_user(f"fr-s{index}"))).case
        services.dismiss_case(staff=moderator, case=case, reason="Nothing wrong")
    open_case = report_listing(reporter, listing_for(verified_user("fr-last"))).case
    client.force_login(moderator)

    record = client.get(f"/api/moderation/cases/{open_case.pk}/").json()["reporter_records"][0]
    assert record == {
        "user": {"id": reporter.pk, "username": "fr-reporter", "first_name": ""},
        "reviewed": 3,
        "upheld": 0,
        "possible_false_reporter": True,
    }
    stats = client.get("/api/moderation/stats/").json()
    assert [row["user"]["username"] for row in stats["possible_false_reporters"]] == ["fr-reporter"]


@pytest.mark.django_db
def test_stats_count_volume_outcomes_and_appeals(client):
    moderator = staff("st2-mod")
    other = staff("st2-other")
    seller = verified_user("st2-seller")
    weapon = report_listing(
        verified_user("st2-a"), listing_for(seller), prohibited_category="weapon"
    )
    report_listing(verified_user("st2-b"), listing_for(seller), reason=Report.Reason.SPAM)
    action = services.warn_user(staff=moderator, case=weapon.case, user=seller, reason="Warn")
    services.resolve_case(staff=moderator, case=weapon.case, reason="Done")
    appeal = services.file_appeal(user=seller, action_id=action.pk, message="Please")
    services.decide_appeal(staff=other, appeal=appeal, uphold=True, reason="Stands")
    client.force_login(moderator)

    stats = client.get("/api/moderation/stats/?days=7").json()
    assert stats["cases_opened"] == 2
    assert stats["reports"] == 2
    assert {row["key"]: row["count"] for row in stats["reports_by_reason"]} == {
        "prohibited_item": 1,
        "spam": 1,
    }
    assert {row["key"] for row in stats["outcomes"]} == {"warn"}
    assert stats["median_hours_to_first_action"] is not None
    assert (stats["appeals_filed"], stats["appeals_upheld"]) == (1, 1)

    client.force_login(verified_user("st2-student"))
    assert client.get("/api/moderation/stats/").status_code == 403
