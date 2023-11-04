from django.urls import path  # type: ignore

from .views import UltAidAbout, UltAidCreate, UltAidDetail, UltAidUpdate

app_name = "ultaids"

urlpatterns = [
    path("about/", UltAidAbout.as_view(), name="about"),
    path("create/", UltAidCreate.as_view(), name="create"),
    path("<uuid:pk>/", UltAidDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", UltAidUpdate.as_view(), name="update"),
]
