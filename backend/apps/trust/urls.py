from django.urls import path

from . import views

urlpatterns = [
    path("reports/", views.ReportCreateView.as_view(), name="report-create"),
    path("blocks/", views.BlockListCreateView.as_view(), name="block-list"),
    path("blocks/<str:username>/", views.BlockDeleteView.as_view(), name="block-delete"),
    path("me/restrictions/", views.MyRestrictionsView.as_view(), name="my-restrictions"),
]
