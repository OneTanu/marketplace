from django.urls import path

from . import views

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("listings/", views.ListingCreateView.as_view(), name="listing-create"),
    path("listings/<int:pk>/", views.ListingDetailView.as_view(), name="listing-detail"),
]
