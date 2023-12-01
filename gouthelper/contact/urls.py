from django.urls import path

from .views import ContactSuccessView, ContactView

app_name = "contact"

urlpatterns = [
    path("", ContactView.as_view(), name="contact"),
    path("success/", ContactSuccessView.as_view(), name="success"),
]
