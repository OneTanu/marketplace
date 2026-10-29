import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client
from PIL import Image
from procrastinate import testing
from procrastinate.contrib.django import app

from apps.accounts.models import User
from apps.listings import services as listing_services
from apps.listings.models import Category, Listing
from apps.notifications import services, tasks
from apps.notifications.models import Notification, SavedSearch, SavedSearchMatch
from apps.schools.models import MarketplaceStatus, School
from apps.trust.models import Block, UserRestriction

LIST_URL = "/api/saved-searches/"


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def umd():
    return School.objects.get(slug="umd")


@pytest.fixture
def gw():
    return School.objects.create(
        name="George Washington University",
        short_name="GW",
        slug="gw",
        marketplace_status=MarketplaceStatus.OPEN,
    )


def student(email, school):
    return User.objects.create_user(
        email, "pw-123456789", username=email.split("@")[0], school=school
    )


@pytest.fixture
def searcher(umd):
    return student("searcher@umd.edu", umd)


@pytest.fixture
def seller(umd):
    return student("seller@umd.edu", umd)


@pytest.fixture
def client(searcher):
    client = Client()
    client.force_login(searcher)
    return client


def image():
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, "JPEG")
    return SimpleUploadedFile("photo.jpg", buffer.getvalue())


def post(seller, title="Blue denim jacket", *, category="men-jeans", price_cents=2500, **details):
    return listing_services.create_item_listing(
        seller,
        category=Category.objects.get(slug=category),
        title=title,
        price_cents=price_cents,
        condition=details.pop("condition", "good"),
        photos=[image()],
        **details,
    )


def save(user, **filters):
    return services.create_saved_search(user, **filters)


def alerts_for(user):
    return Notification.objects.filter(user=user, kind=Notification.Kind.SAVED_SEARCH)


def category(slug):
    return Category.objects.get(slug=slug)


# --- Saving searches (API) ---


@pytest.mark.django_db
def test_saving_a_search_with_a_generated_name(client, searcher):
    response = client.post(
        LIST_URL,
        {
            "filters": {
                "q": "  denim   jacket ",
                "category": "men-jeans",
                "brand": "Levi's",
                "size": "32x30",
                "max_price": 4000,
                "color": "blue",
                "condition": "like_new",
                "sort": "price_asc",
            }
        },
        content_type="application/json",
    )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert (
        body["name"]
        == "“denim jacket” · Men › Jeans · Levi's · 32x30 · Blue · Like new · Under $40"
    )
    assert body["alerts_enabled"] is True
    assert body["filters"] == {
        "q": "denim jacket",
        "school": "",
        "category": "men-jeans",
        "brand": "Levi's",
        "min_price": None,
        "max_price": 4000,
        "size": "32x30",
        "condition": "like_new",
        "color": "blue",
        "sort": "price_asc",
    }
    assert SavedSearch.objects.get().user == searcher


@pytest.mark.django_db
def test_school_scope_round_trips(client, gw):
    for school in ("all", "gw", ""):
        response = client.post(
            LIST_URL,
            {"name": f"Lamps {school}", "filters": {"q": "lamp", "school": school}},
            content_type="application/json",
        )
        assert response.status_code == 201, response.json()
        assert response.json()["filters"]["school"] == school
    assert SavedSearch.objects.get(name="Lamps all").all_schools is True
    assert SavedSearch.objects.get(name="Lamps gw").school == gw


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("filters", "field"),
    [
        ({}, "detail"),
        ({"school": "all"}, "detail"),  # a scope alone isn't a search
        ({"q": "x", "school": "nowhere"}, "filters"),
        ({"category": "not-a-category"}, "filters"),
        ({"condition": "mint"}, "filters"),
        ({"color": "plaid"}, "filters"),
        ({"min_price": -1}, "filters"),
        ({"min_price": 5000, "max_price": 1000}, "max_price_cents"),
        ({"q": "x", "sort": "random"}, "filters"),
        ({"q": "x" * 101}, "filters"),
    ],
)
def test_invalid_searches_are_refused(client, filters, field):
    response = client.post(LIST_URL, {"filters": filters}, content_type="application/json")

    assert response.status_code == 400
    assert field in response.json()
    assert not SavedSearch.objects.exists()


