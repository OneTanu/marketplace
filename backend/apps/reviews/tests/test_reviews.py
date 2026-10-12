import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.deals import services as deal_services
from apps.deals.models import Deal
from apps.deals.tests.test_services import listing_for, verified_user
from apps.reviews.models import Review
from apps.reviews.services import create_review


def completed_deal():
    seller = verified_user("seller")
    buyer = verified_user("buyer")
    deal = deal_services.create_deal(
        listing=listing_for(seller), buyer=buyer, kind=Deal.Kind.BUY_NOW
    )
    deal_services.accept_deal(deal=deal, actor=seller)
    deal_services.confirm_handoff(deal=deal, actor=buyer)
    deal_services.confirm_handoff(deal=deal, actor=seller)
    deal.refresh_from_db()
    return deal, buyer, seller


@pytest.mark.django_db
def test_completed_parties_review_each_other_once():
    deal, buyer, seller = completed_deal()

    review = create_review(deal=deal, author=buyer, rating=5, comment="  Easy meetup.  ")

    assert review.subject == seller
    assert review.comment == "Easy meetup."
    with pytest.raises(ValidationError):
        create_review(deal=deal, author=buyer, rating=4)


@pytest.mark.django_db
def test_review_requires_completed_deal_and_party():
    deal, buyer, _seller = completed_deal()
    outsider = verified_user("outsider")

    with pytest.raises(PermissionDenied):
        create_review(deal=deal, author=outsider, rating=5)

    deal.status = Deal.Status.PENDING
    deal.save(update_fields=["status"])
    with pytest.raises(ValidationError):
        create_review(deal=deal, author=buyer, rating=5)


@pytest.mark.django_db
def test_review_api_is_private_to_deal_parties(client):
    deal, buyer, _seller = completed_deal()
    outsider = verified_user("outsider")
    client.force_login(buyer)

    created = client.post(
        f"/api/deals/{deal.pk}/reviews/",
        {"rating": 5, "comment": "Great"},
        content_type="application/json",
    )

    assert created.status_code == 201
    assert created.json()["subject"]["username"] == "seller"
    assert Review.objects.count() == 1
    client.force_login(outsider)
    assert client.get(f"/api/deals/{deal.pk}/reviews/").status_code == 404
