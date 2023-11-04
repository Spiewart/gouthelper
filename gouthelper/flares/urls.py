from django.urls import path  # type: ignore

from .views import FlareAbout, FlareCreate, FlareDetail, FlareUpdate

app_name = "flares"

urlpatterns = [
    path("about/", FlareAbout.as_view(), name="about"),
    path("create/", FlareCreate.as_view(), name="create"),
    path("<uuid:pk>/", FlareDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", FlareUpdate.as_view(), name="update"),
]
