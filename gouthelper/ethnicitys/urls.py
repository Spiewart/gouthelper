from django.urls import path  # type: ignore

from .views import EthnicityAbout

app_name = "ethnicitys"

urlpatterns = [
    path("about/", EthnicityAbout.as_view(), name="about"),
]
