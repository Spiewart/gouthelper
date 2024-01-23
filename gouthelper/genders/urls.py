from django.urls import path  # type: ignore

from .views import GenderAbout

app_name = "genders"

urlpatterns = [
    path("about/", GenderAbout.as_view(), name="about"),
]
