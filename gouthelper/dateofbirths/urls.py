from django.urls import path  # type: ignore

from .views import DateOfBirthAbout

app_name = "dateofbirths"

urlpatterns = [
    path("about/", DateOfBirthAbout.as_view(), name="about"),
]