@pytest.mark.django_db
def test_unknown_filter_keys_are_not_stored(client):
    response = client.post(
        LIST_URL,
        {"filters": {"q": "lamp", "price_drop": True, "seller": 1}},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert set(response.json()["filters"]) == {
        "q", "school", "category", "brand", "min_price", "max_price",
        "size", "condition", "color", "sort",
    }  # fmt: skip


@pytest.mark.django_db
def test_the_same_filters_cant_be_saved_twice(client, searcher):
    save(searcher, query="lamp", brand="IKEA")

    response = client.post(
        LIST_URL,
        # Same filters, different whitespace, name and sort.
        {"name": "Again", "filters": {"q": " lamp ", "brand": "IKEA", "sort": "price_desc"}},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json() == {"detail": services.ALREADY_SAVED}


@pytest.mark.django_db
def test_the_database_refuses_duplicate_filters(searcher):
    SavedSearch.objects.create(user=searcher, name="One", query="lamp")

    with pytest.raises(IntegrityError):
        SavedSearch.objects.create(user=searcher, name="Two", query="lamp")


@pytest.mark.django_db
def test_saved_searches_are_limited_per_student(client, searcher, umd):
    for i in range(services.MAX_SAVED_SEARCHES):
        save(searcher, query=f"thing {i}")
    # Someone else's searches don't count.
    save(student("other@umd.edu", umd), query="lamp")

    response = client.post(LIST_URL, {"filters": {"q": "lamp"}}, content_type="application/json")

    assert response.status_code == 400
    assert response.json() == {"detail": services.TOO_MANY_SEARCHES}


@pytest.mark.django_db
def test_listing_renaming_toggling_and_deleting(client, searcher, umd):
    mine = save(searcher, query="lamp", name="Lamps")
    save(student("other@umd.edu", umd), query="desk")

    assert [s["name"] for s in client.get(LIST_URL).json()] == ["Lamps"]

    url = f"{LIST_URL}{mine.pk}/"
    renamed = client.patch(url, {"name": "  Desk   lamps "}, content_type="application/json")
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Desk lamps"
    off = client.patch(url, {"alerts_enabled": False}, content_type="application/json")
    assert off.json()["alerts_enabled"] is False
    assert off.json()["filters"]["q"] == "lamp"  # filters don't change
    assert client.patch(url, {"name": "  "}, content_type="application/json").status_code == 400

    assert client.delete(url).status_code == 204
    assert not SavedSearch.objects.filter(pk=mine.pk).exists()


@pytest.mark.django_db
def test_other_students_searches_are_a_404(client, umd):
    theirs = save(student("other@umd.edu", umd), query="lamp")
    url = f"{LIST_URL}{theirs.pk}/"

    assert client.get(url).status_code == 404
    assert client.patch(url, {"name": "Mine"}, content_type="application/json").status_code == 404
    assert client.delete(url).status_code == 404
    theirs.refresh_from_db()
    assert theirs.name != "Mine"


@pytest.mark.django_db
def test_services_refuse_another_students_search(searcher, umd):
    theirs = save(student("other@umd.edu", umd), query="lamp")

    with pytest.raises(Exception, match="isn't your saved search"):
        services.update_saved_search(theirs, searcher, name="Mine")
    with pytest.raises(Exception, match="isn't your saved search"):
        services.delete_saved_search(theirs, searcher)


@pytest.mark.django_db
def test_saved_searches_need_a_signed_in_student():
    assert Client().get(LIST_URL).status_code == 403


# --- Matching ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("filters", "listing", "matches"),
    [
        ({"query": "denim jacket"}, {"title": "Blue denim jacket"}, True),
        ({"query": "denim jacket"}, {"title": "Denim jeans"}, False),
        ({"query": "carhartt"}, {"title": "Work coat", "brand": "Carhartt"}, True),
        ({"query": "vintage"}, {"title": "Coat", "description": "Vintage, 1990s"}, True),
        ({"category": "men"}, {"category": "men-jeans"}, True),
        ({"category": "men-jeans"}, {"category": "men-jeans"}, True),
        ({"category": "men-pants"}, {"category": "men-jeans"}, False),
        ({"category": "women"}, {"category": "men-jeans"}, False),
        ({"brand": "nike"}, {"brand": "Nike"}, True),
        ({"brand": "nike"}, {"brand": "Adidas"}, False),
        ({"min_price_cents": 2000}, {"price_cents": 2500}, True),
        ({"min_price_cents": 3000}, {"price_cents": 2500}, False),
        ({"max_price_cents": 2500}, {"price_cents": 2500}, True),
        ({"max_price_cents": 2000}, {"price_cents": 2500}, False),
        ({"size": "32x30"}, {"size": "32X30"}, True),  # waist 32, inseam 30
        ({"size": "32x30"}, {"size": "32x32"}, False),
        ({"size": "M"}, {"size": "m"}, True),
        ({"color": "blue"}, {"color": "blue"}, True),
        ({"color": "blue"}, {"color": "red"}, False),
        ({"condition": "like_new"}, {"condition": "like_new"}, True),
        ({"condition": "like_new"}, {"condition": "good"}, False),
        (
            {"query": "jacket", "category": "men", "brand": "levi's", "max_price_cents": 3000},
            {"title": "Trucker jacket", "brand": "Levi's", "price_cents": 2900},
            True,
        ),
        (
            {"query": "jacket", "category": "men", "brand": "levi's", "max_price_cents": 3000},
            {"title": "Trucker jacket", "brand": "Levi's", "price_cents": 3100},
            False,
        ),
    ],
)
def test_alerts_match_every_filter(searcher, seller, filters, listing, matches):
    if "category" in filters:
        filters["category"] = category(filters["category"])
    save(searcher, **filters)

    notified = services.alert_saved_searches(listing_id=post(seller, **listing).pk)

    assert notified == int(matches)
    assert alerts_for(searcher).count() == int(matches)


@pytest.mark.django_db
def test_an_alert_links_to_the_listing(searcher, seller):
    save(searcher, query="denim", name="Denim")
    listing = post(seller, "Blue denim jacket", price_cents=2500)

    services.alert_saved_searches(listing_id=listing.pk)

    alert = alerts_for(searcher).get()
    assert alert.title == "New match for “Denim”"
    assert alert.body == "Blue denim jacket, $25"
    assert alert.link == f"/listings/{listing.pk}"
    match = SavedSearchMatch.objects.get()
    assert (match.user, match.listing, match.notification) == (searcher, listing, alert)


@pytest.mark.django_db
def test_school_scope(searcher, seller, gw):
    colonial = student("colonial@gwu.edu", gw)
    home = save(searcher, query="denim", name="Home")
    save(searcher, query="denim", school=gw, name="GW")

    services.alert_saved_searches(listing_id=post(colonial, "Denim at GW").pk)
    # Only the GW search matched a GW listing; the home-school one didn't.
    assert list(alerts_for(searcher).values_list("title", flat=True)) == ["New match for “GW”"]

    home.delete()
    everywhere = save(student("roamer@umd.edu", searcher.school), query="denim", all_schools=True)
    services.alert_saved_searches(listing_id=post(colonial, "More denim at GW").pk)
    assert alerts_for(everywhere.user).count() == 1


@pytest.mark.django_db
def test_no_alert_for_a_closed_schools_listing_on_an_all_schools_search(searcher, gw):
    save(searcher, query="denim", all_schools=True)
    listing = post(student("colonial@gwu.edu", gw), "Denim")
    gw.marketplace_status = MarketplaceStatus.PAUSED
    gw.save()

    assert services.alert_saved_searches(listing_id=listing.pk) == 0


@pytest.mark.django_db
def test_no_alert_about_your_own_listing(seller):
    save(seller, query="denim")

    assert services.alert_saved_searches(listing_id=post(seller).pk) == 0


@pytest.mark.django_db
def test_no_alert_when_alerts_are_off_but_the_search_still_runs(client, searcher, seller):
    search = save(searcher, query="denim")
    services.update_saved_search(search, searcher, alerts_enabled=False)
    listing = post(seller)

    assert services.alert_saved_searches(listing_id=listing.pk) == 0
    # Running it is just the feed with its filters.
    results = client.get("/api/listings/", {"q": "denim"}).json()["results"]
    assert [card["id"] for card in results] == [listing.pk]


@pytest.mark.django_db
def test_no_alert_across_a_block(searcher, seller, umd):
    other = student("other@umd.edu", umd)
    save(searcher, query="denim")
    save(other, query="denim")
    Block.objects.create(blocker=searcher, blocked=seller)

    services.alert_saved_searches(listing_id=post(seller).pk)
    assert not alerts_for(searcher).exists()
    assert alerts_for(other).count() == 1

    Block.objects.all().delete()
    Block.objects.create(blocker=seller, blocked=searcher)
    services.alert_saved_searches(listing_id=post(seller, "Denim two").pk)
    assert not alerts_for(searcher).exists()


@pytest.mark.django_db
def test_no_alert_for_a_restricted_seller_or_an_inactive_searcher(searcher, seller, umd):
    save(searcher, query="denim")
    inactive = student("inactive@umd.edu", umd)
    save(inactive, query="denim")
    User.objects.filter(pk=inactive.pk).update(is_active=False)
    listing = post(seller)
    UserRestriction.objects.create(user=seller, kind=UserRestriction.Kind.SELLING, reason="x")

    assert services.alert_saved_searches(listing_id=listing.pk) == 0


@pytest.mark.django_db
@pytest.mark.parametrize("status", [Listing.Status.PENDING, Listing.Status.REMOVED])
def test_no_alert_once_the_listing_isnt_available(searcher, seller, status):
    save(searcher, query="denim")
    listing = post(seller)
    Listing.objects.filter(pk=listing.pk).update(status=status)

    assert services.alert_saved_searches(listing_id=listing.pk) == 0
    assert services.alert_saved_searches(listing_id=999999) == 0


@pytest.mark.django_db
def test_alerts_are_sent_once_however_often_the_job_runs(searcher, seller):
    save(searcher, query="denim")
    save(searcher, brand="Levi's")  # a second matching search
    listing = post(seller, brand="Levi's")

    assert services.alert_saved_searches(listing_id=listing.pk) == 1
    assert services.alert_saved_searches(listing_id=listing.pk) == 0

    assert alerts_for(searcher).count() == 1
    assert SavedSearchMatch.objects.count() == 1


@pytest.mark.django_db
def test_the_database_refuses_a_second_match(searcher, seller):
    listing = post(seller)
    SavedSearchMatch.objects.create(user=searcher, listing=listing)

    with pytest.raises(IntegrityError):
        SavedSearchMatch.objects.create(user=searcher, listing=listing)


@pytest.mark.django_db
def test_editing_a_listing_sends_no_alert(searcher, seller):
    """Only new listings alert: there are no price-drop (or other edit) alerts."""
    listing = post(seller, price_cents=5000)
    save(searcher, query="denim", max_price_cents=3000)

    listing_services.update_item_listing(listing, seller, price_cents=2500)

    assert not alerts_for(searcher).exists()
    assert (
        not Notification.objects.exclude(kind=Notification.Kind.SAVED_SEARCH)
        .filter(user=searcher)
        .exists()
    )


# --- The job ---


@pytest.fixture
def in_memory_jobs():
    with app.replace_connector(testing.InMemoryConnector()) as in_memory_app:
        yield in_memory_app


@pytest.mark.django_db
def test_posting_a_listing_queues_the_alert_job(searcher, seller, in_memory_jobs):
    save(searcher, query="denim")

    listing = post(seller)

    jobs = [j for j in in_memory_jobs.connector.jobs.values() if j["task_name"].startswith("not")]
    assert [(j["task_name"], j["args"]) for j in jobs] == [
        ("notifications.alert_saved_searches", {"listing_id": listing.pk})
    ]
    assert not alerts_for(searcher).exists()  # nothing until the job runs
    # The worker runs jobs on its own database connection, which can't see this test's
    # uncommitted rows, so run the queued task's function here.
    tasks.alert_saved_searches(**jobs[0]["args"])
    assert alerts_for(searcher).count() == 1


@pytest.mark.django_db
def test_a_listing_that_fails_to_post_queues_nothing(searcher, seller, in_memory_jobs):
    save(searcher, query="denim")

    with pytest.raises(ValidationError):
        post(seller, price_cents=0)  # $0 outside Free

    assert not in_memory_jobs.connector.jobs
