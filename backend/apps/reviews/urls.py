from django.urls import path

from .views import DealReviewView

urlpatterns = [
    path("deals/<int:deal_id>/reviews/", DealReviewView.as_view(), name="deal-reviews"),
]
