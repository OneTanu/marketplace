from django.urls import path

from . import views

urlpatterns = [
    path("deals/", views.DealListView.as_view(), name="deal-list"),
    path(
        "meetup-preferences/",
        views.MeetupPreferenceView.as_view(),
        name="meetup-preferences",
    ),
    path("deals/<int:pk>/", views.DealDetailView.as_view(), name="deal-detail"),
    path("deals/<int:pk>/accept/", views.AcceptDealView.as_view(), name="deal-accept"),
    path("deals/<int:pk>/decline/", views.DeclineDealView.as_view(), name="deal-decline"),
    path("deals/<int:pk>/cancel/", views.CancelDealView.as_view(), name="deal-cancel"),
    path("deals/<int:pk>/counter/", views.CounterOfferView.as_view(), name="deal-counter"),
    path(
        "deals/<int:pk>/report-problem/",
        views.ReportProblemView.as_view(),
        name="deal-report-problem",
    ),
    path("deals/<int:pk>/archive/", views.ArchiveDealView.as_view(), name="deal-archive"),
    path("deals/<int:pk>/trade-offer/", views.TradeOfferView.as_view(), name="deal-trade-offer"),
    path(
        "deals/<int:pk>/trade-options/",
        views.TradeOptionsView.as_view(),
        name="deal-trade-options",
    ),
    path(
        "deals/<int:pk>/meetup-proposals/",
        views.MeetupProposalCreateView.as_view(),
        name="deal-meetup-propose",
    ),
    path(
        "deals/<int:pk>/meetup-proposals/accept/",
        views.MeetupProposalAcceptView.as_view(),
        name="deal-meetup-accept",
    ),
    path(
        "deals/<int:pk>/meetup-status/",
        views.MeetupStatusCreateView.as_view(),
        name="deal-meetup-status",
    ),
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
    path(
        "listings/<int:listing_id>/meetup-options/",
        views.ListingMeetupOptionsView.as_view(),
        name="listing-meetup-options",
    ),
]
