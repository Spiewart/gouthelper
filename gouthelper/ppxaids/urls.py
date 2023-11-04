from django.urls import path  # type: ignore

from .views import PpxAidAbout, PpxAidCreate, PpxAidDetail, PpxAidUpdate

app_name = "ppxaids"

urlpatterns = [
    path("about/", PpxAidAbout.as_view(), name="about"),
    path("create/", PpxAidCreate.as_view(), name="create"),
    path("<uuid:pk>/", PpxAidDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", PpxAidUpdate.as_view(), name="update"),
]
