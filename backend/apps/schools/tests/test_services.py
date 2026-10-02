import pytest

from apps.schools.models import School, SchoolDomain
from apps.schools.services import school_for_email


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("email", "slug"),
    [
        ("terp@umd.edu", "umd"),
        ("Terp@UMD.EDU", "umd"),
        ("terp@terpmail.umd.edu", "umd"),
        ("terp@gmail.com", None),
        ("terp@fakeumd.edu", None),
        ("terp@umd.edu.evil.com", None),
        ("terp@cs.umd.edu", None),
        ("terp@fake-terpmail.umd.edu", None),
    ],
)
def test_school_for_email(email, slug):
    school = school_for_email(email)
    assert (school.slug if school else None) == slug


@pytest.mark.django_db
def test_new_school_is_a_database_row():
    gw = School.objects.create(name="George Washington University", short_name="GW", slug="gw")
    SchoolDomain.objects.create(school=gw, domain=" GWU.edu ")
    assert school_for_email("colonial@gwu.edu") == gw


@pytest.mark.django_db
def test_inactive_school_does_not_match():
    School.objects.filter(slug="umd").update(is_active=False)
    assert school_for_email("terp@umd.edu") is None
