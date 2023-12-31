from django.urls import path  # type: ignore

from .views import PpxAbout, PpxCreate, PpxDetail, PpxUpdate

app_name = "ppxs"

urlpatterns = [
    path("about/", PpxAbout.as_view(), name="about"),
    path("create/", PpxCreate.as_view(), name="create"),
    path("<uuid:pk>/", PpxDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", PpxUpdate.as_view(), name="update"),
]
