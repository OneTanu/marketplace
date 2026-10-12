from django.urls import path

from . import views

urlpatterns = [
    path("deals/", views.DealListView.as_view(), name="deal-list"),
    path("deals/<int:pk>/", views.DealDetailView.as_view(), name="deal-detail"),
    path("deals/<int:pk>/accept/", views.AcceptDealView.as_view(), name="deal-accept"),
    path("deals/<int:pk>/decline/", views.DeclineDealView.as_view(), name="deal-decline"),
    path("deals/<int:pk>/cancel/", views.CancelDealView.as_view(), name="deal-cancel"),
    path("deals/<int:pk>/counter/", views.CounterOfferView.as_view(), name="deal-counter"),
    path(
        "deals/<int:pk>/confirm-handoff/",
        views.ConfirmHandoffView.as_view(),
        name="deal-confirm-handoff",
    ),
    path(
        "listings/<int:listing_id>/deals/",
        views.ListingDealCreateView.as_view(),
        name="listing-deal-create",
    ),
]
