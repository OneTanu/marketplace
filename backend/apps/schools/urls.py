from rest_framework.routers import SimpleRouter

from .views import SchoolViewSet

router = SimpleRouter()
router.register("schools", SchoolViewSet, basename="school")

urlpatterns = router.urls
