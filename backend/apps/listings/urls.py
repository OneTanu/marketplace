from django.urls import path

from . import views

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("listings/", views.ListingListCreateView.as_view(), name="listing-list"),
    path("listings/mine/", views.MyListingsView.as_view(), name="my-listings"),
    path("bookmarks/", views.BookmarkListView.as_view(), name="bookmark-list"),
    path(
        "users/<str:username>/listings/",
        views.PublicSellerListingsView.as_view(),
        name="public-seller-listings",
    ),
    path("listings/<int:pk>/", views.ListingDetailView.as_view(), name="listing-detail"),
    path(
        "listings/<int:pk>/bookmark/",
        views.ListingBookmarkView.as_view(),
        name="listing-bookmark",
    ),
    path("listings/<int:pk>/photos/", views.ListingPhotosView.as_view(), name="listing-photos"),
    path(
        "listings/<int:pk>/photos/order/",
        views.ListingPhotoOrderView.as_view(),
        name="listing-photo-order",
    ),
    path(
        "listings/<int:pk>/photos/<int:photo_id>/",
        views.ListingPhotoDetailView.as_view(),
        name="listing-photo-detail",
    ),
]
