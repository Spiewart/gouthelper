from django.urls import path  # type: ignore

from .views import About, DecisionAids, Home, TreatmentAids

app_name = "contents"

urlpatterns = [
    path("", Home.as_view(), name="home"),
    path("about/", About.as_view(), name="about"),
    path("decision-aids/", DecisionAids.as_view(), name="decision-aids"),
    path("treatment-aids/", TreatmentAids.as_view(), name="treatment-aids"),
]
