from django.urls import path  # type: ignore

from .views import FlareAidAbout, FlareAidCreate, FlareAidDetail, FlareAidUpdate

app_name = "flareaids"

urlpatterns = [
    path("about/", FlareAidAbout.as_view(), name="about"),
    path("create/", FlareAidCreate.as_view(), name="create"),
    path("<uuid:pk>/", FlareAidDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", FlareAidUpdate.as_view(), name="update"),
]
