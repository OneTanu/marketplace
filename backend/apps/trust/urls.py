from django.urls import path

from . import staff_views, views

urlpatterns = [
    path("reports/", views.ReportCreateView.as_view(), name="report-create"),
    path("blocks/", views.BlockListCreateView.as_view(), name="block-list"),
    path("blocks/<str:username>/", views.BlockDeleteView.as_view(), name="block-delete"),
    path("me/restrictions/", views.MyRestrictionsView.as_view(), name="my-restrictions"),
    path("me/standing/", views.MyStandingView.as_view(), name="my-standing"),
    path("me/appeals/", views.AppealCreateView.as_view(), name="my-appeals"),
    path(
        "me/info-requests/<int:pk>/answer/",
        views.AnswerInfoRequestView.as_view(),
        name="my-info-request-answer",
    ),
    # Staff only (403 for students).
    path("moderation/cases/", staff_views.CaseQueueView.as_view(), name="moderation-queue"),
    path("moderation/stats/", staff_views.ModerationStatsView.as_view(), name="moderation-stats"),
    path("moderation/summary/", staff_views.QueueSummaryView.as_view(), name="moderation-summary"),
    path(
        "moderation/cases/<int:pk>/",
        staff_views.CaseDetailView.as_view(),
        name="moderation-case",
    ),
    path(
        "moderation/cases/<int:pk>/actions/",
        staff_views.CaseActionView.as_view(),
        name="moderation-case-action",
    ),
    path(
        "moderation/restrictions/<int:pk>/lift/",
        staff_views.LiftRestrictionView.as_view(),
        name="moderation-lift-restriction",
    ),
]
