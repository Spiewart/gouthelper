from django.urls import path  # type: ignore

from .views import AboutFlare, AboutPpx, AboutUlt, TreatmentAbout

app_name = "treatments"

urlpatterns = [
    path("about/", TreatmentAbout.as_view(), name="about"),
    path("about/flare/", AboutFlare.as_view(), name="about-flare"),
    path("about/ppx/", AboutPpx.as_view(), name="about-ppx"),
    path("about/ult/", AboutUlt.as_view(), name="about-ult"),
]
