from django.urls import path  # type: ignore

from .views import AboutHlab5801, AboutUrate, LabAbout

app_name = "labs"

urlpatterns = [
    path("about/", LabAbout.as_view(), name="about"),
    path("about/hlab5801/", AboutHlab5801.as_view(), name="about-hlab5801"),
    path("about/urate/", AboutUrate.as_view(), name="about-urate"),
]
