from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from gouthelper.flares.api.views import FlareViewSet
from gouthelper.users.api.views import PseudopatientViewSet, UserViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("flares", FlareViewSet)
router.register("pseudopatients", PseudopatientViewSet)
router.register("users", UserViewSet)


app_name = "api"
urlpatterns = router.urls
