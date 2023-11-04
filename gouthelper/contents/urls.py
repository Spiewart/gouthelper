from django.urls import path  # type: ignore

from .views import About, Home

app_name = "contents"

urlpatterns = [
    path("", Home.as_view(), name="home"),
    path("about/", About.as_view(), name="about"),
]
